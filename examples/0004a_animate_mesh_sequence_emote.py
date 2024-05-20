from pathlib import Path
import logging as log
import trimesh
import pickle
import argparse
from tqdm import tqdm
log.basicConfig(level='DEBUG')

parser = argparse.ArgumentParser('Export a mesh sequence (*.objs) to an animation file for rendering')
parser.add_argument('animation_file', type=str, help='Path to the directory containing the mesh sequence')

args = parser.parse_args()
animation_file = Path(args.animation_file)
objs = list(animation_file.glob('*.obj'))
objs.sort()
output_filename = (Path('tmp') / animation_file.parent.stem).with_suffix('.pickle')
log.info(f'Rendering animation: {len(objs)} frames from {args.animation_file} -> {output_filename}')
trimeshes = list(map(lambda o: trimesh.load(str(o), ), objs))
# meshes = list(map(pyrender.Mesh.from_trimesh, trimeshes))
fps = 25
output = {'data': []}
output['metadata'] = {'fps': fps}
if (animation_file.parent / 'audio.wav').exists():
    output['metadata']['audio'] = animation_file.parent / 'audio.wav'
    
for _trimesh in tqdm(trimeshes):
    data = {'vertex': _trimesh.vertices}
    output['data'].append(data)
    
output_filename.parent.mkdir(exist_ok=True, parents=True)
pickle.dump(output, open(output_filename, 'wb'))