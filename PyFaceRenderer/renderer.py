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
from PIL import Image
from pytorch3d.structures import Meshes
from pytorch3d.io import load_obj
from pytorch3d.renderer import (
    look_at_view_transform,
    OrthographicCameras,
    FoVPerspectiveCameras, 
    PointLights, 
    RasterizationSettings, 
    MeshRenderer, 
    MeshRasterizer,  
    SoftPhongShader,
    TexturesVertex
)
import torch
logger = log.getLogger('PyRenderer')


class FaceRenderer: 
    fr_window = None
    ctrl_window = None

    def __init__(self, mesh: Union[Meshes, str], height=640, width=360, wireframe=True) -> None:
        self._height = height
        self._width = width
        with dpg.texture_registry(show=False):
            self.__texture_id = dpg.add_dynamic_texture(width, height, np.ones((height, width, 4), dtype=np.uint8)*200, tag='__face_renderer_texture_tag')
        
        if isinstance(mesh, Meshes):
            self.mesh = mesh
        elif mesh == 'mediapipe':
            verts, faces, aux = load_obj('examples/models/face_mesh.obj')
            verts_rgb = torch.ones_like(verts)[None] # (1, V, 3)
            verts_rgb[..., 0] = 69/255
            verts_rgb[..., 1] = 145/255
            verts_rgb[..., 2] = 197/255
            textures = TexturesVertex(verts_rgb)
            self.mesh = Meshes(verts=[verts], faces=[faces.verts_idx], textures=textures)
        elif mesh == 'fuze':
            verts, faces, aux = load_obj('examples/models/fuze.obj')
            verts_rgb = torch.ones_like(verts)[None] # (1, V, 3)
            verts_rgb[..., 0] = 69/255
            verts_rgb[..., 1] = 145/255
            verts_rgb[..., 2] = 197/255
            textures = TexturesVertex(verts_rgb)
            self.mesh = Meshes(verts=[verts], faces=[faces.verts_idx], textures=textures)
        else:
            raise NotImplementedError(f'Unrecognized mesh or topology: {mesh}')
        # print(verts.shape, verts.min(), verts.max())

        R, T = look_at_view_transform(10.0, 0, 0)
        self.init_camera_pose = (R, T)
        self.cameras = OrthographicCameras(R=R, T=T, focal_length=0.1)
        # self.cameras = FoVPerspectiveCameras(R=R, T=T, fov=60)
        logger.info(self.init_camera_pose)
        
        pose = np.zeros((4, 4))
        # print(T.shape)
        pose[:3, :3] = R
        pose[:3, -1] = T
        # print(pose)
        self.trackball = Trackball(pose=pose, size=(width, height), scale=1.0)

        raster_settings = RasterizationSettings(
            image_size=(height, width, ), 
            blur_radius=0.0, 
            faces_per_pixel=1, 
        )

        lights = PointLights(device='cpu', location=[[0.0, 0.0, 0.0]])

        self.renderer = MeshRenderer(
            rasterizer=MeshRasterizer(
                cameras=self.cameras, 
                raster_settings=raster_settings
            ),
            shader=SoftPhongShader(
                device='cpu', 
                cameras=self.cameras,
                lights=lights
            )
        )

        self._is_focus = False
        self._is_clicked = False
        self._start_drag_pos = None
        


    def show_face_renderer(self, show_control=True):
        with dpg.window(label='Face Renderer', tag='_face_renderer_window') as self.fr_window:
            dpg.add_image('__face_renderer_texture_tag', tag='__face_render_image', width=self._width, height=self._height)
            pass

        with dpg.item_handler_registry() as fr_handler_reg:
            dpg.add_item_resize_handler(callback=self.resize_renderer)
            dpg.add_item_clicked_handler(callback=self.set_clicked, user_data='Clicked')
            dpg.add_item_focus_handler(callback=self.set_clicked, user_data='Focus')
            
        
        with dpg.handler_registry():
            # dpg.add_mouse_down_handler(callback=self.dragged, user_data='mouse down')
            
            def reset_pose():
                logger.info('Reset pose')
                self.trackball._n_pose = self.init_camera_pose
                self._render()
            dpg.add_key_press_handler(dpg.mvKey_R, callback=reset_pose)
            dpg.add_mouse_release_handler(callback=self.set_unclicked, )
            dpg.add_mouse_drag_handler(callback=self.dragged, )
            
            
        
        dpg.bind_item_handler_registry('__face_render_image', fr_handler_reg)
        
        width = 100
        with dpg.window(label='FR Control panel', show=show_control) as self.ctrl_window:
            dpg.add_combo(['cuda', 'cpu', 'mps'], label='Device')
            dpg.add_drag_float(label='Dist', tag='__fr_ctrl_panel_dist', default_value=10.0, min_value=-90, max_value=90)
            dpg.add_drag_float(label='Elev', tag='__fr_ctrl_panel_elev', default_value=0.0, min_value=-90, max_value=90)
            dpg.add_drag_float(label='Azim', tag='__fr_ctrl_panel_azim', default_value=0.0, min_value=-90, max_value=90)

            # dpg.add_checkbox(label='Wireframe', tag='__fr_ctrl_panel_wireframe', )
            # dpg.add_button(label='Center Mesh', callback=self.center_mesh, width=width)
            # dpg.add_button(label='Up Mesh', callback=self.up_mesh, width=width)
            dpg.add_button(label='Render', callback=self._render, width=width)
            pass
        self._render()

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
            self.trackball.set_state(Trackball.STATE_ROTATE)
            self.trackball.down(self._start_drag_pos)
        elif mouse_coord[0] == 0 and mouse_coord[1] == 0:
            # ghost drag
            return 
        self.trackball.drag(mouse_coord)
        self._render()
        return 

    def update_mesh(self, vertex:np.ndarray):        
        if vertex.shape != self.mesh._verts_padded.shape:
            logger.error(f'Shape mismatch: {vertex.shape} != vertex_array.shape')
            return
        self.mesh._verts_padded = vertex
        self._render()
    
    @torch.no_grad()
    def _render(self):
        """Trigger a re-render event"""
        # pose = self.trackball.pose.copy()
        # self._camera_node.matrix = pose
        d, e, a = dpg.get_value('__fr_ctrl_panel_dist'), dpg.get_value('__fr_ctrl_panel_elev'), dpg.get_value('__fr_ctrl_panel_azim')
        R, T = look_at_view_transform(d, e, a)
        self.cameras.T = T
        self.cameras.R = R
        image = self.renderer(self.mesh)[0].numpy() * 255
        
        print(f'Render {image.shape}, {image[:, :, -1].max()}')
        texture_data = numpy2texture_data(image, bgr=False)
        dpg.set_value('__face_renderer_texture_tag', texture_data)
        logger.debug('Updated image')
        # print(f'rendered')



    def resize_renderer(self):
        # print('resize_renderer')
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
            # print('resize_renderer')
        