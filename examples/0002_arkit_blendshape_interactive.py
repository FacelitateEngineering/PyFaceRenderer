import dearpygui.dearpygui as dpg
from PyFaceRenderer import FaceRenderer
import logging as log

log.basicConfig(level='ERROR')
dpg.create_context()
dpg.configure_app(docking=True, docking_space=True, )
dpg.create_viewport(title=f'PyFaceRenderer ARKit Sample', width=700, height=640, always_on_top=True, )

fr = FaceRenderer('arkit', )
fr.show_face_renderer(show_control=True)
fr._render()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()