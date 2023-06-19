import dearpygui.dearpygui as dpg
from PyFaceRenderer import FaceRenderer
dpg.create_context()
dpg.configure_app(docking=True, docking_space=True, )
dpg.create_viewport(title=f'DearPyGui Drag test', width=1920, height=1080, always_on_top=False, )
fr = FaceRenderer()
fr.show_face_renderer()
dpg.start_dearpygui()