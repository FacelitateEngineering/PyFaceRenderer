import dearpygui.dearpygui as dpg
from PyFaceRenderer import FaceRenderer
import logging as log
log.basicConfig(level='DEBUG')
dpg.create_context()
dpg.configure_app(docking=True, docking_space=True, )
dpg.create_viewport(title=f'EMOTE Sample', width=1920, height=1080, always_on_top=True, )
fr = FaceRenderer('/Volumes/Home-NAS/EMOTE/M003_Neutral_2/meshes/00000.obj')
fr.show_face_renderer(show_control=True)


dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()   