import numpy as np
from OpenGL.GL import *
from pyrender.constants import FLOAT_SZ

def upload_vertex_data(primitive):
    print('upload_vertex_data')
    vertexbuffer = primitive._buffers[0]
    glBindVertexArray(primitive._vaid)
    glBindBuffer(GL_ARRAY_BUFFER, vertexbuffer)
    print('glBindBuffer(GL_ARRAY_BUFFER, vertexbuffer) finished')

    if hasattr(primitive, 'face_renderer_buffer'):
        print('hasattr(primitive, ')
        primitive.face_renderer_buffer[:, :3] = primitive.positions
    else:
        print('first time')
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
        print('set buffer')
        primitive.face_renderer_buffer = vertex_data
        print('done setting buffer')
    
    print('before np.ascontiguousarray')
    vertex_data = np.ascontiguousarray(
        primitive.face_renderer_buffer.flatten().astype(np.float32)
    )
    print(f'vertex_data: {vertex_data.shape} {vertex_data.dtype}')
    glBufferSubData( GL_ARRAY_BUFFER, 0, FLOAT_SZ * len(vertex_data), vertex_data,)