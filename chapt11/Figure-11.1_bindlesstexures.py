#!/usr/bin/python3

import sys
import time
import ctypes

fullscreen = True
sys.path.append("./shared")

from sbmloader import SBMObject
#from ktxloader import KTXObject
#from textoverlay import OVERLAY_
from shader import shader_load, link_from_shaders

from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, \
    m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate, m3dScaleMatrix44, \
    scale, m3dLookAt, normalize

try:
    from OpenGL.GLUT import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
    #from OpenGL.raw.GL.ARB.vertex_array_object import glGenVertexArrays, glBindVertexArray
    from OpenGL.raw.GL.ARB.bindless_texture import glGetTextureHandleARB, glMakeTextureHandleResidentARB
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
#ktxobject = KTXObject()
#overlay = OVERLAY_()



NUM_TEXTURES        = 384
TEXTURE_LEVELS      = 5
TEXTURE_SIZE        = (1 << (TEXTURE_LEVELS - 1))


program = GLuint(0)


class textures_:
    def __init__(self):
        self.name = GLuint(0)
        self.handle = GLuint64(0)

textures = [textures_() for _ in range(1024)]

class buffers_:
    transformBuffer = GLuint(0)
    textureHandleBuffer = GLuint(0)

buffers = buffers_()

class MATRICES_:
    view = (GLfloat * 16)(*identityMatrix)
    projection = (GLfloat * 16)(*identityMatrix)
    model = [(GLfloat * 16)(*identityMatrix) for _ in range(NUM_TEXTURES)]

MATRICES = MATRICES_()


import random
random.seed (0x13371337)

def random_uint():
    return random.randint(0, 4294967295)



def load_shaders():
    global program
    
    shaders = [GLuint(0) for _ in range(2)]

    shaders[0] = shader_load("render.vs.glsl", GL_VERTEX_SHADER)
    shaders[1] = shader_load("render.fs.glsl", GL_FRAGMENT_SHADER)

    program = link_from_shaders(shaders, 2, True)



class Scene:

    def __init__(self, width, height):
        global myobject
        global buffers

        tex_data = [0 for _ in range(32 * 32 * 4)]

        mutated_data = [0 for _ in range(32 * 32)]

        for i in range(0, 32):
        
            for j in range(0, 32):

                tex_data[i * 4 * 32 + j * 4] = (i ^ j) << 3
                tex_data[i * 4 * 32 + j * 4 + 1] = (i ^ j) << 3
                tex_data[i * 4 * 32 + j * 4 + 2] = (i ^ j) << 3
                

        buffers.transformBuffer = glGenBuffers(1)
        glBindBuffer(GL_UNIFORM_BUFFER, buffers.transformBuffer)

        glBufferStorage(GL_UNIFORM_BUFFER,
                        ctypes.sizeof(GLfloat) * 16 * 2 * NUM_TEXTURES,
                        None,
                        GL_MAP_WRITE_BIT)

        buffers.textureHandleBuffer = glGenBuffers(1)
        
        glBindBuffer(GL_UNIFORM_BUFFER, buffers.textureHandleBuffer)

        glBufferStorage(GL_UNIFORM_BUFFER,
                        NUM_TEXTURES * ctypes.sizeof(GLuint64) * 2,
                        None,
                        GL_MAP_WRITE_BIT)

        pHandles = glMapBufferRange(GL_UNIFORM_BUFFER, 0, NUM_TEXTURES * ctypes.sizeof(GLuint64) * 2, 
            GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)
        
        pHandlesp = (GLuint64 * 2 * NUM_TEXTURES).from_address(pHandles)


        for i in range(0, NUM_TEXTURES):

            r = (random_uint() & 0xFCFF3F) << (random_uint() % 12)
            textures[i].name = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, textures[i].name)
            glTexStorage2D(GL_TEXTURE_2D, TEXTURE_LEVELS, GL_RGBA8, TEXTURE_SIZE, TEXTURE_SIZE)
            
            mutated_data = np.frombuffer(np.array(tex_data, dtype=np.byte), dtype=np.uint32)
            for j in range(0, 32 * 32):
                mutated_data[j] = ( mutated_data[j] & r) | 0x20202020
            
            byte_buffer = np.frombuffer(mutated_data, dtype=np.byte)
            
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, TEXTURE_SIZE, TEXTURE_SIZE, GL_RGBA, GL_UNSIGNED_BYTE, byte_buffer)
            glGenerateMipmap(GL_TEXTURE_2D)
            textures[i].handle = glGetTextureHandleARB(textures[i].name)
            glMakeTextureHandleResidentARB(textures[i].handle)
            pHandlesp[i][0] = textures[i].handle
            
        glUnmapBuffer(GL_UNIFORM_BUFFER)

        load_shaders()
        
        myobject.load("torus_nrms_tc.sbm")


    def display(self):

        currentTime = time.time()

        last_time = 0.0
        total_time = 0.0

        f = currentTime

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(70.0), float(self.width) / float(self.height), 0.1, 500.0);    


        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, [0.0,0.0,0.0])
        glClearBufferfi(GL_DEPTH_STENCIL, 0, 1.0, 0)

        glFinish()

        glBindBufferBase(GL_UNIFORM_BUFFER, 0, buffers.transformBuffer)
        
        pMatrices = glMapBufferRange(GL_UNIFORM_BUFFER, 0, ctypes.sizeof(GLfloat) * 16 * (NUM_TEXTURES+2), GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

        pMatricesp = (GLfloat * 16 * (NUM_TEXTURES+2)).from_address(pMatrices)

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, 0.0, -80.0)
        
        pMatricesp[0] = T 
        pMatricesp[1] = proj_matrix

        angle = f
        angle2 = 0.7 * f
        angle3 = 0.1 * f
        
        for i in range (2, NUM_TEXTURES+2):

            T1 = (GLfloat * 16)(*identityMatrix)
            m3dTranslateMatrix44(T1, (i % 32) * 4.0 - 62.0, (i >> 5) * 6.0 - 33.0, 15.0 * sin(angle * 0.19) + 3.0 * cos(angle2 * 6.26) + 40.0 * sin(angle3))

            RX = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RX, angle * m3dDegToRad(130.0), 1.0, 0.0, 0.0)
            
            RZ = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RZ, angle * m3dDegToRad(140.0), 0.0, 0.0, 1.0)

            pMatricesp[i] = m3dMultiply(T1, m3dMultiply(RX, RZ))

            angle += 1.0
            angle2 += 4.1
            angle3 += 0.01

        glUnmapBuffer(GL_UNIFORM_BUFFER)

        glFinish()

        glBindBufferBase(GL_UNIFORM_BUFFER, 1, buffers.textureHandleBuffer)

        glEnable(GL_DEPTH_TEST)

        glUseProgram(program)

        myobject.render(NUM_TEXTURES)
        
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

    glutInitContextVersion(4,4)
    glutInitContextProfile(GLUT_CORE_PROFILE)    
    
    w1 = glutCreateWindow('OpenGL SuperBible - Bindless Textures')
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
