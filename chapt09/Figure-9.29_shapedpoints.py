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
render_vao = GLuint(0)
    
    
class Scene:

    def __init__(self, width, height):
        global render_prog
        global render_vao
        
        self.width = width
        self.height = height
        
        fs_source = '''
#version 410 core

layout (location = 0) out vec4 color;

flat in int shape;

void main(void)
{
    color = vec4(1.0);
    vec2 p = gl_PointCoord * 2.0 - vec2(1.0);
    if (shape == 0)
    {
        if (dot(p, p) > 1.0)
            discard;
    }
    else if (shape == 1)
    {
        if (dot(p, p) > sin(atan(p.y, p.x) * 5.0))
            discard;
    }
    else if (shape == 2)
    {
        if (abs(0.8 - dot(p, p)) > 0.2)
            discard;
    }
    else if (shape == 3)
    {
        if (abs(p.x) < abs(p.y))
            discard;
    }
}
'''

        vs_source = '''
#version 410 core

flat out int shape;

void main(void)
{
    const vec4[4] position = vec4[4](vec4(-0.4, -0.4, 0.5, 1.0),
                                     vec4( 0.4, -0.4, 0.5, 1.0),
                                     vec4(-0.4,  0.4, 0.5, 1.0),
                                     vec4( 0.4,  0.4, 0.5, 1.0));
    gl_Position = position[gl_VertexID];
    shape = gl_VertexID;
}
'''

        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)

        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source)
        glCompileShader(fs)

        render_prog = glCreateProgram()
        glAttachShader(render_prog, vs)
        glAttachShader(render_prog, fs)
        glLinkProgram(render_prog)

        glDeleteShader(vs)
        glDeleteShader(fs)

        glGenVertexArrays(1, render_vao)
        glBindVertexArray(render_vao)




    def display(self):

        currentTime = time.time()

        black = [ 0.0, 0.0, 0.0, 0.0 ]
        one = [ 1.0 ]
        t = currentTime

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_DEPTH, 0, one)

        glUseProgram(render_prog)

        glPointSize(200.0)
        glBindVertexArray(render_vao)
        glDrawArrays(GL_POINTS, 0, 4)


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
    
    glutInitContextVersion(4,1)
    glutInitContextProfile(GLUT_CORE_PROFILE)
    
    w1 = glutCreateWindow('OpenGL SuperBible - Shaped Points')
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
