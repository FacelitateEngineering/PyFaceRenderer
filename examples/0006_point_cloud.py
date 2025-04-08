import dearpygui.dearpygui as dpg
from PyFaceRenderer import FaceRenderer
import logging as log
from pathlib import Path
import numpy as np
from PyFaceRenderer.primitive_extension import upload_pose_data, upload_vertex_data
log.basicConfig(level='ERROR')
dpg.create_context()
dpg.configure_app(docking=True, docking_space=True, )
dpg.create_viewport(title=f'PyFaceRenderer pointcloud Sample', width=770, height=640, always_on_top=True, )
npys = list(Path('/mnt/d/p3d').glob("*.npy"))
npys.sort()
points = np.load(npys[0])
fr = FaceRenderer('pointcloud', camera_type='persp', n_points=len(points))
fr.show_face_renderer(show_control=True)
fr._render()

def timeline_callback(s, a):
    fr._renderer._platform.make_current()
    a = np.clip(a, 0, len(npys)-1)
    # print(a)
    npy = npys[a]
    data = np.load(npy, )
    # print(f'data: {data[:, 0].max() - data[:, 0].min()}')
    # print(f'data: {data[:, 1].max() - data[:, 1].min()}')
    # print(f'data: {data[:, 2].max() - data[:, 2].min()}')
    
    tfs = np.tile(np.eye(4), (len(data), 1, 1))
    tfs[:,:3,3] = data
    # print(f'fr.mesh._primitives[0].poses: {fr.mesh._primitives[0].poses.shape}')
    # fr.mesh._primitives[0].positions = fr._init_position * a / 50
    # upload_vertex_data(fr.mesh._primitives[0])
    
    fr.mesh._primitives[0].poses = tfs
    upload_pose_data(fr.mesh._primitives[0])
    # print()
    fr._render()
    return 

dpg.configure_item('__fr_ctrl_panel_timeline', callback=timeline_callback)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()