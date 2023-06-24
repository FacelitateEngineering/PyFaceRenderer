import numpy as np
from OpenGL.GL import *
from pyrender.constants import FLOAT_SZ

def upload_vertex_data(primitive):
    vertexbuffer = primitive._buffers[0]
    glBindVertexArray(primitive._vaid)
    glBindBuffer(GL_ARRAY_BUFFER, vertexbuffer)
    # positions
    vertex_data = primitive.positions
    attr_sizes = [3]

    # Normals
    if primitive.normals is not None:
        vertex_data = np.hstack((vertex_data, primitive.normals))
        attr_sizes.append(3)

    # Tangents
    if primitive.tangents is not None:
        vertex_data = np.hstack((vertex_data, primitive.tangents))
        attr_sizes.append(4)

    # Texture Coordinates
    if primitive.texcoord_0 is not None:
        vertex_data = np.hstack((vertex_data, primitive.texcoord_0))
        attr_sizes.append(2)
    if primitive.texcoord_1 is not None:
        vertex_data = np.hstack((vertex_data, primitive.texcoord_1))
        attr_sizes.append(2)

    # Color
    if primitive.color_0 is not None:
        vertex_data = np.hstack((vertex_data, primitive.color_0))
        attr_sizes.append(4)

    # TODO JOINTS AND WEIGHTS
    # PASS

    # Copy data to buffer
    vertex_data = np.ascontiguousarray(
        vertex_data.flatten().astype(np.float32)
    )
    glBufferSubData( GL_ARRAY_BUFFER, 0, FLOAT_SZ * len(vertex_data), vertex_data,)