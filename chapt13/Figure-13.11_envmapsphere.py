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

tex_envmap = GLuint(0)
envmaps = [GLuint(0) for _ in range(3)]
envmap_index=0

class uniforms_:
    mv_matrix = GLint(0)
    proj_matrix = GLint(0)

uniforms = uniforms_()


def load_shaders():
    global render_prog
    global uniforms
    
    if (render_prog):
        glDeleteProgram(render_prog)

    vs = shader_load("render.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("render.fs.glsl", GL_FRAGMENT_SHADER)

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
    
        global envmaps
        global myobject  
        global tex_envmap
        
        self.width = width
        self.height = height 

        envmaps[0] = ktxobject.ktx_load("spheremap1.ktx")
        envmaps[1] = ktxobject.ktx_load("spheremap2.ktx")
        envmaps[2] = ktxobject.ktx_load("spheremap3.ktx")
        tex_envmap = envmaps[envmap_index]

        myobject.load("dragon.sbm")

        load_shaders()

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        

    def display(self):

        currentTime = time.time()

        gray = [ 0.2, 0.2, 0.2, 1.0 ]
        ones = [ 1.0 ]

        glClearBufferfv(GL_COLOR, 0, gray)
        glClearBufferfv(GL_DEPTH, 0, ones)
        glBindTexture(GL_TEXTURE_2D, tex_envmap)

        glViewport(0, 0, self.width, self.height)

        glUseProgram(render_prog)

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(60.0), float(self.width) / float(self.height), 0.1, 1000.0);    

        T1 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T1, 0.0, 0.0, -15.0)

        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, currentTime * m3dDegToRad(1.0), 1.0, 0.0, 0.0)
        
        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, currentTime * m3dDegToRad(1.1), 0.0, 1.0, 0.0)
                
        T2 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T2, 0.0, -4.0, 0.0)        
        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(T1, m3dMultiply(RX, m3dMultiply(RY, T2)))
        

        glUniformMatrix4fv(uniforms.mv_matrix, 1, GL_FALSE, mv_matrix)
        glUniformMatrix4fv(uniforms.proj_matrix, 1, GL_FALSE, proj_matrix)

        myobject.render()

        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global envmap_index
        global tex_envmap
        
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

        elif key == b'r' or key == b'R': 
            load_shaders();
            
        elif key == b'e' or key == b'E':
            envmap_index = (envmap_index + 1) % 3;
            tex_envmap = envmaps[envmap_index];


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
    
    w1 = glutCreateWindow('OpenGL SuperBible - Spherical Environment Map')
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
