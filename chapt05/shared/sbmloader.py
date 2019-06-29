#!/usr/bin/python3

import sys
import time 
import os
import math
import ctypes
import numpy.matlib 
import numpy as np 
try:
    from OpenGL.GLUT import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
    #from OpenGL.raw.GL.ARB.vertex_array_object import glGenVertexArrays, glBindVertexArray
except:
    print ('''
    ERROR: PyOpenGL not installed properly.
        ''')
    sys.exit()

sub_object = []

def SB6M_FOURCC(a,b,c,d):
    return ( (ord(a) << 0) | (ord(b) << 8) | (ord(c) << 16) | (ord(d) << 24) )

SB6M_MAGIC = SB6M_FOURCC('S','B','6','M')

SB6M_CHUNK_TYPE_INDEX_DATA      = SB6M_FOURCC('I','N','D','X')
SB6M_CHUNK_TYPE_VERTEX_DATA     = SB6M_FOURCC('V','R','T','X')
SB6M_CHUNK_TYPE_VERTEX_ATTRIBS  = SB6M_FOURCC('A','T','R','B')
SB6M_CHUNK_TYPE_SUB_OBJECT_LIST = SB6M_FOURCC('O','L','S','T')
SB6M_CHUNK_TYPE_COMMENT         = SB6M_FOURCC('C','M','N','T')
SB6M_CHUNK_TYPE_DATA            = SB6M_FOURCC('D','A','T','A')

class SB6M_HEADER:
    def __init__(self, data):
        int_data = np.frombuffer(np.array(data[:16], dtype=np.byte), dtype=np.uint32)
        self.magic, self.size, self.num_chunks, self.flags = int_data 
        print(self.magic, self.size, self.num_chunks, self.flags)

class SB6M_CHUNK_HEADER:
    def __init__(self, data, offset):
        int_data = np.frombuffer(np.array(data[offset:offset+8], dtype=np.byte), dtype=np.uint32)
        self.type, self.size = int_data

class SB6M_CHUNK_INDEX_DATA(SB6M_CHUNK_HEADER):
     def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+20], dtype=np.byte), dtype=np.uint32)
        self.index_type, self.index_count, self.index_data_offset = int_data

class SB6M_CHUNK_VERTEX_DATA(SB6M_CHUNK_HEADER):
     def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+20], dtype=np.byte), dtype=np.uint32)
        self.data_size, self.data_offset, self.total_vertices = int_data

class SB6M_CHUNK_VERTEX_DATA(SB6M_CHUNK_HEADER):
     def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+20], dtype=np.byte), dtype=np.uint32)
        self.data_size, self.data_offset, self.total_vertices = int_data

SB6M_VERTEX_ATTRIB_FLAG_NORMALIZED = 0x00000001
SB6M_VERTEX_ATTRIB_FLAG_INTEGER    = 0x00000002

class SB6M_VERTEX_ATTRIB_DECL:
    def __init__(self, data, offset):
        self.name = ''.join([chr(n) for n in data[offset:offset+64] if n > 30])
        int_data = np.frombuffer(np.array(data[offset+64:offset+84], dtype=np.byte), dtype=np.uint32)
        self.size, self.type, self.stride, self.flags, self.data_offset = int_data

class SB6M_VERTEX_ATTRIB_CHUNK(SB6M_CHUNK_HEADER):
    def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+12], dtype=np.byte), dtype=np.uint32)
        self.attrib_count = int_data[0]
        self.attrib_data = []
        for i in range(self.attrib_count):
            self.attrib_data.append(SB6M_VERTEX_ATTRIB_DECL(data, offset+12+i*84))

class SB6M_DATA_CHUNK(SB6M_CHUNK_HEADER):
    def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+20], dtype=np.byte), dtype=np.uint32)
        self.encoding, self.data_offset, self.data_length = int_data

class SB6M_SUB_OBJECT_DECL:
    def __init__(self, data, offset):
        int_data = np.frombuffer(np.array(data[offset:offset+8], dtype=np.byte), dtype=np.uint32)
        self.first, self.count = int_data

