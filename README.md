# PyFaceRenderer
DearPyGui-based Face renderer

This package uses an offscreen renderer for rendering face models, and display the result using DearPyGui.

This doesn't do much beside letting you visualize your face recognition result.

![Alt text](data/screenshot.png?raw=true "Screenshot")

Windows offscreen rendering capability is spotty so this is only really working on linux. 
This however, runs quite well as we test in WSL. 

### Install
This repository uses [a fork of pyrender]((https://github.com/FacelitateEngineering/pyrender)) which computes vertex for linear blendshape on GLSL shader for slightly faster interactive manipulation. 
<!-- To install follow the instruction [here] -->
It would be installed via requirement.txt. 


### Wayland (Ubuntu)
On ubuntu the context might return 0
See more: https://github.com/mcfletch/pyopengl/issues/104
But a potential fix for now is to directly edit 
`site-packages/OpenGL/contextdata.py`

```python
def getContext( context = None ):
    """Get the context (if passed, just return)
    
    context -- the context ID, if None, the current context
    """
    if context is None:
        context = platform.GetCurrentContext()
        # if context == 0:
        #     from OpenGL import error
        #     raise error.Error(
        #         """Attempt to retrieve context when no valid context"""
        #     )
    return context
```


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
