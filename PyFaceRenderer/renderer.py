import dearpygui.dearpygui as dpg
import numpy as np
from pyrender.trackball import Trackball
from pyrender.camera import OrthographicCamera
import pyrender
import trimesh

def resize_renderer():
    window_width, window_height = dpg.get_item_rect_size('_face_renderer_window')
    window_height = window_height - 20
    aspect_ratio = 9/16
    if window_width/window_height > aspect_ratio: # too wide
        img_height = window_height
        img_width = int(window_height/16*9)
    else: # too tall
        img_height = int(window_width/9*16)
        img_width = window_width
    x_pos = int(window_width/2-img_width/2)
    dpg.set_item_height('__face_render_image', img_height)
    dpg.set_item_width('__face_render_image', img_width)
    dpg.set_item_pos('__face_render_image', (x_pos, 0))




class FaceRenderer: 
    fr_window = None
    ctrl_window = None

    def __init__(self, height=1920, width=1080, wireframe=True) -> None:
        with dpg.texture_registry(show=False):
            self.__texture_id = dpg.add_dynamic_texture(width, height, np.zeros((height, width, 4), dtype=np.uint8))
        self.trackbacll = Trackball(size=(width, height), scale=1.0)
        self.mesh = pyrender.Mesh.from_trimesh(trimesh.load('examples/models/face_mesh.obj'), wireframe=wireframe)
        self.scene = pyrender.Scene()
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
        self.scene.add(self.camera, pose=camera_pose)
        light = pyrender.SpotLight(color=np.ones(3), intensity=3.0,
                                innerConeAngle=np.pi/16.0,
                                outerConeAngle=np.pi/6.0)
        self.scene.add(light, pose=camera_pose)
        self._renderer = pyrender.OffscreenRenderer(width, height)
        self._is_focus = False


        
    def show_face_renderer(self, show_control=True):
        with dpg.window('Face Renderer', tag='_face_renderer_window') as self.fr_window:
            dpg.add_image('__face_render_image')
            pass

        with dpg.handler_registry() as fr_handler_reg:
            dpg.add_item_resize_handler(callback=resize_renderer)

        dpg.bind_item_handler_registry(self.fr_window, fr_handler_reg)
        with dpg.window('FR Control panel', show=show_control) as self.ctrl_window:
            pass

    



    def __update(self):


        dpg.set_value()
        return 
