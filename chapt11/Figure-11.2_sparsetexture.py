#!/usr/bin/python3

import sys
import time
import ctypes

fullscreen = True
sys.path.append("./shared")

from sbmloader import SBMObject    # location of sbm file format loader
from ktxloader import KTXObject    # location of ktx file format loader
from textoverlay import OVERLAY_
from shader import shader_load, link_from_shaders

from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, \
    m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate, m3dScaleMatrix44, \
    scale, m3dLookAt, normalize

try:
    from OpenGL.GLUT import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
    #from OpenGL.raw.GL.ARB.vertex_array_object import glGenVertexArrays, glBindVertexArray
    from OpenGL.raw.GL.ARB.sparse_texture import GL_TEXTURE_SPARSE_ARB, glTexPageCommitmentARB
except:
    print ('''
    ERROR: PyOpenGL not installed properly.
        ''')
    sys.exit()

import numpy as np
from math import cos, sin
#import glm
identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

myobject = SBMObject()
ktxobject = KTXObject()
overlay = OVERLAY_()


PAGE_SIZE       = 128
TEX_SIZE        = 16 * PAGE_SIZE

texture = GLuint(0)
program = GLuint(0)
vao = GLuint(0)

class uniforms_:
    mv_matrix = GLint(0)
    vp_matrix = GLint(0)

uniforms = uniforms_()

bit_reversal_table = np.array([

    0x00, 0x80, 0x40, 0xc0, 0x20, 0xa0, 0x60, 0xe0,
    0x10, 0x90, 0x50, 0xd0, 0x30, 0xb0, 0x70, 0xf0,
    0x08, 0x88, 0x48, 0xc8, 0x28, 0xa8, 0x68, 0xe8,
    0x18, 0x98, 0x58, 0xd8, 0x38, 0xb8, 0x78, 0xf8,
    0x04, 0x84, 0x44, 0xc4, 0x24, 0xa4, 0x64, 0xe4,
    0x14, 0x94, 0x54, 0xd4, 0x34, 0xb4, 0x74, 0xf4,
    0x0c, 0x8c, 0x4c, 0xcc, 0x2c, 0xac, 0x6c, 0xec,
    0x1c, 0x9c, 0x5c, 0xdc, 0x3c, 0xbc, 0x7c, 0xfc,
    0x02, 0x82, 0x42, 0xc2, 0x22, 0xa2, 0x62, 0xe2,
    0x12, 0x92, 0x52, 0xd2, 0x32, 0xb2, 0x72, 0xf2,
    0x0a, 0x8a, 0x4a, 0xca, 0x2a, 0xaa, 0x6a, 0xea,
    0x1a, 0x9a, 0x5a, 0xda, 0x3a, 0xba, 0x7a, 0xfa,
    0x06, 0x86, 0x46, 0xc6, 0x26, 0xa6, 0x66, 0xe6,
    0x16, 0x96, 0x56, 0xd6, 0x36, 0xb6, 0x76, 0xf6,
    0x0e, 0x8e, 0x4e, 0xce, 0x2e, 0xae, 0x6e, 0xee,
    0x1e, 0x9e, 0x5e, 0xde, 0x3e, 0xbe, 0x7e, 0xfe,
    0x01, 0x81, 0x41, 0xc1, 0x21, 0xa1, 0x61, 0xe1,
    0x11, 0x91, 0x51, 0xd1, 0x31, 0xb1, 0x71, 0xf1,
    0x09, 0x89, 0x49, 0xc9, 0x29, 0xa9, 0x69, 0xe9,
    0x19, 0x99, 0x59, 0xd9, 0x39, 0xb9, 0x79, 0xf9,
    0x05, 0x85, 0x45, 0xc5, 0x25, 0xa5, 0x65, 0xe5,
    0x15, 0x95, 0x55, 0xd5, 0x35, 0xb5, 0x75, 0xf5,
    0x0d, 0x8d, 0x4d, 0xcd, 0x2d, 0xad, 0x6d, 0xed,
    0x1d, 0x9d, 0x5d, 0xdd, 0x3d, 0xbd, 0x7d, 0xfd,
    0x03, 0x83, 0x43, 0xc3, 0x23, 0xa3, 0x63, 0xe3,
    0x13, 0x93, 0x53, 0xd3, 0x33, 0xb3, 0x73, 0xf3,
    0x0b, 0x8b, 0x4b, 0xcb, 0x2b, 0xab, 0x6b, 0xeb,
    0x1b, 0x9b, 0x5b, 0xdb, 0x3b, 0xbb, 0x7b, 0xfb,
    0x07, 0x87, 0x47, 0xc7, 0x27, 0xa7, 0x67, 0xe7,
    0x17, 0x97, 0x57, 0xd7, 0x37, 0xb7, 0x77, 0xf7,
    0x0f, 0x8f, 0x4f, 0xcf, 0x2f, 0xaf, 0x6f, 0xef,
    0x1f, 0x9f, 0x5f, 0xdf, 0x3f, 0xbf, 0x7f, 0xff
], dtype=np.ubyte)

