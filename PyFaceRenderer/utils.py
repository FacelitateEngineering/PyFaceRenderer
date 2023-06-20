import numpy as np
import platform 
_platform = platform.system().lower()

def numpy2texture_data(array, force_alpha=True, bgr=True):
    if bgr:
        frame = np.flip(array.copy(), 2)
    else:
        frame = array
    if ('darwin' in _platform or force_alpha) and (frame.shape[2] == 3):
        frame = np.concatenate((frame, np.ones((*frame.shape[:2], 1), dtype=np.uint8)*255), axis=-1)
    data = frame.ravel()
    data = np.asfarray(data, dtype='f')    
    data = np.true_divide(data, 255.0)
    return data
