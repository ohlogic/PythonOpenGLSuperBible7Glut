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
skybox_prog = GLuint(0)

tex_envmap = GLuint(0)
envmaps = [GLuint(0) for _ in range(3)]
envmap_index = 0

class uniforms_:

    class render:
        mv_matrix = GLint(0)
        proj_matrix = GLint(0)
        
    class skybox:
        view_matrix = GLint(0)

uniforms = uniforms_()

skybox_vao = GLuint(0)



def load_shaders():
    global render_prog
    global uniforms
    global skybox_prog
    
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

    uniforms.render.mv_matrix = glGetUniformLocation(render_prog, "mv_matrix")
    uniforms.render.proj_matrix = glGetUniformLocation(render_prog, "proj_matrix")

    vs = shader_load("skybox.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("skybox.fs.glsl", GL_FRAGMENT_SHADER)

    skybox_prog = glCreateProgram()
    glAttachShader(skybox_prog, vs)
    glAttachShader(skybox_prog, fs)
    glLinkProgram(skybox_prog)

    glDeleteShader(vs)
    glDeleteShader(fs)

    uniforms.skybox.view_matrix = glGetUniformLocation(skybox_prog, "view_matrix")


class Scene:

    def __init__(self, width, height):
        global myobject
        global tex_envmap
        global skybox_vao
    
        envmaps[0] = ktxobject.ktx_load("mountaincube.ktx")
        tex_envmap = envmaps[envmap_index]

        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

        glEnable(GL_TEXTURE_CUBE_MAP_SEAMLESS)

        myobject.load("dragon.sbm")

        load_shaders()

        glGenVertexArrays(1, skybox_vao)
        glBindVertexArray(skybox_vao)

        glDepthFunc(GL_LEQUAL)
        

    def display(self):

        currentTime = time.time()

        gray = [ 0.2, 0.2, 0.2, 1.0 ]
        ones = [ 1.0 ]
        t = currentTime * 0.1

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(60.0), float(self.width) / float(self.height), 0.1, 1000.0);    

        view_matrix = (GLfloat * 16)(*identityMatrix)
        view_matrix = m3dLookAt([15.0 * sin(t), 0.0, 15.0 * cos(t)],
                                (0.0, 0.0, 0.0),
                                (0.0, 1.0, 0.0))
               
        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, t * m3dDegToRad(0.0), 1.0, 0.0, 0.0)
                                                  
        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, t * m3dDegToRad(130.1), 0.0, 1.0, 0.0)
                    
        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, -4.0, 0.0)

        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(RX, m3dMultiply(RY, T))
        
        mv_matrix = m3dMultiply(view_matrix , mv_matrix)

        glClearBufferfv(GL_COLOR, 0, gray)
        glClearBufferfv(GL_DEPTH, 0, ones)
        glBindTexture(GL_TEXTURE_CUBE_MAP, tex_envmap)

        glViewport(0, 0, self.width, self.height)

        glUseProgram(skybox_prog)
        glBindVertexArray(skybox_vao)

        glUniformMatrix4fv(uniforms.skybox.view_matrix, 1, GL_FALSE, view_matrix)

        glDisable(GL_DEPTH_TEST)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        glUseProgram(render_prog)

        glUniformMatrix4fv(uniforms.render.mv_matrix, 1, GL_FALSE, mv_matrix)
        glUniformMatrix4fv(uniforms.render.proj_matrix, 1, GL_FALSE, proj_matrix)

        glEnable(GL_DEPTH_TEST)

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
    
    w1 = glutCreateWindow('OpenGL SuperBible - Cubic Environment Map')
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
