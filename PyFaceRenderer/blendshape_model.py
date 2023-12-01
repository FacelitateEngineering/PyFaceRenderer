import pyrender
from typing import List, Union, Optional, Iterable
import trimesh
import numpy as np
from copy import copy

class BlendshapeModel:
    def __init__(self, meshes:Union[List[pyrender.Mesh], List[str]], blendshape_names:Optional[List[str]]) -> None:
        if len(meshes) == 0:
            raise ValueError("No meshes provided")
        if isinstance(meshes[0], str):
            self.meshes = list[map(lambda path: pyrender.Mesh.from_trimesh(trimesh.load(path)), meshes)]
        elif isinstance(meshes[0], pyrender.Mesh):
            self.meshes = meshes
        else:
            raise ValueError("Invalid mesh type")
        if blendshape_names is not None:
            assert len(blendshape_names) == len(meshes), "Number of blendshape names must match number of meshes"
        self.blendshape_names = blendshape_names
        self.vertices = np.stack([m.primitives[0].position for m in self.meshes])
        pass


    @property
    def n_blendshapes(self) -> int:
        return len(self.meshes)
    

    def get_mesh(self, coe) -> np.ndarray:
        assert len(coe) == self.n_blendshapes, "Number of blendshapes must match number of coefficients"
        out = np.sum(coe[..., None, None] * self.vertices, axis=0) 
        return out
    
if __name__ == "__main__":
    trimesh = trimesh.load('data/models/face_mesh.obj')
    mesh = pyrender.Mesh.from_trimesh(trimesh)
    import code
    code.interact(local=locals())
    