from pathlib import Path
import logging as log
import trimesh
import pickle
import argparse
from tqdm import tqdm
log.basicConfig(level='DEBUG')
[log.getLogger(package).setLevel(log.ERROR) for package in  ['matplotlib', 'h5py._conv', 'git.cmd', 'tensorflow', 'OpenGL', 'trimesh', 'PyRenderer', 'torch', 'py.warnings', 'PIL', 'urllib3', 'trimesh', 'numba', ]] # disable printing

parser = argparse.ArgumentParser('Export a mesh sequence (*.objs) to an animation file for rendering')
parser.add_argument('animation_file', type=str, help='Path to the directory containing the mesh sequence')
parser.add_argument('--fps', type=int, default=25, help='Path to the directory containing the mesh sequence')

args = parser.parse_args()
animation_file = Path(args.animation_file)
sentence_folders = list(filter(lambda f: f.is_dir(), animation_file.glob("*")))
for sentence_folder in sentence_folders:
    folders = list(filter(lambda x: x.is_dir(), sentence_folder.glob('*')))
    for folder in folders:    
        objs = list((folder/'meshes').glob('*.obj'))
        objs.sort()
        if len(objs) == 0:
            log.info(f'No mesh found in {folder}')
            continue
            # exit(1) 
        output_filename = (Path('tmp') / f'{sentence_folder.stem}_{folder.stem}').with_suffix('.pickle')
        log.info(f'Rendering animation: {len(objs)} frames from {folder.parent.stem} -> {output_filename}')
        trimeshes = list(map(lambda o: trimesh.load(str(o), ), objs))
        # meshes = list(map(pyrender.Mesh.from_trimesh, trimeshes))
        output = {'data': []}
        output['metadata'] = {'fps': args.fps}
        if (folder / 'audio.wav').exists():
            output['metadata']['audio'] = folder / 'audio.wav'
            
        for _trimesh in tqdm(trimeshes):
            data = {'vertex': _trimesh.vertices}
            output['data'].append(data)
            
        output_filename.parent.mkdir(exist_ok=True, parents=True)
        pickle.dump(output, open(output_filename, 'wb'))
