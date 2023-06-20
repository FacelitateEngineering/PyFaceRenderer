import trimesh
import pyrender

fuze_trimesh = trimesh.load('examples/models/face_mesh.obj')
mesh = pyrender.Mesh.from_trimesh(fuze_trimesh, wireframe=False)
scene = pyrender.Scene(bg_color=[0.1]* 4, ambient_light=[0.4]* 4)
scene.add(mesh)
pyrender.Viewer(scene, use_raymond_lighting=True)
