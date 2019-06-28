#!/usr/bin/python3

import sys
#import time

sys.path.append("./shared")

#from sbmloader import SBMObject    # location of sbm file format loader
from ktxloader import KTXObject    # location of ktx file format loader

#from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate, m3dScaleMatrix44

fullscreen = True

#import numpy.matlib
#import numpy as np

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


texture = GLuint(0)
program = GLuint(0)
vao = GLuint(0)


class Scene:

    def __init__(self, width, height):
        global texture
        global program
        global vao

        self.width = width
        self.height = height

        vs = GLuint(0)
        fs = GLuint(0)

        vs_source = '''
#version 410 core

uniform vec2 offset;

out vec2 tex_coord;

void main(void)
{
    const vec4 vertices[] = vec4[](vec4(-0.45, -0.45, 0.5, 1.0),
                                   vec4( 0.45, -0.45, 0.5, 1.0),
                                   vec4(-0.45,  0.45, 0.5, 1.0),
                                   vec4( 0.45,  0.45, 0.5, 1.0));

    gl_Position = vertices[gl_VertexID] + vec4(offset, 0.0, 0.0);
    tex_coord = vertices[gl_VertexID].xy * 3.0 + vec2(0.45 * 3);
}
'''

        fs_source = '''
#version 410 core

uniform sampler2D s;

out vec4 color;

in vec2 tex_coord;

void main(void)
{
    color = texture(s, tex_coord);
}
'''


        #// Generate a name for the texture
        glGenTextures(1, texture)

        #// Load texture from file
        ktxobj = KTXObject()
        texture = ktxobj.ktx_load("rightarrows.ktx")

        #// Now bind it to the context using the GL_TEXTURE_2D binding point
        glBindTexture(GL_TEXTURE_2D, texture)

        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)

        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source)
        glCompileShader(fs)

        program = glCreateProgram()
        glAttachShader(program, vs)
        glAttachShader(program, fs)
        glLinkProgram(program)

        glDeleteShader(vs)
        glDeleteShader(fs)

        glGetProgramInfoLog(program)

        glGenVertexArrays(1, vao)
        glBindVertexArray(vao)


    def display(self):

        #currentTime = time.time()

        green = [ 0.0, 0.1, 0.0, 1.0 ]
        yellow = [ 0.4, 0.4, 0.0, 1.0 ]
        glClearBufferfv(GL_COLOR, 0, green);

        wrapmodes = [ GL_CLAMP_TO_EDGE, GL_REPEAT, GL_CLAMP_TO_BORDER, GL_MIRRORED_REPEAT ]
        offsets = [  [-0.5, -0.5],
                      [0.5, -0.5],
                     [-0.5,  0.5],
                      [0.5,  0.5] ]
                                          
        glUseProgram(program)
        glViewport(0, 0, self.width, self.height)

        glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, yellow)

        for i in range(0, 4):
            # https://stackoverflow.com/questions/56797971/why-only-half-of-expected-output-using-texture-coordinate-wrapping-modes-exampl
            glUniform2fv(0, 1, offsets[i])
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrapmodes[i])
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrapmodes[i])

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

        print('done')

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

    w1 = glutCreateWindow('OpenGL SuperBible - Texture Wrap Modes')
    glutInitWindowPosition(int((1360/2)-(512/2)), int((768/2)-(512/2)))

    fullscreen = False
    many_cubes = False
    #glutFullScreen()

    scene = Scene(512,512)
    glutReshapeFunc(scene.reshape)
    glutDisplayFunc(scene.display)
    glutKeyboardFunc(scene.keyboard)

    glutIdleFunc(scene.display)
    #glutTimerFunc( int(1/60), scene.timer, 0)

    scene.init()

    glutMainLoop()
