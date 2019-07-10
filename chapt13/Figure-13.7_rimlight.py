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

program = GLuint(0)

class uniforms_:
    mv_matrix = GLint(0)
    proj_matrix = GLint(0)
    rim_color = GLint(0)
    rim_power = GLint(0)

uniforms = uniforms_()

mat_rotation = (GLfloat * 16)(*identityMatrix)


paused = False
rim_color = [0.3, 0.3, 0.3]
rim_power = 2.5
rim_enable = True

def loadShaders():
    global program
    global uniforms
    
    vs = shader_load("render.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("render.fs.glsl", GL_FRAGMENT_SHADER)

    if (program != 0):
        glDeleteProgram(program)

    program = glCreateProgram()

    glAttachShader(program, vs)
    glAttachShader(program, fs)

    glLinkProgram(program)

    uniforms.mv_matrix = glGetUniformLocation(program, "mv_matrix")
    uniforms.proj_matrix = glGetUniformLocation(program, "proj_matrix")
    uniforms.rim_color = glGetUniformLocation(program, "rim_color")
    uniforms.rim_power = glGetUniformLocation(program, "rim_power")



class Scene:

    def __init__(self, width, height):
        global myobject
    
        loadShaders()

        myobject.load("dragon.sbm")

        glEnable(GL_CULL_FACE)
        #//glCullFace(GL_FRONT)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)




    def display(self):

        currentTime = time.time()


        green = [ 0.0, 0.25, 0.0, 1.0 ]
        black = [ 0.0, 0.0, 0.0, 0.0 ]
        one = 1.0
        last_time = 0.0
        total_time = 0.0

        if (not paused):
            total_time += (currentTime - last_time)
        last_time = currentTime

        f = total_time

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_DEPTH, 0, one)

        glUseProgram(program)


        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0);    

                                                     
        glUniformMatrix4fv(uniforms.proj_matrix, 1, GL_FALSE, proj_matrix)


        mv_matrix = (GLfloat * 16)(*identityMatrix)

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, -5.0, -20.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(5.0), 0.0, 1.0, 0.0)
        
        mv_matrix = m3dMultiply(T, RY)
                                
        glUniformMatrix4fv(uniforms.mv_matrix, 1, GL_FALSE, mv_matrix)

        glUniform3fv(uniforms.rim_color, 1, rim_color if rim_enable else (0.0, 0.0, 0.0))
        glUniform1f(uniforms.rim_power, rim_power)

        myobject.render()


        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global rim_color
        global rim_power
        global rim_enable
        global paused
        
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

        elif key == b'q' or key == b'Q':
            rim_color[0] += 0.1
            
        elif key == b'w' or key == b'W':
            rim_color[1] += 0.1
            
        elif key == b'e' or key == b'E':
            rim_color[2] += 0.1
            
        elif key == b'r' or key == b'R':
            rim_power *= 1.5
            
        elif key == b'a' or key == b'A':
            rim_color[0] -= 0.1
            
        elif key == b's' or key == b'S':
            rim_color[1] -= 0.1
            
        elif key == b'd' or key == b'D':
            rim_color[2] -= 0.1
            
        elif key == b'g' or key == b'G':
            rim_power /= 1.5
            
        elif key == b'z' or key == b'Z':
            rim_enable = not rim_enable;
            
        elif key == b'p' or key == b'P':
            paused = not paused
            
        elif key == b'l' or key == b'L':
            loadShaders()
            





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
    
    w1 = glutCreateWindow('OpenGL SuperBible - Rim Lighting')
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
