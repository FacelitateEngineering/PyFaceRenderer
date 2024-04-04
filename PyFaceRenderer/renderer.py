import os
import platform
import subprocess
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
from .utils import numpy2texture_data, lookat, rot2quat
from .primitive_extension import upload_vertex_data
from PIL import Image
from typing import Optional
from pathlib import Path
from .blendshape_model import ARKitModel
from datetime import datetime
from tqdm import tqdm
import pickle
import shutil

logger = log.getLogger('PyRenderer')

class FaceRenderer:
    fr_window:Optional[int] = None
    ctrl_window = None

    def __init__(self, mesh: Union[pyrender.Mesh, str], height=640, width=360, default_camera_pose=None, background_image:Optional[np.ndarray]=None) -> None:
        self._height = height
        self._width = width
        self.mesh_type = 'static'
        with dpg.texture_registry(show=False):
            self.__texture_id = dpg.add_dynamic_texture(width, height, np.ones((height, width, 4), dtype=np.uint8)*255, tag='__face_renderer_texture_tag')        
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
        elif mesh == 'flame':
            model = pickle.load(open('data/models/flame/generic_model_converted.pkl', 'rb'))
            self.trimesh = trimesh.Trimesh(model['v_template'], model['f'])
            self.mesh = pyrender.Mesh.from_trimesh(self.trimesh)
        elif isinstance(mesh, (str, Path)):
            mesh_path = Path(mesh)
            assert mesh_path.exists(), mesh_path
            self.trimesh = trimesh.load(str(mesh))
            self.mesh = pyrender.Mesh.from_trimesh(self.trimesh, )
        else:
            raise NotImplementedError(f'Unrecognized mesh or topology: {mesh}')
        
        
        self.background_image = np.array(Image.fromarray(background_image).resize([self._width, self._height])) if background_image is not None else None
        self.scene = pyrender.Scene(bg_color=[0.3, 0.3, 0.3, 0.2], )
        
        self.mesh_node = Node(mesh=self.mesh, )
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
        self.set_camera('ortho')
        self.scene.add_node(self._camera_node)
        self.scene.main_camera_node = self._camera_node

        self._renderer = pyrender.OffscreenRenderer(width, height)

        self._render_callbacks = []
        self._update_texture = True
        self._is_focus = False
        self._is_clicked = False
        self._start_drag_pos = None
        self._mesh_pos_inv_operations = []
        self._is_rendering = False

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
                yfov=2*np.pi, 
                # aspectRatio=9/16,
                znear=0.01,
                zfar=1000000.0,
            )
        else:
            self.camera = OrthographicCamera(
                xmag=0.5, ymag=0.5,
                znear=0.01,
                zfar=1000000.0,
            )
        if self._camera_node is None:
            self._camera_node = Node(matrix=self.trackball._n_pose, camera=self.camera, light=self.light)
        else:
            self._camera_node.camera = self.camera
        return 
    

    def center_mesh(self):
        self._renderer._platform.make_current()
        center = (self.mesh._primitives[0].bounds[1] + self.mesh._primitives[0].bounds[0])/2
        _scale = dpg.get_value('__fr_ctrl_panel_mesh_scale')
        dpg.set_value('__fr_ctrl_panel_mesh_trans', -center*_scale)
        self._render()

    def scale_mesh(self):
        self._renderer._platform.make_current()
        _p = self.mesh._primitives[0]
        ori_scale = max(_p.bounds[1] - _p.bounds[0])
        dpg.set_value('__fr_ctrl_panel_mesh_scale', 1.0/ori_scale)
        self._render()
        return 


    def reset_mesh(self):
        dpg.set_value('__fr_ctrl_panel_mesh_scale', 1.0)
        dpg.set_value('__fr_ctrl_panel_mesh_trans', [0.0, 0.0, 0.0])
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
        

        
        with dpg.window(label='FR Control panel', show=show_control, tag='_face_renderer_ctrl_window', pos=(self._width, 0), height=self._height, width=2*width) as self.ctrl_window:
            with dpg.collapsing_header(label='Mesh', default_open=True):
                with dpg.group(horizontal=True, horizontal_spacing=0):
                    dpg.add_drag_doublex(width=width, speed=0.1, tag=f'__fr_ctrl_panel_mesh_trans', size=3, callback=self._render, min_value=-1000.0, max_value=1000.0)
                    dpg.add_text(' Position')
                with dpg.group(horizontal=True, horizontal_spacing=0):
                    dpg.add_drag_doublex(width=width, speed=0.1, tag=f'__fr_ctrl_panel_mesh_rot', size=3, callback=self._render, min_value=-np.pi*2, max_value=np.pi*2)
                    dpg.add_text(' Rotation')
                with dpg.group(horizontal=True, horizontal_spacing=0):
                    dpg.add_drag_double(width=width, speed=0.0001, tag=f'__fr_ctrl_panel_mesh_scale', default_value=1.0, callback=self._render)
                    dpg.add_text(' Scale')
                with dpg.collapsing_header(label='Utils', default_open=True):
                    dpg.add_button(label='Center', callback=self.center_mesh, width=width)
                    dpg.add_button(label='Scale', callback=self.scale_mesh, width=width)
                    dpg.add_button(label='Reset', callback=self.reset_mesh, width=width)
            with dpg.collapsing_header(label='Camera', default_open=False):    
                def look_at_centroid():
                    center = (self.mesh._primitives[0].bounds[1] + self.mesh._primitives[0].bounds[0])/2
                    camera_pos = self.trackball._n_pose[:3, 3]
                    matrix = lookat(camera_pos, center, np.array([1, 0, 0]))
                    self.trackball._n_pose = matrix
                    self._render()
                    return 
                
                dpg.add_combo(['ROTATE', 'ZOOM', 'PAN', 'ROLL'], label='Mode', default_value='ROTATE', width=width, 
                callback=lambda s, a: self.set_mode(a))
                def _set_n_pose(s, a, u):
                    self.trackball._n_pose[u] = a
                    self._render()
                for i in range(4):
                    dpg.add_drag_floatx(tag=f'__fr_ctrl_panel_camera_pose_row_{i}', width=width, speed=0.05, min_value=-100.0, max_value=100.0, size=4, callback=_set_n_pose, user_data=i)
                dpg.add_button(label='LookAt', callback=look_at_centroid, width=width)
                dpg.add_button(label='Reset', callback=self.reset_pose, width=width, )
            with dpg.collapsing_header(label='Light', default_open=False):
                dpg.add_text('Directional')
                dpg.add_drag_float(label='Intensity', callback=lambda s, a: self.set_light_intensity(a), width=width, default_value=30)
                dpg.add_color_edit(default_value=(0, int(255*0.45), int(255*0.55)), label='Color', callback=lambda s, a: self.set_light_color((a[0:3])), )
                # dpg.add_text('Ambient')
                # dpg.add_drag_float(label='Intensity', callback=lambda s, a: self.scene.ambient_light(a), width=width, default_value=30)
                # dpg.add_color_edit(default_value=(0, int(255*0.45), int(255*0.55)), label='Color', callback=lambda s, a: self.set_light_color((a[0:3])), )

            with dpg.collapsing_header(label='Visualization', default_open=False):
                dpg.add_drag_float(label='Mesh Alpha', default_value=1.0, min_value=0.0, max_value=1.0, speed=0.05, clamped=True, tag='__fr_ctrl_panel_alpha', callback=self._render)
                dpg.add_checkbox(label='Wireframe', tag='__fr_ctrl_panel_wireframe', callback=self._render)
            if self.mesh_type == 'blendshape':
                self._coe = np.zeros(self.blendshape_model.n_blendshapes)
                def _update_blendshape(s, a, u):
                    if u is None:
                        self._coe[:] = 0.0
                    else:
                        self._coe[u] = np.clip(a, 0.0, 1.0)
                    self.mesh.primitives[0].coes_0 = self._coe
                    self._render()
                    
                with dpg.collapsing_header(label='Blendshapes', default_open=False):
                    blendshape_ids = []
                    for i in range(self.blendshape_model.n_blendshapes):
                        _id = dpg.add_drag_float(default_value=0.0, min_value=0.0, max_value=1.0, speed=0.01, clamped=True, callback=_update_blendshape, 
                                                 width=width, user_data=i, label=f'{str(self.blendshape_model.blendshape_names[i])}', 
                                                 tag=f'{str(self.blendshape_model.blendshape_names[i])}_drag')
                        blendshape_ids.append(_id)
                    def reset_blendshapes(s, a, u):
                        for _id in u:
                            dpg.set_value(_id, 0.0)
                        self._coe[:] = 0.0
                        self.mesh.primitives[0].coes_0[:] = 0.0
                        self._render()

                    dpg.add_button(label='Reset', callback=reset_blendshapes, width=width, user_data=blendshape_ids)

            with dpg.collapsing_header(label='IO', default_open=True):
                param_names = ['__fr_ctrl_panel_mesh_trans', '__fr_ctrl_panel_mesh_rot', '__fr_ctrl_panel_mesh_scale', ]
                for i in range(4):
                    param_names.append(f'__fr_ctrl_panel_camera_pose_row_{i}')
                    
                def export_config():
                    params = {p: dpg.get_value(p) for p in param_names}
                    np.save('face_renderer_config.npy', params)
                    log.info('Exported Config')
                    return 
                
                def import_config():
                    if Path('face_renderer_config.npy').exists():
                        conf = np.load('face_renderer_config.npy', allow_pickle=True).item()
                        for param_name, value in conf.items():            
                            dpg.set_value(param_name, value)
                        for i in range(4):
                            _set_n_pose(None, conf[f'__fr_ctrl_panel_camera_pose_row_{i}'], i)
                        log.info('Imported Config')
                        self._render()
                    else:
                        log.error('Config file not found')
                dpg.add_button(label='Export', callback=export_config, width=width)
                dpg.add_button(label='Import', callback=import_config, width=width)

                def screenshot():
                    self._update_texture = False
                    color, depth = self._render()
                    self._update_texture = True
                    Path('Screenshots').mkdir(exist_ok=True)
                    filename = datetime.now().strftime('Screenshots/Screenshot_%Y%m%d_%H%M%S.png')
                    Image.fromarray(color).save(filename)
                    log.info(f'Saved screenshot to {filename}')
                    return    
                
            with dpg.collapsing_header(label='Render', default_open=True):
                dpg.add_button(label='Screenshot', callback=screenshot, width=width)
                dpg.add_input_text(label='Animation File', default_value='data/mediapipe.pkl', width=width, tag='__fr_ctrl_panel_animation_file')
                dpg.add_button(label='Render Animation', callback=lambda: self.render_animation(), width=width)
                
            
            dpg.add_separator()
            dpg.add_button(label='Render', callback=self._render, width=2*width)
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

    def render_animation(self, ):
        animation_file = Path(dpg.get_value('__fr_ctrl_panel_animation_file'))
        if not animation_file.exists():
            log.error(f'Animation file not found: {animation_file}')
            return
        self._update_texture = False
        output_filename = datetime.now().strftime(f'Screenshots/{animation_file.stem}_rendered_%Y%m%d_%H%M%S.mp4')
        
        screenshot = Path('Screenshots')
        tmp_folder = screenshot / 'tmp'
        if tmp_folder.exists():
            shutil.rmtree(tmp_folder) # remove all existing caches
        tmp_folder.mkdir(parents=True)

        with open(animation_file,'rb') as f:
            animation_frames = pickle.load(f)
        log.info(f'Rendering animation: {len(animation_frames["data"])} frames from {animation_file} -> {output_filename}')
        if hasattr(self.mesh.primitives[0], 'coes_0') and self.mesh.primitives[0].coes_0 is not None:
            self.mesh.primitives[0].coes_0[:] = 0.0
        
        for i, animation in tqdm(enumerate(animation_frames['data']), total=len(animation_frames['data'])):
            if 'blendshapes' in animation:
                a:dict = animation['blendshapes']
                for blendshape_name, value in a.items():
                    if blendshape_name in self.blendshape_model.blendshape_names:
                        idx = self.blendshape_model.blendshape_names.index(blendshape_name)
                        self.mesh.primitives[0].coes_0[idx] = value
                    else:
                        logger.warning(f'[{i}] Blendshape {blendshape_name} not found in model ({value})')
            if 'vertex' in animation:
                self.update_mesh(animation['vertex'], update_normal=False)
            color, depth = self._render()
            Image.fromarray(color).save(f'Screenshots/tmp/{animation_file.stem}{i:07d}.png')
        
        fps = animation_frames['metadata']['fps']
        if 'audio' in animation_frames['metadata'] and Path(animation_frames['metadata']['audio']).exists(): # attach the audio file
            audio_file_path = animation_frames['metadata']['audio']
            import librosa
            sample, sr =  librosa.load(audio_file_path)
            duration = sample.shape[-1]/sr
            fps = len(animation_frames['data'])/duration
            command = f"ffmpeg -framerate {fps} -pattern_type glob -i 'Screenshots/tmp/*.png' -i {audio_file_path}  -map 0:v -map 1:a -c:v libx264 -pix_fmt yuv420p {output_filename}"
        else:
            command = f"ffmpeg -framerate {fps} -pattern_type glob -i 'Screenshots/tmp/*.png' -c:v libx264 -pix_fmt yuv420p {output_filename}"
        
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,universal_newlines=True, shell=True)
        p.wait()
        _platform = platform.system().lower()
        if _platform == "windows":
            os.startfile(output_filename)
        elif _platform == "darwin":
            subprocess.Popen(["open", output_filename])
        else:
            subprocess.Popen(["xdg-open", output_filename])

        self._update_texture = True
        return 


    def _render(self):
        """Trigger a re-render event"""
        if self._is_rendering:
            log.debug('Dropping frame')
            return 
        self._is_rendering = True
        pose = self.trackball.pose.copy()
        self._camera_node.matrix = pose
        self.mesh_node.translation = dpg.get_value('__fr_ctrl_panel_mesh_trans')[:3]
        self.mesh_node.rotation = rot2quat(*dpg.get_value('__fr_ctrl_panel_mesh_rot')[:3])
        self.mesh_node.scale = [dpg.get_value('__fr_ctrl_panel_mesh_scale')]*3
        
        
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
            # logger.debug('Updated image')

        for i in range(4):
            dpg.set_value(f'__fr_ctrl_panel_camera_pose_row_{i}', pose[i, :].astype(np.float32))
        self._is_rendering = False
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

