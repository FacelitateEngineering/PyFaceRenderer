from typing import Union
import dearpygui.dearpygui as dpg
import numpy as np
from pyrender.trackball import Trackball
from pyrender.camera import OrthographicCamera, PerspectiveCamera
from pyrender.node import Node
from pyrender.light import DirectionalLight
import pyrender
from pyrender.constants import RenderFlags
import trimesh
import logging as log
from .utils import numpy2texture_data, lookat
from .primitive_extension import upload_vertex_data
from PIL import Image
from typing import Optional
from pathlib import Path
from .blendshape_model import ARKitModel

logger = log.getLogger('PyRenderer')

class FaceRenderer:
    fr_window:Optional[int] = None
    ctrl_window = None


    def __init__(self, mesh: Union[pyrender.Mesh, str], height=640, width=360, default_camera_pose=None, background_image:Optional[np.ndarray]=None) -> None:
        self._height = height
        self._width = width
        self.mesh_type = 'static'
        with dpg.texture_registry(show=False):
            self.__texture_id = dpg.add_dynamic_texture(width, height, np.ones((height, width, 4), dtype=np.uint8)*200, tag='__face_renderer_texture_tag')
        
        if isinstance(mesh, pyrender.Mesh):
            self.mesh = mesh
        elif isinstance(mesh, trimesh.Trimesh):
            self.trimesh = mesh
            self.mesh = pyrender.Mesh.from_trimesh(self.trimesh, )
        elif mesh == 'mediapipe':
            self.trimesh = trimesh.load('data/models/face_mesh.obj')
            self.mesh = pyrender.Mesh.from_trimesh(self.trimesh, )
        elif mesh == 'fuze':
            self.trimesh = trimesh.load('data/models/fuze.obj')
            self.mesh = pyrender.Mesh.from_trimesh(self.trimesh)
        elif mesh == 'arkit':
            self.blendshape_model = ARKitModel()
            self.trimesh = self.blendshape_model.trimesh
            self.mesh = self.blendshape_model.neutral_mesh
            self.mesh_type = 'blendshape'
        elif isinstance(mesh, (str, Path)):
            mesh_path = Path(mesh)
            assert mesh_path.exists(), mesh_path
            self.trimesh = trimesh.load(str(mesh))
            self.mesh = pyrender.Mesh.from_trimesh(self.trimesh)
        else:
            raise NotImplementedError(f'Unrecognized mesh or topology: {mesh}')
        
        
        self.background_image = np.array(Image.fromarray(background_image).resize([self._width, self._height])) if background_image is not None else None
        self.scene = pyrender.Scene(bg_color=[0.3, 0.3, 0.4, 0.2], ambient_light=[0.4]* 4)
        self.mesh_node = Node(mesh=self.mesh)
        self.scene.add_node(self.mesh_node)

        if default_camera_pose is None:
            default_camera_pose = np.eye(4)
            default_camera_pose[2, -1] = 0.5

        self.init_camera_pose = default_camera_pose
        logger.info(self.init_camera_pose)

        self.trackball = Trackball(pose=self.init_camera_pose, size=(self._width, self._height), scale=1.0, )
        # self.trackball

        self.light = pyrender.DirectionalLight(color=np.array([0.0, 0.45, 0.5]), intensity=30.0,)
        self._camera_node = None
        self.set_camera('perps')
        self.scene.add_node(self._camera_node)
        self.scene.main_camera_node = self._camera_node

        self._renderer = pyrender.OffscreenRenderer(width, height)

        self._render_callbacks = []
        self._update_texture = True
        self._is_focus = False
        self._is_clicked = False
        self._start_drag_pos = None
        self._mesh_pos_inv_operations = []

    def add_render_callbacks(self, callback):
        self._render_callbacks.append(callback)

    def set_light_intensity(self, intensity):
        self.light.intensity = intensity
        self._render()

    def set_light_color(self, color):
        self.light.color = np.array(color)
        self._render()
        pass

    def set_camera(self, cam_type:str):
        if cam_type == 'persp':
            self.camera = PerspectiveCamera(
                yfov=np.pi, 
                # aspectRatio=9/16,
                znear=0.01,
                zfar=100.0,
            )
        else:
            self.camera = OrthographicCamera(
                xmag=0.5, ymag=0.5,
                znear=0.01,
                zfar=100.0,
            )
        if self._camera_node is None:
            self._camera_node = Node(matrix=self.trackball._n_pose, camera=self.camera, light=self.light)
        else:
            self._camera_node.camera = self.camera
        return 

    def print_centroid(self):
        logger.info('Mesh Info:')
        logger.info(f'Centroid: {self.mesh._primitives[0].centroid}')
        logger.info(f'Bounds: {self.mesh._primitives[0].bounds}')
        logger.info(f'Scales: {self.mesh._primitives[0].bounds[1] - self.mesh._primitives[0].bounds[0]}')
        return 

    def center_mesh(self):
        self._renderer._platform.make_current()
        center = (self.mesh._primitives[0].bounds[1] + self.mesh._primitives[0].bounds[0])/2
        self._trans = -center
        logger.debug('Centered Mesh')
        self._render()

    def scale_mesh(self, scale=1.0):
        self._renderer._platform.make_current()
        _p = self.mesh._primitives[0]
        ori_scale = max(_p.bounds[1] - _p.bounds[0])
        _p.positions = _p.positions/ori_scale*scale # now the bounds should be 0, 0, 0, 1, 1, 1
        self._mesh_pos_inv_operations.append(lambda x: x/scale*ori_scale)
        upload_vertex_data(_p)
        logger.debug(f'Scaled Mesh to {scale}')
        self._render()
        return 

    def move_mesh(self, axis, _dir):
        self._renderer._platform.make_current()
        _p = self.mesh._primitives[0]
        _step = dpg.get_value('__fr_ctrl_panel_sensitivity')
        _p.positions[:, axis] += _dir*_step
        _p.positions = _p.positions # triggers the recalculation
        def unmove(x):
            x[:, axis] -= _dir*_step
            return x
        self._mesh_pos_inv_operations.append(unmove)
        upload_vertex_data(_p)
        logger.debug('Uped Mesh')
        self._render()

    def reset_mesh(self):
        self._renderer._platform.make_current()
        _p = self.mesh._primitives[0]
        for op in self._mesh_pos_inv_operations[::-1]:
            _p.positions = op(_p.positions)
        upload_vertex_data(_p)
        logger.debug('Reset Mesh')
        self._mesh_pos_inv_operations.clear()
        self._render()

    def reset_pose(self):
        logger.info('Reset pose')
        self.trackball = Trackball(pose=self.init_camera_pose, size=(self._width, self._height), scale=1.0, )
        self._render()


    def show_face_renderer(self, show_control=True):
        with dpg.window(label='Face Renderer', tag='_face_renderer_window', pos=(0, 0), width=self._width, height=self._height) as self.fr_window:
            dpg.add_image('__face_renderer_texture_tag', tag='__face_render_image', width=self._width, height=self._height)
            pass

        with dpg.item_handler_registry() as fr_handler_reg:
            dpg.add_item_resize_handler(callback=self.resize_renderer)
        
        with dpg.item_handler_registry() as fr_image_handler_reg:
            dpg.add_item_clicked_handler(callback=self.set_clicked, user_data='Clicked')
            dpg.add_item_focus_handler(callback=self.set_clicked, user_data='Focus')


        with dpg.handler_registry(tag='_face_renderer_window_handler'):
            dpg.add_key_press_handler(dpg.mvKey_R, callback=self.reset_pose)
            dpg.add_mouse_release_handler(callback=self.set_unclicked, )
            dpg.add_mouse_drag_handler(callback=self.dragged, )

        
        dpg.bind_item_handler_registry('_face_renderer_window', fr_handler_reg)
        dpg.bind_item_handler_registry('__face_render_image', fr_image_handler_reg)
        self.trackball.set_state(Trackball.STATE_ROTATE)
        width = 200
        self._trans = np.zeros(3)
        self._rot = np.eye(3)
        self._scale = np.ones(3)
        
        with dpg.window(label='FR Control panel', show=show_control, tag='_face_renderer_ctrl_window', pos=(self._width, 0)) as self.ctrl_window:
            with dpg.collapsing_header(label='Mesh', default_open=True):
                dpg.add_button(label='Center', callback=self.center_mesh, width=width)
                dpg.add_button(label='Scale', callback=lambda: self.scale_mesh(), width=width)

                def set_trans(_, value, axis):
                    self._trans[axis] = value
                    self._render()

                with dpg.group(horizontal=True, horizontal_spacing=0):
                    for i, axis in enumerate(['X', 'Y', 'Z']):
                        dpg.add_drag_float(callback=set_trans, width=width, default_value=0.0, speed=1.0, tag=f'__fr_ctrl_panel_trans_{axis}', user_data=i)

                dpg.add_drag_float(label='Sensitivity', width=width, default_value=0.01, speed=0.0005, min_value=0.0, max_value=0.1, tag='__fr_ctrl_panel_sensitivity')
                dpg.add_button(label='Print Centroid', callback=self.print_centroid, width=width)
                dpg.add_button(label='Reset', callback=self.reset_mesh, width=width)
            with dpg.collapsing_header(label='Camera', default_open=True):
                dpg.add_button(label='Reset Pose', callback=self.reset_pose, width=width)
                dpg.add_combo(['persp', 'orth'], label='Type', default_value='persp', width=width, callback=lambda s, a: self.set_camera(a))
                def look_at_centroid():
                    center = (self.mesh._primitives[0].bounds[1] + self.mesh._primitives[0].bounds[0])/2
                    camera_pos = self.trackball._n_pose[:3, 3]
                    matrix = lookat(camera_pos, center, np.array([1, 0, 0]))
                    self.trackball._n_pose = matrix
                    self._render()
                    return 
                dpg.add_button(label='LookAt', callback=look_at_centroid, width=width)
                dpg.add_combo(['ROTATE', 'ZOOM', 'PAN', 'ROLL'], label='Mode', default_value='ROTATE', width=width, 
                callback=lambda s, a: self.set_mode(a))
                def _set_n_pose(s, a, u):
                    self.trackball._n_pose[u] = a
                    self._render()
                for i in range(4):
                    dpg.add_drag_floatx(tag=f'__fr_ctrl_panel_camera_pose_row_{i}', width=width, speed=0.05, min_value=-100.0, max_value=100.0, size=4, callback=_set_n_pose, user_data=i)
            with dpg.collapsing_header(label='Light0', default_open=True):
                dpg.add_drag_float(label='Intensity', callback=lambda s, a: self.set_light_intensity(a), width=width, default_value=30)
                dpg.add_color_edit(default_value=(0, int(255*0.45), int(255*0.55)), label='Color', callback=lambda s, a: self.set_light_color((a[0:3])), )
            with dpg.collapsing_header(label='Visualization', default_open=True):
                dpg.add_drag_float(label='Mesh Alpha', default_value=1.0, min_value=0.0, max_value=1.0, speed=0.05, clamped=True, tag='__fr_ctrl_panel_alpha', callback=self._render)
                dpg.add_checkbox(label='Wireframe', tag='__fr_ctrl_panel_wireframe', callback=self._render)
            if self.mesh_type == 'blendshape':
                self._coe = np.zeros(self.blendshape_model.n_blendshapes)
                def _update_blendshape(s, a, u):
                    self._coe[u] = a
                    vertices = self.blendshape_model.get_mesh(self._coe)                    
                    self._render()
                    
                with dpg.collapsing_header(label='Blendshapes', default_open=False):
                    for i in range(self.blendshape_model.n_blendshapes):
                        with dpg.group(horizontal=True, horizontal_spacing=0):
                            dpg.add_text(str(self.blendshape_model.blendshape_names[i]), )
                            dpg.add_drag_float(default_value=0.0, min_value=-1.0, max_value=1.0, speed=0.05, clamped=True, callback=_update_blendshape)

            dpg.add_button(label='Render', callback=self._render, width=width)
            pass
        self._render()

    def set_mode(self, mode):
        mode = getattr(Trackball, f'STATE_{mode}')
        self.trackball.set_state(mode)


    def set_clicked(self, s, a, u):
        self._is_clicked = True
        self._start_drag_pos = None
        return

    def set_unclicked(self):
        self._is_clicked = False
        self._start_drag_pos = None
        self.trackball._pose = self.trackball._n_pose
        return

    def dragged(self, s, a, u):
        if not (self._is_clicked and dpg.is_item_focused('_face_renderer_window')):
            return
        mouse_coord = (a[1], -a[2])
        if self._start_drag_pos is None:
            self._start_drag_pos = mouse_coord
            self.trackball.down(self._start_drag_pos)
        elif mouse_coord[0] == 0 and mouse_coord[1] == 0:
            # ghost drag
            return
        self.trackball.drag(mouse_coord)
        self._render()
        return

    def update_mesh(self, vertex:np.ndarray, update_normal=True):
        self._renderer._platform.make_current()
        if update_normal:
            if vertex.shape != self.trimesh.vertices.shape:
                logger.error(f'Shape mismatch: {vertex.shape} != {self.trimesh.vertices.shape}')
                return
            self.trimesh.vertices[:] = vertex[:]
            self.mesh.primitives[0].positions = self.trimesh.vertices
            self.mesh.primitives[0].normals = self.trimesh.vertex_normals
        else:
            if vertex.shape != self.mesh.primitives[0].positions.shape:
                logger.error(f'Shape mismatch: {vertex.shape} != {self.mesh.primitives[0].positions.shape}')
                return 
            self.mesh.primitives[0].positions = vertex
        upload_vertex_data(self.mesh.primitives[0])
        logger.info('Updated Mesh from vertex array')


    def _render(self):
        """Trigger a re-render event"""
        pose = self.trackball.pose.copy()
        self._camera_node.matrix = pose
        # self._light_node.matrix = pose
        flags = RenderFlags.NONE
        if dpg.get_value('__fr_ctrl_panel_wireframe'):
            flags |= RenderFlags.FLIP_WIREFRAME

        color, depth = self._renderer.render(self.scene, flags)
        
        if self._update_texture:
            _depth = (depth[..., None] > 0.01)
            alpha = dpg.get_value('__fr_ctrl_panel_alpha')
            if self.background_image is None:
                _depth = _depth.astype(np.uint8) * int(255*alpha)
                color = np.concatenate([color, _depth], axis=-1)
            elif alpha == 1.0: 
                color = np.where(_depth, color, self.background_image)
            else: # alpha blending with image
                _depth = _depth.astype(float)*alpha
                color = (color * _depth + self.background_image * (1-_depth)).astype(np.uint8)

            texture_data = numpy2texture_data(color, bgr=False)
            dpg.set_value('__face_renderer_texture_tag', texture_data)
            logger.debug('Updated image')

        for i in range(4):
            dpg.set_value(f'__fr_ctrl_panel_camera_pose_row_{i}', pose[i, :].astype(np.float32))

        return color, depth

    def print_pose(self):
        logger.info(self.trackball.pose)
        return

    def resize_renderer(self):
        with dpg.mutex():
            window_width, window_height = dpg.get_item_rect_size('_face_renderer_window')
            _window_height = window_height - 20
            aspect_ratio = 9/16
            if window_width/_window_height > aspect_ratio: # too wide
                img_height = _window_height
                img_width = int(_window_height/16*9)
            else: # too tall
                img_height = int(window_width/9*16)
                img_width = window_width
                window_height = int(window_width/aspect_ratio)

            x_pos = int(window_width/2-img_width/2)
            dpg.set_item_height('__face_render_image', img_height)
            dpg.set_item_width('__face_render_image', img_width)
            dpg.set_item_pos('__face_render_image', (x_pos, 0))
            self.trackball.resize((img_width, img_height))

