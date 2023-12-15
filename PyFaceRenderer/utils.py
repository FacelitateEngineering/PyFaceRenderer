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
    return np.array([[mx[0], my[0], mz[0], 0], [mx[1], my[1], mz[1], 0], [mx[2], my[2], mz[2], 0], [*eye, 1]]).T

def rot2quat(roll, pitch, yaw):
  """
  Convert an Euler angle to a quaternion.
   
  Input
    :param roll: The roll (rotation around x-axis) angle in radians.
    :param pitch: The pitch (rotation around y-axis) angle in radians.
    :param yaw: The yaw (rotation around z-axis) angle in radians.
 
  Output
    :return qx, qy, qz, qw: The orientation in quaternion [x,y,z,w] format
  """
  qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
  qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
  qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
  qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
  return [qx, qy, qz, qw]