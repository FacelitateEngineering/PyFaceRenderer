from pathlib import Path
import pyrender
from typing import List, Union, Optional, Iterable
import trimesh
import numpy as np
from copy import copy
from pathlib import Path


objs = list(Path('deformation_transfer_ARkit_blendshapes/data/ARKit_blendShapes').glob('*.obj'))
objs.sort()
idx = objs.index(Path('deformation_transfer_ARkit_blendshapes/data/ARKit_blendShapes/Neutral.obj'))
neutral_mesh = objs.pop(idx)
bs_names = list(map(lambda obj: obj.stem, objs))

def get_v(path):
    return pyrender.Mesh.from_trimesh(trimesh.load(path)).primitives[0].positions
blendshapes = np.stack([get_v(m) for m in objs], axis=0)
neutral_mesh = get_v(neutral_mesh)
blendshape_delta = blendshapes - neutral_mesh[None]
np.save('data/ARKit_blendshapes.npy', blendshape_delta)
with open('data/ARKit_blendshapes_names.txt', 'w') as f:
    f.write('\n'.join(bs_names))
print('Exported ARKit blendshapes')