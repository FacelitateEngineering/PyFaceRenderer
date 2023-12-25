import dearpygui.dearpygui as dpg
from PyFaceRenderer import FaceRenderer
import logging as log
import mediapipe as mp
import cv2
import code
import numpy as np

log.basicConfig(level='DEBUG')
dpg.create_context()
dpg.configure_app(docking=True, docking_space=True, )
dpg.create_viewport(title=f'PyFaceRenderer ARKit Sample', width=700, height=640, always_on_top=True, )

fr = FaceRenderer('arkit', )
fr.show_face_renderer(show_control=True)
fr._render()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()