def load_shaders():
    global program
    
    shaders = [GLuint(0) for _ in range(2)]

    shaders[0] = shader_load("render.vs.glsl", GL_VERTEX_SHADER)
    shaders[1] = shader_load("render.fs.glsl", GL_FRAGMENT_SHADER)

    program = link_from_shaders(shaders, 2, True)

tt = 0

class Scene:

    def __init__(self, width, height):
        global vao
        global texture
        global texture_data

        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_SPARSE_ARB, GL_TRUE)

        glTexStorage2D(GL_TEXTURE_2D, 11, GL_RGBA8, TEX_SIZE, TEX_SIZE)

        glGenVertexArrays(1, vao)

        load_shaders()

        with open("smiley.raw", 'rb') as f:
            texture_data = np.fromfile(f, count=(128 * 128 * 4), dtype=np.ubyte)


    def display(self):
        global tt

        currentTime = time.time()

        last_time = 0.0
        total_time = 0.0

        f = total_time

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, 0.0, -2.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(40.0), 0.0, 1.0, 0.0)
        
        mv_matrix = m3dMultiply(T, RY)

        vp_matrix = (GLfloat * 16)(*identityMatrix)
        vp_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0);    


        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, [0.0,0.0,0.0])

        glBindVertexArray(vao)
        glUseProgram(program)

        glBindTexture(GL_TEXTURE_2D, texture)


        r = (tt & 0x100)
        
        tile = bit_reversal_table[(tt & 0xFF)]

        x = (tile >> 0) & 0xF
        y = (tile >> 4) & 0xF
        
        if (r == 0):
        
            glTexPageCommitmentARB(GL_TEXTURE_2D,
                                   0,
                                   x * PAGE_SIZE, y * PAGE_SIZE, 0,
                                   PAGE_SIZE, PAGE_SIZE, 1,
                                   GL_TRUE)
            glTexSubImage2D(GL_TEXTURE_2D,
                            0,
                            x * PAGE_SIZE, y * PAGE_SIZE,
                            PAGE_SIZE, PAGE_SIZE,
                            GL_RGBA, GL_UNSIGNED_BYTE,
                            texture_data)
        
        else :
        
            glTexPageCommitmentARB(GL_TEXTURE_2D,
                                   0,
                                   x * PAGE_SIZE, y * PAGE_SIZE, 0,
                                   PAGE_SIZE, PAGE_SIZE, 1,
                                   GL_FALSE)
        

        tt += 17

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        

        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen

        print ('key:' , key)
        if key == b'\x1b': # ESC
            sys.exit()

        elif key == b'f' or key == b'F': #fullscreen toggle
            if (fullscreen == True):
                glutReshapeWindow(512, 512)
                glutPositionWindow(int((1360/2)-(512/2)), int((768/2)-(512/2)))
                fullscreen = False
            else:
                glutFullScreen()
                fullscreen = True

    def init(self):
        pass

    def timer(self, blah):
        glutPostRedisplay()
        glutTimerFunc( int(1/60), self.timer, 0)
        time.sleep(1/60.0)

if __name__ == '__main__':
    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    glutInitWindowSize(512, 512)

    #glutInitContextVersion(4,1)
    #glutInitContextProfile(GLUT_CORE_PROFILE)    
    
    w1 = glutCreateWindow('OpenGL SuperBible - Sparse Textures')
    glutInitWindowPosition(int((1360/2)-(512/2)), int((768/2)-(512/2)))
    fullscreen = False
    #glutFullScreen()
    scene = Scene(512,512)
    glutReshapeFunc(scene.reshape)
    glutDisplayFunc(scene.display)
    glutKeyboardFunc(scene.keyboard)
    glutIdleFunc(scene.display)
    #glutTimerFunc( int(1/60), scene.timer, 0)
    scene.init()
    glutMainLoop()
