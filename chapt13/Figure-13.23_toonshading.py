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

render_prog = GLuint(0)

tex_toon = GLuint(0)

class uniforms_:
    mv_matrix = GLint(0)
    proj_matrix = GLint(0)

uniforms = uniforms_()


def load_shaders():
    global render_prog
    global uniforms
    
    if (render_prog):
        glDeleteProgram(render_prog)

    vs = shader_load("toonshading.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("toonshading.fs.glsl", GL_FRAGMENT_SHADER)

    render_prog = glCreateProgram()
    glAttachShader(render_prog, vs)
    glAttachShader(render_prog, fs)
    glLinkProgram(render_prog)

    glDeleteShader(vs)
    glDeleteShader(fs)

    uniforms.mv_matrix = glGetUniformLocation(render_prog, "mv_matrix")
    uniforms.proj_matrix = glGetUniformLocation(render_prog, "proj_matrix")



class Scene:

    def __init__(self, width, height):
        global tex_toon
        
    
        toon_tex_data = [
        
            0x44, 0x00, 0x00, 0x00,
            0x88, 0x00, 0x00, 0x00,
            0xCC, 0x00, 0x00, 0x00,
            0xFF, 0x00, 0x00, 0x00
        ] # GLubyte

        size_toon_tex_data = ctypes.sizeof(c_ubyte) * len(toon_tex_data)

        tex_toon = glGenTextures(1)
        glBindTexture(GL_TEXTURE_1D, tex_toon)
        glTexStorage1D(GL_TEXTURE_1D, 1, GL_RGB8, size_toon_tex_data // 4)
        glTexSubImage1D(GL_TEXTURE_1D, 0,
                        0, size_toon_tex_data // 4,
                        GL_RGBA, GL_UNSIGNED_BYTE,
                        toon_tex_data)
        glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)

        myobject.load("torus_nrms_tc.sbm")

        load_shaders()

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)




    def display(self):

        currentTime = time.time()

        gray = [ 0.1, 0.1, 0.1, 1.0 ]
        ones = [ 1.0 ]

        glClearBufferfv(GL_COLOR, 0, gray)
        glClearBufferfv(GL_DEPTH, 0, ones)

        glBindTexture(GL_TEXTURE_1D, tex_toon)

        glViewport(0, 0, self.width, self.height)

        glUseProgram(render_prog)

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(60.0), float(self.width) / float(self.height), 0.1, 1000.0)
        
        
        

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, 0.0, -3.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, currentTime * m3dDegToRad(13.75), 0.0, 1.0, 0.0)
        
        RZ = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RZ, currentTime * m3dDegToRad(7.75), 0.0, 0.0, 1.0)
        
        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, currentTime * m3dDegToRad(15.3), 1.0, 0.0, 0.0)
        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(T, m3dMultiply(RY, m3dMultiply(RZ, RX)))
        
        glUniformMatrix4fv(uniforms.mv_matrix, 1, GL_FALSE, mv_matrix)
        glUniformMatrix4fv(uniforms.proj_matrix, 1, GL_FALSE, proj_matrix)

        myobject.render()


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
    
    w1 = glutCreateWindow('OpenGL SuperBible - Toon Shading')
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
