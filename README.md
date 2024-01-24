# PyFaceRenderer
DearPyGui-based Face renderer

This package uses an offscreen renderer for rendering face models, and display the result using DearPyGui.

This doesn't do much beside letting you visualize your face recognition result.

![Alt text](data/screenshot.png?raw=true "Screenshot")


### Install
This repository uses [a fork of pyrender]((https://github.com/FacelitateEngineering/pyrender)) which computes vertex for linear blendshape on GLSL shader for slightly faster interactive manipulation. 
<!-- To install follow the instruction [here] -->
It would be installed via requirement.txt. 


### Animation Format
Animation are simply dictionaries stored as a pickle file.
```python
animation =
{
    'data': [
        {'blendshapes': 
            {
                blendshape_1: value, 
                blendshape_2: value, 
                ...
            }
        }
        ]
    'metadata': {
        'fps': 30, 
        'audio': 'path_to_audio_file'
        }
}
```
