import dearpygui.dearpygui as dpg
from PyFaceRenderer import FaceRenderer
import logging as log
import mediapipe as mp
import cv2
import code
import numpy as np

mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    min_detection_confidence=0.5)

image = cv2.imread('data/face.png')
rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) # RGB形式に変換
rgb_image = cv2.resize(rgb_image, (1080, 1920))
results = face_mesh.process(rgb_image) # 顔メッシュを計算

landmark_array = np.array([(landmark.x, landmark.y, landmark.z) for landmark in results.multi_face_landmarks[0].landmark])
# landmark_array *= -1
landmark_array[:, 0] *= 1080
landmark_array[:, 1] *= 1920
landmark_array[:, 2] *= 1080
# code.interact(local=locals())

log.basicConfig(level='DEBUG')
dpg.create_context()
dpg.configure_app(docking=True, docking_space=True, )
pose = np.eye(4)
pose[1, 1] = -1
pose[2, 2] = -1
pose[2, 3] = -5
dpg.create_viewport(title=f'PyFaceRenderer Mediapipe Sample', width=1920, height=1080, always_on_top=True, )

fr = FaceRenderer('mediapipe', default_camera_pose=pose)
fr.show_face_renderer(show_control=True)
fr.update_mesh(landmark_array)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()   