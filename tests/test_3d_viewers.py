import trimesh
import pyrender

fuze_trimesh = trimesh.load('examples/models/face_mesh.obj')
mesh = pyrender.Mesh.from_trimesh(fuze_trimesh, wireframe=False)
scene = pyrender.Scene()
scene.add(mesh)
pyrender.Viewer(scene, use_raymond_lighting=True)
