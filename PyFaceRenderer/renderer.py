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
logger = log.getLogger('PyRenderer')






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

        self.scene.add_node(self._camera_node)
        self.scene.main_camera_node = self._camera_node
        self._camera_node = Node(matrix=camera_pose, camera=self.camera)


        # self.scene.add(self.camera, pose=camera_pose)
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
            dpg.add_item_resize_handler(callback=self.resize_renderer)

        dpg.bind_item_handler_registry(self.fr_window, fr_handler_reg)
        with dpg.window('FR Control panel', show=show_control) as self.ctrl_window:
            pass


    def update_mesh(self, vertex:np.ndarray):
        vertex_array = self.mesh.primitives[0].position
        if vertex.shape != vertex_array.shape:
            logger.error(f'Shape mismatch: {vertex.shape} != vertex_array.shape')
            return
        self.mesh.primitives[0].position = vertex
        self.__update()

    # def update_camera_angle(self, camera_angle):

    #     self.__update()
    #     return    

    def _create_direct_light(self):
        light = DirectionalLight(color=np.ones(3), intensity=1.0)
        n = Node(light=light, matrix=np.eye(4))
        return n
    
    def _render(self):
        """Render the scene into the framebuffer and flip.
        """
        scene = self.scene
        self._camera_node.matrix = self._trackball.pose.copy()

        # Set lighting
        vli = self.viewer_flags['lighting_intensity']
        if self.viewer_flags['use_raymond_lighting']:
            for n in self._raymond_lights:
                n.light.intensity = vli / 3.0
                if not self.scene.has_node(n):
                    scene.add_node(n, parent_node=self._camera_node)
        else:
            self._direct_light.light.intensity = vli
            for n in self._raymond_lights:
                if self.scene.has_node(n):
                    self.scene.remove_node(n)

        if self.viewer_flags['use_direct_lighting']:
            if not self.scene.has_node(self._direct_light):
                scene.add_node(
                    self._direct_light, parent_node=self._camera_node
                )
        elif self.scene.has_node(self._direct_light):
            self.scene.remove_node(self._direct_light)

        flags = RenderFlags.NONE
        if self.render_flags['flip_wireframe']:
            flags |= RenderFlags.FLIP_WIREFRAME
        elif self.render_flags['all_wireframe']:
            flags |= RenderFlags.ALL_WIREFRAME
        elif self.render_flags['all_solid']:
            flags |= RenderFlags.ALL_SOLID

        if self.render_flags['shadows']:
            flags |= RenderFlags.SHADOWS_DIRECTIONAL | RenderFlags.SHADOWS_SPOT
        if self.render_flags['vertex_normals']:
            flags |= RenderFlags.VERTEX_NORMALS
        if self.render_flags['face_normals']:
            flags |= RenderFlags.FACE_NORMALS
        if not self.render_flags['cull_faces']:
            flags |= RenderFlags.SKIP_CULL_FACES

        color, depth = self._renderer.render(self.scene, flags)



    def resize_renderer(self):
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
        self._trackball.resize((img_width, img_height))
