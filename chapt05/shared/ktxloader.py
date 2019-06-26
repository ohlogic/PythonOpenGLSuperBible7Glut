#!/usr/bin/python3

import sys
import time 
import os
import time
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


class header:
    identifier=''    # [12]
    endianness=0     # unsigned int
    gltype=0
    gltypesize=0
    glformat=0
    glinternalformat=0
    glbaseinternalformat=0
    pixelwidth=0
    pixelheight=0
    pixeldepth=0
    arrayelements=0
    faces=0
    miplevels=0
    keypairbytes=0

class keyvaluepair:
    size =0
    rawbytes=[]    # unsigned char  [4]


def swap16(u16):
    pass
    
def swap32(u32):
    pass

def calculate_stride(h, width, pad = 4):

    channels = 0;

    if (GL_RED == h.glbaseinternalformat):
        channels = 1;
    elif (GL_RG == h.glbaseinternalformat):
        channels = 2;
    elif (GL_BGR == h.glbaseinternalformat or GL_RGB == h.glbaseinternalformat):
        channels = 3;
    elif (GL_BGRA == h.glbaseinternalformat or GL_RGBA  == h.glbaseinternalformat):
        channels = 4;

    stride = h.gltypesize * channels * width
    stride = (stride + (pad - 1)) & ~(pad - 1)
    return stride


def calculate_face_size(h):

    stride = calculate_stride(h, h.pixelwidth)
    return stride * h.pixelheight


identifier = 0xAB, 0x4B, 0x54, 0x58, 0x20, 0x31, 0x31, 0xBB, 0x0D, 0x0A, 0x1A, 0x0A


class KTXObject:

    def __init__(self):
        pass

    def ktx_load(self, filename, tex = 0):
    
    #try:

        ptr=0
        
        temp = GLuint
        retval = GLuint
        
        data_start=0
        data_end=0
        data=''
        target = GL_NONE
        h = header()
        data = numpy.fromfile(filename, dtype=np.byte)
        filesize = data.size
        
        int_data = np.array(data[:12], dtype=np.ubyte)
        ptr = 12
        
        good = True
        for i in range(len(identifier)):
            if (int_data[i] != identifier[i]):
                good = False
            else:
                print ('identifier', hex(identifier[i]) , " = ", hex(int_data[i]))
        
        print ('result, good identifier:', good )
        
        a = ''
        for i in range(len(identifier)):
            a+=chr(identifier[i])

        h.identifier = a
        print('id:', h.identifier)
        
        
        int_data = np.frombuffer(np.array(data[12:12+4*13], dtype=np.byte), dtype=np.uint32)
        ptr += 4*13
        
        
        h.endianness, \
        h.gltype, \
        h.gltypesize, \
        h.glformat, \
        h.glinternalformat, \
        h.glbaseinternalformat, \
        h.pixelwidth, \
        h.pixelheight, \
        h.pixeldepth, \
        h.arrayelements, \
        h.faces, \
        h.miplevels, \
        h.keypairbytes = int_data

        print('data:', hex(h.endianness))
        
        if (h.endianness == 0x04030201):
            
            # therefore little endian
            if (data[12] == 1 and data[13] == 2 and data[14] == 3 and data[15] == 4):
                print ('little endian')
            else:
                print ('somethings wrong endian?')
            
            # // No swap needed
            pass 
            
        elif (h.endianness == 0x01020304):
            pass
            #int.from_bytes(b'\xa3\x8eq\xb5', 'little')
            #np.frombuffer(b'\xa3\x8eq\xb5', dtype='<u')
            
        
        # // Guess target (texture type)
        if (h.pixelheight == 0):
        
            if (h.arrayelements == 0):
                target = GL_TEXTURE_1D;
            else:
                target = GL_TEXTURE_1D_ARRAY;
            
        elif (h.pixeldepth == 0):
        
            if (h.arrayelements == 0):
            
                if (h.faces == 0):
                    target = GL_TEXTURE_2D;
                else:
                    target = GL_TEXTURE_CUBE_MAP;
            else:
            
                if (h.faces == 0):
                    target = GL_TEXTURE_2D_ARRAY;
                else:
                    target = GL_TEXTURE_CUBE_MAP_ARRAY;
        else:
        
            target = GL_TEXTURE_3D;
             
        print ('target:', target)
        
        
            # // Check for insanity...
        if (target == GL_NONE or                                   # // Couldn't figure out target
            (h.pixelwidth == 0) or                                 # // Texture has no width???
            (h.pixelheight == 0 and h.pixeldepth != 0)):             # // Texture has depth but no height???
            print ('something wrong with the ktx file, exiting')
            sys.exit()
        
        #temp = tex;
        if (tex == 0):
            tex = glGenTextures(1)
        
        glBindTexture(target, tex)

        data_start = ptr + h.keypairbytes
        
        dt = data[data_start:]
        
        if (h.miplevels == 0):
            h.miplevels = 1;
        
        if (target == GL_TEXTURE_2D):
            if (h.gltype == GL_NONE):
                print ('it equals none')
            else:
                print ('we have a gltype FOUND!')
                
                glTexStorage2D(GL_TEXTURE_2D, h.miplevels, h.glinternalformat, h.pixelwidth, h.pixelheight)
                
                #p = data
                height = h.pixelheight
                width = h.pixelwidth
                glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
                
                for i in range(0, h.miplevels):
                    glTexSubImage2D(GL_TEXTURE_2D, i, 0, 0, width, height, h.glformat, h.gltype, data[ptr:]);
                    ptr += height * calculate_stride(h, width, 1);
                    
                    height >>= 1
                    width >>= 1
                    if (height == 0):
                        height = 1
                    if (width == 0):
                        width = 1
                        
                    # what do I do here if more than one miplevels????, unfamiliar with the >>= operator
    #except:
    #    print("error reading file {}".format(filename))

        return tex