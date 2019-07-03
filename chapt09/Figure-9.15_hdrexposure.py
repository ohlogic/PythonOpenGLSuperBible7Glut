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

texture = GLuint(0)
program = GLuint(0)
vao = GLuint(0)
exposure=1.0

vs_source = '''
#version 420 core

void main(void)
{
    const vec4 vertices[] = vec4[](vec4(-1.0, -1.0, 0.5, 1.0),
                                   vec4( 1.0, -1.0, 0.5, 1.0),
                                   vec4(-1.0,  1.0, 0.5, 1.0),
                                   vec4( 1.0,  1.0, 0.5, 1.0));

    gl_Position = vertices[gl_VertexID];
}
'''

fs_source = '''
#version 430 core

uniform sampler2D s;

uniform float exposure;

out vec4 color;

void main(void)
{
    vec4 c = texture(s, gl_FragCoord.xy / vec2(512.0, 512.0));
    c.xyz = vec3(1.0) - exp(-c.xyz * exposure);
    color = c;
}
'''
def checkGLError():
    status = glGetError()
    if status != GL_NO_ERROR:
        raise RuntimeError('gl error %s' % (status,))

class Scene:

    def __init__(self, width, height):
        global overlay
        global texture
        global program
        global vao    
    
        self.width = width
        self.height = height
        
        overlay.init(80, 50)

        #// Generate a name for the texture
        glGenTextures(1, texture)

        #// Load texture from file
        texture = ktxobject.ktx_load("treelights_2k.ktx")

        #// Now bind it to the context using the GL_TEXTURE_2D binding point
        glBindTexture(GL_TEXTURE_2D, texture)

        program = glCreateProgram()
        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source)
        glCompileShader(fs)
        
        if not glGetShaderiv(fs, GL_COMPILE_STATUS):
            print( 'compile error:' )
            print( glGetShaderInfoLog(fs) )
            
        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)
        
        if not glGetShaderiv(vs, GL_COMPILE_STATUS):
            print( 'compile error:' )
            print( glGetShaderInfoLog(vs) )
            
        glAttachShader(program, vs)
        glAttachShader(program, fs)

        glLinkProgram(program)
        
        if not glGetProgramiv(program, GL_LINK_STATUS):
            print( 'link error:' )
            print( glGetProgramInfoLog(program) )
        
        glGenVertexArrays(1, vao)
        glBindVertexArray(vao)
        

    def display(self):
        global texture
        global program
        
        currentTime = time.time()

        green = [ 0.0, 0.25, 0.0, 1.0 ]
        glClearBufferfv(GL_COLOR, 0, green)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, texture)
        glUseProgram(program)
        glViewport(0, 0, self.width, self.height)
        glUniform1f(0, exposure)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        overlay.clear()
        buffer = ("Exposure = %2.2f (Numpad +/- to change)" % exposure)
        overlay.drawText(buffer, 0, 0)
        overlay.draw()

        checkGLError()

        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global exposure

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
        elif key == b'+':
            exposure *= 1.1
        elif key == b'-':
            exposure /= 1.1

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
    w1 = glutCreateWindow('OpenGL SuperBible - HDR Exposure')
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
