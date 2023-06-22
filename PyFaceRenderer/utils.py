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

def normalize(vector):
    return vector / (np.linalg.norm(vector))


def lookat(eye, target, up):
    mz = normalize( (eye[0]-target[0], eye[1]-target[1], eye[2]-target[2]) ) # inverse line of sight
    mx = normalize( np.cross( up, mz ) )
    my = normalize( np.cross( mz, mx ) )
    tx =  np.dot( mx, eye )
    ty =  np.dot( my, eye )
    tz = -np.dot( mz, eye )
    return np.array([[mx[0], my[0], mz[0], 0], [mx[1], my[1], mz[1], 0], [mx[2], my[2], mz[2], 0], [tx, ty, tz, 1]])
