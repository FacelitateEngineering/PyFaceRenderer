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
from .utils import numpy2texture_data
from PIL import Image
logger = log.getLogger('PyRenderer')


class FaceRenderer: 
    fr_window = None
    ctrl_window = None

    def __init__(self, mesh: Union[pyrender.Mesh, str], height=640, width=360, wireframe=True) -> None:
        self._height = height
        self._width = width
        with dpg.texture_registry(show=False):
            self.__texture_id = dpg.add_dynamic_texture(width, height, np.ones((height, width, 4), dtype=np.uint8)*200, tag='__face_renderer_texture_tag')
        
        if isinstance(mesh, pyrender.Mesh):
            self.mesh = mesh
        elif mesh == 'mediapipe':
            self.mesh = pyrender.Mesh.from_trimesh(trimesh.load('examples/models/face_mesh.obj'), wireframe=wireframe)
        elif mesh == 'fuze':
            self.mesh = pyrender.Mesh.from_trimesh(trimesh.load('examples/models/fuze.obj'), wireframe=wireframe)
        else:
            raise NotImplementedError(f'Unrecognized mesh or topology: {mesh}')
        self.scene = pyrender.Scene(bg_color=[0.3, 0.3, 0.4, 0.2], ambient_light=[0.4]* 4)
        self.scene.add(self.mesh)
        self.camera = OrthographicCamera(
            xmag=1.0, ymag=1.0,
            znear=0.05,
            zfar=100.0, 
        )
        
        s = np.sqrt(2)/2
        camera_pose = np.array([
            [0.0, -s,   s,   0.3],
            [1.0,  0.0, 0.0, 0.0],
            [0.0,  s,   s,   0.35],
            [0.0,  0.0, 0.0, 1.0],
        ])
        
        self.trackball = Trackball(pose=camera_pose, size=(width, height), scale=1.0)
        self._camera_node = Node(matrix=camera_pose, camera=self.camera)
        self.scene.add_node(self._camera_node)
        self.scene.main_camera_node = self._camera_node
        

        # self.scene.add(self.camera, pose=camera_pose)
        light = pyrender.SpotLight(color=np.ones(3), intensity=3.0,
                                innerConeAngle=np.pi/16.0,
                                outerConeAngle=np.pi/6.0)
        self.scene.add(light, pose=camera_pose)
        self._renderer = pyrender.OffscreenRenderer(width, height)
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
            dpg.add_mouse_release_handler(callback=self.set_unclicked, )
            
            dpg.add_mouse_drag_handler(callback=self.dragged, )
            
        
        dpg.bind_item_handler_registry('__face_render_image', fr_handler_reg)
        
        with dpg.window(label='FR Control panel', show=show_control) as self.ctrl_window:
            dpg.add_checkbox(label='Wireframe', tag='__fr_ctrl_panel_wireframe', )
            dpg.add_button(label='Render', callback=self._render)
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
        # print(f'set_unclicked')
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
        vertex_array = self.mesh.primitives[0].position
        if vertex.shape != vertex_array.shape:
            logger.error(f'Shape mismatch: {vertex.shape} != vertex_array.shape')
            return
        self.mesh.primitives[0].position = vertex
        self._render()
    
    def _render(self):
        """Trigger a re-render event"""
        self._camera_node.matrix = self.trackball.pose.copy()
        flags = RenderFlags.NONE
        if dpg.get_value('__fr_ctrl_panel_wireframe'):
            flags |= RenderFlags.FLIP_WIREFRAME

        color, depth = self._renderer.render(self.scene, flags)
        texture_data = numpy2texture_data(color, bgr=False)
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
        