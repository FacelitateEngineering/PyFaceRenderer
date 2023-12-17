import pyrender
from typing import List, Union, Optional, Iterable
import trimesh
import numpy as np
from copy import copy
from pathlib import Path

class BlendshapeModel:
    def __init__(self, neutral_mesh:Union[Path, str], blendshapes: np.ndarray, blendshape_names:Optional[List[str]]=None) -> None:
        self.trimesh = trimesh.load(neutral_mesh)
        self.neutral_mesh = pyrender.Mesh.from_trimesh(self.trimesh)
        self.neutral_position = np.asarray(self.neutral_mesh.primitives[0].positions.copy())
        self.blendshape_names = blendshape_names
        self.blendshapes = blendshapes

    @property
    def n_blendshapes(self) -> int:
        return len(self.blendshapes)    

    def get_mesh(self, coe:np.ndarray=None) -> np.ndarray:
        if coe is None:
            coe = np.zeros(self.n_blendshapes)
            coe[0] = 1.0 # neutral
        assert len(coe.shape) == 1, coe.shape
        assert len(coe) == self.n_blendshapes, "Number of blendshapes must match number of coefficients"
        out = np.sum(coe[..., None, None] * self.blendshapes, axis=0) + self.neutral_position
        return out

class ARKitModel(BlendshapeModel):
    def __init__(self, ) -> None:
        neutral_mesh = Path('deformation_transfer_ARkit_blendshapes/data/ARKit_blendShapes/Neutral.obj')
        blendshapes = np.load('data/ARKit_blendshapes.npy')
        with open('data/ARKit_blendshapes_names.txt', 'r') as f:
            bs_names = f.read().split('\n')
        super().__init__(neutral_mesh, blendshapes, bs_names)

if __name__ == "__main__":
    arkit = ARKitModel()
    import code
    code.interact(local=locals())