class SB6M_CHUNK_SUB_OBJECT_LIST(SB6M_CHUNK_HEADER):
    def __init__(self, data, offset):
        global sub_object
    
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+12], dtype=np.byte), dtype=np.uint32)
        self.count = int_data[0]
        #self.sub_object = []
        for i in range(self.count):

            sub_object.append(SB6M_SUB_OBJECT_DECL(data, offset+12+i*8))

class SB6M_CHUNK_HEADER_:
    chunk_type = 0
    chunk_name = ''
    size = 0

class SB6M_DATA_ENCODING:
    SB6M_DATA_ENCODING_RAW  = 0


class SB6M_CHUNK_COMMENT:
    header = SB6M_CHUNK_HEADER_()
    comment = []
    comment.append('')
    comment.append('')
    


def render(instance_count = 1, base_instance = 0):
    render_sub_object(0, instance_count, base_instance)


class SBMObject:

    def __init__(self):
        self.vao = GLuint(0)

    def get_sub_object_count(self):
        return len(sub_object)

    def get_sub_object_info(self, index):
       if (index >= len(sub_object)):
           return 0, 0
       return sub_object[index].first, sub_object[index].count

    def get_vao(self):
        return self.vao

    def load(self, filename):

        vertex_attrib_chunk = None
        vertex_data_chunk = None
        index_data_chunk = None
        sub_object_chunk = None
        data_chunk = None

        #try:
        data = numpy.fromfile(filename, dtype=np.byte)
        filesize = data.size

        header = SB6M_HEADER(data)
        offset = header.size

        for i in range(header.num_chunks):

            chunk = SB6M_CHUNK_HEADER(data, offset)
            if chunk.type == SB6M_CHUNK_TYPE_VERTEX_ATTRIBS:
                vertex_attrib_chunk = SB6M_VERTEX_ATTRIB_CHUNK(data, offset) 
            elif chunk.type == SB6M_CHUNK_TYPE_VERTEX_DATA:
                vertex_data_chunk = SB6M_CHUNK_VERTEX_DATA(data, offset)
            elif chunk.type == SB6M_CHUNK_TYPE_INDEX_DATA:
                index_data_chunk = SB6M_CHUNK_INDEX_DATA(data, offset) 
            elif chunk.type == SB6M_CHUNK_TYPE_SUB_OBJECT_LIST:
                sub_object_chunk = SB6M_CHUNK_SUB_OBJECT_LIST(data, offset)
            elif chunk.type == SB6M_CHUNK_TYPE_DATA:
                data_chunk = SB6M_DATA_CHUNK(data, offset) 
            elif chunk.type == SB6M_CHUNK_TYPE_COMMENT:
                print ('just comment')
            else:
                print ('am here')
                pass 
                #raise
                

            offset += chunk.size

        #except:
        #    print("error reading file {}".format(filename))

        print("finished reading")

        if vertex_data_chunk and vertex_attrib_chunk:
            start = vertex_data_chunk.data_offset
            end = start + vertex_data_chunk.data_size
            vertex_data = np.frombuffer(np.array(data[start:end], dtype=np.byte), dtype=np.float)

            data_buffer = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, data_buffer)
            glBufferData(GL_ARRAY_BUFFER, vertex_data, GL_STATIC_DRAW)

            self.vertexcount = vertex_data_chunk.total_vertices
            self.vao = glGenVertexArrays(1)
            glBindVertexArray(self.vao)

            for attrib_i, attrib in enumerate(vertex_attrib_chunk.attrib_data):
                if attrib.name=='position' or attrib.name=='map1': 
                    glVertexAttribPointer(attrib_i,
                        attrib.size, attrib.type,
                        GL_TRUE if (attrib.flags & SB6M_VERTEX_ATTRIB_FLAG_NORMALIZED) != 0 else GL_FALSE,
                        attrib.stride, ctypes.c_void_p(int(attrib.data_offset)))
                    glEnableVertexAttribArray(attrib_i)

    def render(self):

        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.vertexcount)