from typing import Union
import dearpygui.dearpygui as dpg
import numpy as np
from pyrender.trackball import Trackball
from pyrender.camera import OrthographicCamera
from pyrender.node import Node
from pyrender.light import DirectionalLight
import pyrender
from pyrender.constants import RenderFlags
import trimesh
import logging as log
from .utils import numpy2texture_data, lookat
from .primitive_extension import upload_vertex_data
from PIL import Image
logger = log.getLogger('PyRenderer')

class FaceRenderer:
    fr_window = None
    ctrl_window = None

    def __init__(self, mesh: Union[pyrender.Mesh, str], height=640, width=360, default_camera_pose=None) -> None:
        self._height = height
        self._width = width
        with dpg.texture_registry(show=False):
            self.__texture_id = dpg.add_dynamic_texture(width, height, np.ones((height, width, 4), dtype=np.uint8)*200, tag='__face_renderer_texture_tag')

        if isinstance(mesh, pyrender.Mesh):
            self.mesh = mesh
        elif mesh == 'mediapipe':
            self.trimesh = trimesh.load('data/models/face_mesh.obj')
            self.mesh = pyrender.Mesh.from_trimesh(self.trimesh, )
        elif mesh == 'fuze':
            self.trimesh = trimesh.load('data/models/fuze.obj')
            self.mesh = pyrender.Mesh.from_trimesh(self.trimesh)
        else:
            raise NotImplementedError(f'Unrecognized mesh or topology: {mesh}')
        

        
        self.scene = pyrender.Scene(bg_color=[0.3, 0.3, 0.4, 0.2], ambient_light=[0.4]* 4)
        self.mesh_node = Node(mesh=self.mesh)
        self.scene.add_node(self.mesh_node)
        self.camera = OrthographicCamera(
            xmag=1.0, ymag=1.0,
            znear=0.01,
            zfar=100.0,
        )

        if default_camera_pose is None:
            default_camera_pose = np.eye(4)
            default_camera_pose[2, -1] = 0.5

        self.init_camera_pose = default_camera_pose
        logger.info(self.init_camera_pose)

        self.trackball = Trackball(pose=self.init_camera_pose, size=(width, height), scale=1.0)

        self.light = pyrender.DirectionalLight(color=np.array([0.0, 0.45, 0.5]), intensity=30.0,)
                                # innerConeAngle=np.pi/4.0,
                                # outerConeAngle=np.pi/2)
        self._camera_node = Node(matrix=self.init_camera_pose, camera=self.camera, light=self.light)
        self.scene.add_node(self._camera_node)
        self.scene.main_camera_node = self._camera_node

        # self.scene.add_node(self._light_node)1
        self._renderer = pyrender.OffscreenRenderer(width, height)

        self._is_focus = False
        self._is_clicked = False
        self._start_drag_pos = None

    def set_light_intensity(self, intensity):
        self.light.intensity = intensity
        self._render()

    def set_light_color(self, color):
        self.light.color = np.array(color)
        # print(self.light.color)
        self._render()
        pass

    def center_mesh(self):
        self._renderer._platform.make_current()
        _p = self.mesh._primitives[0]
        # logger.debug('Before Center')
        # logger.debug(f'Bound: {_p.bounds}')
        # logger.debug(f'Centroid: {_p.centroid}')
        _p.positions = _p.positions - _p.bounds[0]
        _p.positions = _p.positions/max(_p.bounds[1]) # now the bounds should be 0, 0, 0, 1, 1, 1
        _p.positions = _p.positions-_p.centroid

        upload_vertex_data(_p)
        logger.debug('Centered Mesh')
        self._render()

    def move_mesh(self, axis, _dir):
        self._renderer._platform.make_current()
        _p = self.mesh._primitives[0]
        _p.positions[:, axis] += _dir*dpg.get_value('__fr_ctrl_panel_sensitivity')

        upload_vertex_data(_p)
        logger.debug('Uped Mesh')
        self._render()

    def reset_pose(self):
        logger.info('Reset pose')
        self.trackball._n_pose = self.init_camera_pose
        self._render()


    def show_face_renderer(self, show_control=True):
        with dpg.window(label='Face Renderer', tag='_face_renderer_window') as self.fr_window:
            dpg.add_image('__face_renderer_texture_tag', tag='__face_render_image', width=self._width, height=self._height)
            pass

        with dpg.item_handler_registry() as fr_handler_reg:
            dpg.add_item_resize_handler(callback=self.resize_renderer)
        
        with dpg.item_handler_registry() as fr_image_handler_reg:
            
            dpg.add_item_clicked_handler(callback=self.set_clicked, user_data='Clicked')
            dpg.add_item_focus_handler(callback=self.set_clicked, user_data='Focus')


        with dpg.handler_registry():
            dpg.add_key_press_handler(dpg.mvKey_R, callback=self.reset_pose)
            dpg.add_mouse_release_handler(callback=self.set_unclicked, )
            dpg.add_mouse_drag_handler(callback=self.dragged, )

        dpg.bind_item_handler_registry('_face_renderer_window', fr_handler_reg)
        dpg.bind_item_handler_registry('__face_render_image', fr_image_handler_reg)
        self.trackball.set_state(Trackball.STATE_ROTATE)
        width = 200
        with dpg.window(label='FR Control panel', show=show_control) as self.ctrl_window:
            with dpg.collapsing_header(label='Mesh Ctrl', default_open=True):
                dpg.add_checkbox(label='Wireframe', tag='__fr_ctrl_panel_wireframe', callback=self._render)
                dpg.add_button(label='Center', callback=self.center_mesh, width=width)
                for i, axis in enumerate(['X', 'Y', 'Z']):
                    with dpg.group(horizontal=Tr1````ue):
                        dpg.add_text(axis)
                        dpg.add_button(label='+', callback=lambda s, a, u: self.move_mesh(u[0], u[1]), width=int(width/2), user_data=(i, 1))
                        dpg.add_button(label='-', callback=lambda s, a, u: self.move_mesh(u[0], u[1]), width=int(width/2), user_data=(i, -1))
                dpg.add_drag_float(label='Sensitivity', width=width, default_value=0.01, speed=0.0005, min_value=0.0, max_value=0.1, tag='__fr_ctrl_panel_sensitivity')
            with dpg.collapsing_header(label='Camera Ctrl', default_open=True):
                dpg.add_button(label='Reset Pose', callback=self.reset_pose, width=width)
                dpg.add_combo(['ROTATE', 'ZOOM', 'PAN', 'ROLL'], label='Mode', default_value='ROTATE', width=width, callback=lambda s, a: self.set_mode(a))
                dpg.add_button(label="Print Pose", callback=self.print_pose, width=width)
            with dpg.collapsing_header(label='Light Ctrl', default_open=True):
                dpg.add_drag_float(label='Intensity', callback=lambda s, a: self.set_light_intensity(a), width=width, default_value=30)
                dpg.add_color_edit(default_value=(0, int(255*0.45), int(255*0.55)), label='Color', callback=lambda s, a: self.set_light_color((a[0:3])), )
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
        if not self._is_clicked:
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

    def update_mesh(self, vertex:np.ndarray):
        if vertex.shape != self.trimesh.vertices.shape:
            logger.error(f'Shape mismatch: {vertex.shape} != {self.trimesh.vertices.shape}')
            return
        self.trimesh.vertices[:] = vertex[:]
        self.mesh.primitives[0].positions = self.trimesh.vertices
        self.mesh.primitives[0].normals = self.trimesh.vertex_normals
        upload_vertex_data(self.mesh.primitives[0])
        self._render()
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
        depth = depth[..., None] > 0.01
        depth = depth.astype(np.uint8) * 255
        color = np.concatenate([color, depth], axis=-1)
        texture_data = numpy2texture_data(color, bgr=False)
        dpg.set_value('__face_renderer_texture_tag', texture_data)
        logger.debug('Updated image')


    def print_pose(self):
        print(self.trackball.pose)
        return

    def resize_renderer(self):
        with dpg.mutex():
            window_width, window_height = dpg.get_item_rect_size('_face_renderer_window')
            _window_height = window_height - 20
            aspect_ratio = 9/16
            if window_width/_window_height > aspect_ratio: # too wide
                img_height = _window_height
                img_width = int(_window_height/16*9)
                # window_width = int(window_height*aspect_ratio)
                # dpg.set_item_width('_face_renderer_window', window_width)

            else: # too tall
                img_height = int(window_width/9*16)
                img_width = window_width
                window_height = int(window_width/aspect_ratio)
                # dpg.set_item_height('_face_renderer_window', window_width)

            x_pos = int(window_width/2-img_width/2)
            dpg.set_item_height('__face_render_image', img_height)
            dpg.set_item_width('__face_render_image', img_width)
            dpg.set_item_pos('__face_render_image', (x_pos, 0))
            self.trackball.resize((img_width, img_height))

