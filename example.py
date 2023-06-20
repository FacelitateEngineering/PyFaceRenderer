import dearpygui.dearpygui as dpg
from PyFaceRenderer import FaceRenderer
dpg.create_context()
dpg.configure_app(docking=True, docking_space=True, )
dpg.create_viewport(title=f'PyFaceRenderer Sample', width=1920, height=1080, always_on_top=True, )
fr = FaceRenderer('fuze', wireframe=False)
fr.show_face_renderer(show_control=True)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui() 