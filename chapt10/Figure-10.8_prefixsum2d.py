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
    from OpenGL.raw.GL.ARB.vertex_array_object import glGenVertexArrays, glBindVertexArray
except:
    print ('''
    ERROR: PyOpenGL not installed properly.
        ''')
    sys.exit()

import numpy as np
from math import cos, sin
import glm
identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

myobject = SBMObject()
ktxobject = KTXObject()
overlay = OVERLAY_()

#GLuint 
images = [GLuint(0) for _ in range(3) ]

prefix_sum_prog = GLuint(0)
show_image_prog = GLuint(0)
dummy_vao = GLuint(0)

NUM_ELEMENTS = 2048

def load_shaders():
    global prefix_sum_prog
    global show_image_prog
    
    cs = shader_load("prefixsum2d.cs.glsl", GL_COMPUTE_SHADER)

    if (prefix_sum_prog):
        glDeleteProgram(prefix_sum_prog)

    prefix_sum_prog = link_from_shaders(cs, 1, True)

    class show_image_shaders_:
        vs = GLuint(0)
        fs = GLuint(0)
            
    show_image_shaders = show_image_shaders_()
    
    show_image_shaders.vs = shader_load("showimage.vs.glsl", GL_VERTEX_SHADER)
    show_image_shaders.fs = shader_load("showimage.fs.glsl", GL_FRAGMENT_SHADER)

    show_image_shaders_list = [show_image_shaders.vs, show_image_shaders.fs]
    
    show_image_prog = link_from_shaders(show_image_shaders_list, 2, True)
    

class Scene:

    def __init__(self, width, height):
    
        global ktxobject
        global dummy_vao
        global images
        
        self.width = width
        self.height = height
        
        #glGenTextures(3, images)
        images = [glGenTextures(1) for _ in range(3)]

        images[0] = ktxobject.ktx_load("salad-gray.ktx")

        for i in range(1, 3):
            glBindTexture(GL_TEXTURE_2D, images[i])
            glTexStorage2D(GL_TEXTURE_2D, 1, GL_R32F, NUM_ELEMENTS, NUM_ELEMENTS)

        glGenVertexArrays(1, dummy_vao)
        glBindVertexArray(dummy_vao)

        load_shaders()
        
        

    def display(self):

        currentTime = time.time()

        glUseProgram(prefix_sum_prog)

        glBindImageTexture(0, images[0], 0, GL_FALSE, 0, GL_READ_ONLY, GL_R32F)
        glBindImageTexture(1, images[1], 0, GL_FALSE, 0, GL_WRITE_ONLY, GL_R32F)

        glDispatchCompute(NUM_ELEMENTS, 1, 1)

        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        glBindImageTexture(0, images[1], 0, GL_FALSE, 0, GL_READ_ONLY, GL_R32F)
        glBindImageTexture(1, images[2], 0, GL_FALSE, 0, GL_WRITE_ONLY, GL_R32F)

        glDispatchCompute(NUM_ELEMENTS, 1, 1)

        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        glBindTexture(GL_TEXTURE_2D, images[2])

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, images[2])

        glUseProgram(show_image_prog)

        glViewport(0, 0, self.width, self.height)
        glBindVertexArray(dummy_vao)
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
    
    w1 = glutCreateWindow('OpenGL SuperBible - 2D Prefix Sum')
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
