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

program_gslayers = GLuint(0)
program_showlayers = GLuint(0)
vao = GLuint(0)
mode=0
transform_ubo = GLuint(0)

layered_fbo = GLuint(0)
array_texture = GLuint(0)
array_depth = GLuint(0)


def load_shaders():
    global program_showlayers
    global program_gslayers
    
    vs = GLuint(0)
    gs = GLuint(0)
    fs = GLuint(0)

    if (program_showlayers):
        glDeleteProgram(program_showlayers)

    program_showlayers = glCreateProgram()

    vs = shader_load("showlayers.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("showlayers.fs.glsl", GL_FRAGMENT_SHADER)

    glAttachShader(program_showlayers, vs)
    glAttachShader(program_showlayers, fs)

    glLinkProgram(program_showlayers)

    glDeleteShader(vs)
    glDeleteShader(fs)

    vs = shader_load("gslayers.vs.glsl", GL_VERTEX_SHADER)
    gs = shader_load("gslayers.gs.glsl", GL_GEOMETRY_SHADER)
    fs = shader_load("gslayers.fs.glsl", GL_FRAGMENT_SHADER)

    if (program_gslayers):
        glDeleteProgram(program_gslayers)

    program_gslayers = glCreateProgram()

    glAttachShader(program_gslayers, vs)
    glAttachShader(program_gslayers, gs)
    glAttachShader(program_gslayers, fs)

    glLinkProgram(program_gslayers)

    glDeleteShader(vs)
    glDeleteShader(gs)
    glDeleteShader(fs)



class Scene:

    def __init__(self, width, height):
        global myobject
        global transform_ubo
        global array_texture
        global array_depth
        global layered_fbo
        
        glGenVertexArrays(1, vao)
        glBindVertexArray(vao)

        load_shaders()

        myobject.load("torus.sbm")

        glGenBuffers(1, transform_ubo)
        glBindBuffer(GL_UNIFORM_BUFFER, transform_ubo)
        glBufferData(GL_UNIFORM_BUFFER, 17 * glm.sizeof(glm.mat4), None, GL_DYNAMIC_DRAW)

        array_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D_ARRAY, array_texture)
        glTexStorage3D(GL_TEXTURE_2D_ARRAY, 1, GL_RGBA8, 256, 256, 16)

        array_depth = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D_ARRAY, array_depth)
        glTexStorage3D(GL_TEXTURE_2D_ARRAY, 1, GL_DEPTH_COMPONENT32, 256, 256, 16)

        glGenFramebuffers(1, layered_fbo)
        glBindFramebuffer(GL_FRAMEBUFFER, layered_fbo)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, array_texture, 0)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, array_depth, 0)




    def display(self):

        currentTime = time.time()

        black = [ 0.0, 0.0, 0.0, 1.0 ]
        gray =  [ 0.1, 0.1, 0.1, 1.0 ]
        one = 1.0


        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, 0.0, -4.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, currentTime * m3dDegToRad(5.0), 0.0, 1.0, 0.0)

        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, currentTime * m3dDegToRad(30.0), 1.0, 0.0, 0.0)

        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(T, m3dMultiply(RY, RX))
        
        
        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0)
        
        mvp = (GLfloat * 16)(*identityMatrix)
        mvp = m3dMultiply(proj_matrix , mv_matrix)

        # not used
        class TRANSFORM_BUFFER_:
            proj_matrix = glm.mat4
            mv_matrix = [glm.mat4 for _ in range(16)]
        transform_buf = TRANSFORM_BUFFER_()

        glBindBufferBase(GL_UNIFORM_BUFFER, 0, transform_ubo)

        # TRANSFORM_BUFFER * 
        buffer = glMapBufferRange(GL_UNIFORM_BUFFER, 0, glm.sizeof(glm.mat4) * 17, GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

        bufferp = (GLfloat * 16 * 17).from_address(buffer) 
        
        bufferp[0] = proj_matrix

        
        for i in range (1, 17):

            fi = float((i + 12) / 16.0)
            
            T = (GLfloat * 16)(*identityMatrix)
            m3dTranslateMatrix44(T, 0.0, 0.0, -4.0)
        
            RY = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RY, currentTime * m3dDegToRad(25.0) * fi, 0.0, 1.0, 0.0)
            
            RX = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RX, currentTime * m3dDegToRad(30.0) * fi, 1.0, 0.0, 0.0)
            
            mv_matrix = (GLfloat * 16)(*identityMatrix)
            mv_matrix = m3dMultiply(T, m3dMultiply(RY, RX))
            
            bufferp[i] = mv_matrix


        glUnmapBuffer(GL_UNIFORM_BUFFER)

        ca0 = GL_COLOR_ATTACHMENT0

        glBindFramebuffer(GL_FRAMEBUFFER, layered_fbo)
        glDrawBuffers(1, ca0)
        glViewport(0, 0, 256, 256)
        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_DEPTH, 0, one)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

        glUseProgram(program_gslayers)

        myobject.render()

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glDrawBuffer(GL_BACK)
        glUseProgram(program_showlayers)

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, gray)

        glBindTexture(GL_TEXTURE_2D_ARRAY, array_texture)
        glDisable(GL_DEPTH_TEST)

        glBindVertexArray(vao)
        glDrawArraysInstanced(GL_TRIANGLE_FAN, 0, 4, 16)

        glBindTexture(GL_TEXTURE_2D_ARRAY, 0)


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
    w1 = glutCreateWindow('OpenGL SuperBible - Layered Rendering')
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