import numpy as np
from OpenGL.GL import *
from pyrender.constants import FLOAT_SZ

def upload_vertex_data(primitive):
    vertexbuffer = primitive._buffers[0]
    glBindVertexArray(primitive._vaid)
    glBindBuffer(GL_ARRAY_BUFFER, vertexbuffer)

    if hasattr(primitive, 'face_renderer_buffer'):
        primitive.face_renderer_buffer[primitive.face_renderer_indice] = primitive.positions.reshape(-1).astype(np.float32)
    else:
        # positions
        vertex_data = primitive.positions
        n_vertex = vertex_data.shape[0]
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
        vertex_data = np.ascontiguousarray(
            vertex_data.flatten().astype(np.float32)
        )

        primitive.face_renderer_buffer = vertex_data
        total_attr_size = sum(attr_sizes)
        _idx = np.arange(n_vertex) * total_attr_size
        indice_array = np.concatenate([_idx, _idx+1, _idx+2])
        indice_array.sort()
        primitive.face_renderer_indice = indice_array

    glBufferSubData( GL_ARRAY_BUFFER, 0, FLOAT_SZ * len(primitive.face_renderer_buffer), primitive.face_renderer_buffer,)