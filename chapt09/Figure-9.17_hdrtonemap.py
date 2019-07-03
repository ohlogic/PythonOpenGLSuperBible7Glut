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

from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate, m3dScaleMatrix44, \
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

tex_src = GLuint(0)
tex_lut = GLuint(0)

program_naive = GLuint(0)
program_exposure = GLuint(0)
program_adaptive = GLuint(0)
vao = GLuint(0)
exposure=0.0
mode=0

class UNIFORMS_:
    class exposure:
        exposure=0;
    
uniforms = UNIFORMS_()

def load_shaders():
    global program_naive
    global program_adaptive
    global program_exposure
    global uniforms
    
    if (program_naive):
        glDeleteProgram(program_naive)

    program_naive = glCreateProgram()

    vs = shader_load("tonemap.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("tonemap_naive.fs.glsl", GL_FRAGMENT_SHADER)

    glAttachShader(program_naive, vs)
    glAttachShader(program_naive, fs)

    glLinkProgram(program_naive)

    glDeleteShader(fs)

    fs = shader_load("tonemap_adaptive.fs.glsl", GL_FRAGMENT_SHADER)

    if (program_adaptive):
        glDeleteProgram(program_adaptive)

    program_adaptive = glCreateProgram()

    glAttachShader(program_adaptive, vs)
    glAttachShader(program_adaptive, fs)

    glLinkProgram(program_adaptive)

    glDeleteShader(fs)

    fs = shader_load("tonemap_exposure.fs.glsl", GL_FRAGMENT_SHADER)

    if (program_exposure):
        glDeleteProgram(program_exposure)

    program_exposure = glCreateProgram()

    glAttachShader(program_exposure, vs)
    glAttachShader(program_exposure, fs)

    glLinkProgram(program_exposure)

    uniforms.exposure.exposure = glGetUniformLocation(program_exposure, "exposure")

    glDeleteShader(vs)
    glDeleteShader(fs)


class Scene:

    def __init__(self, width, height):
        global tex_src
        global tex_lut
        
        self.width = width
        self.height = height
    
        # // Load texture from file
        tex_src = ktxobject.ktx_load("treelights_2k.ktx")

        # // Now bind it to the context using the GL_TEXTURE_2D binding point
        glBindTexture(GL_TEXTURE_2D, tex_src)

        glGenVertexArrays(1, vao)
        glBindVertexArray(vao)

        load_shaders()

        exposureLUT   = [ 11.0, 6.0, 3.2, 2.8, 2.2, 1.90, 1.80, 1.80, 1.70, 1.70,  1.60, 1.60, 1.50, 1.50, 1.40, 1.40, 1.30, 1.20, 1.10, 1.00 ]

        tex_lut = glGenTextures(1)
        glBindTexture(GL_TEXTURE_1D, tex_lut)
        glTexStorage1D(GL_TEXTURE_1D, 1, GL_R32F, 20)
        glTexSubImage1D(GL_TEXTURE_1D, 0, 0, 20, GL_RED, GL_FLOAT, exposureLUT)
        glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)




    def display(self):

        currentTime = time.time()

        black = [ 0.0, 0.25, 0.0, 1.0 ]
        glViewport(0, 0, self.width, self.height)

        glClearBufferfv(GL_COLOR, 0, black)

        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_1D, tex_lut)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, tex_src)

        # // glUseProgram(mode ? program_adaptive : program_naive)
        if (mode == 0):
                glUseProgram(program_naive)
         
        elif (mode == 1):
                glUseProgram(program_exposure)
                glUniform1f(uniforms.exposure.exposure, exposure)
    
        elif (mode == 2):
                glUseProgram(program_adaptive)
         
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)



        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global mode
        
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
        elif key == b'm' or key == b'M':
            mode = (mode + 1) % 3;

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
    w1 = glutCreateWindow('OpenGL SuperBible - HDR Tone Mapping')
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
