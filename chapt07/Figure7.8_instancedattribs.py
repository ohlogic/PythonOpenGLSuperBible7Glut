#!/usr/bin/python3

import sys
import time
import ctypes

fullscreen = True

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


square_buffer = GLuint(0)
square_vao = GLuint(0)
square_program = GLuint(0)



square_vs_source = '''
#version 410 core

layout (location = 0) in vec4 position;
layout (location = 1) in vec4 instance_color;
layout (location = 2) in vec4 instance_position;

out Fragment
{
    vec4 color;
} fragment;

void main(void)
{
    gl_Position = (position + instance_position) * vec4(0.25, 0.25, 1.0, 1.0);
    fragment.color = instance_color;
}
'''

square_fs_source = '''
#version 410 core
precision highp float;

in Fragment
{
    vec4 color;
} fragment;

out vec4 color;

void main(void)
{
    color = fragment.color;
}
'''



class Scene:

    def __init__(self, width, height):

        global square_buffer
        global square_vao
        global square_program

        self.width = width
        self.height = height

        square_vertices = np.array([
            -1.0, -1.0, 0.0, 1.0,
             1.0, -1.0, 0.0, 1.0,
             1.0,  1.0, 0.0, 1.0,
            -1.0,  1.0, 0.0, 1.0], dtype='float32')

        instance_colors = np.array([
            1.0, 0.0, 0.0, 1.0,
            0.0, 1.0, 0.0, 1.0,
            0.0, 0.0, 1.0, 1.0,
            1.0, 1.0, 0.0, 1.0], dtype='float32')

        instance_positions = np.array([
            -2.0, -2.0, 0.0, 0.0,
             2.0, -2.0, 0.0, 0.0,
             2.0,  2.0, 0.0, 0.0,
            -2.0,  2.0, 0.0, 0.0], dtype='float32')

        glGenVertexArrays(1, square_vao)
        glGenBuffers(1, square_buffer)
        glBindVertexArray(square_vao)
        glBindBuffer(GL_ARRAY_BUFFER, square_buffer)
        
        offset = 0  # not GLuint(0)
        
        bufferSize = (len(square_vertices) + len(instance_colors) + len(instance_positions))*4
        glBufferData(GL_ARRAY_BUFFER, bufferSize, None, GL_STATIC_DRAW)

        glBufferSubData(GL_ARRAY_BUFFER, offset, len(square_vertices)*4, square_vertices)
        offset += len(square_vertices)*4

        glBufferSubData(GL_ARRAY_BUFFER, offset, len(instance_colors)*4, instance_colors)
        offset += len(instance_colors)*4

        glBufferSubData(GL_ARRAY_BUFFER, offset, len(instance_positions)*4, instance_positions)
        offset += len(instance_positions)*4

        glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 0, None)
        offsetInstanceColor =  len(square_vertices)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(offsetInstanceColor))
        offsetInstancPosition =  (len(instance_colors) + len(instance_positions))*4
        glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(offsetInstancPosition))


        glEnableVertexAttribArray(0)
        glEnableVertexAttribArray(1)
        glEnableVertexAttribArray(2)

        glVertexAttribDivisor(1, 1)
        glVertexAttribDivisor(2, 1)

        square_program = glCreateProgram()
        
        square_vs = GLuint(0)
        
        square_vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(square_vs, square_vs_source)
        glCompileShader(square_vs)
        glAttachShader(square_program, square_vs)
        
        square_fs = GLuint(0)

        square_fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(square_fs, square_fs_source)
        glCompileShader(square_fs)
        glAttachShader(square_program, square_fs)

        glLinkProgram(square_program)
        glDeleteShader(square_vs)
        glDeleteShader(square_fs)


    def display(self):

        black = [ 0.0, 0.0, 0.0, 0.0 ]
        glClearBufferfv(GL_COLOR, 0, black)

        glUseProgram(square_program)
        glBindVertexArray(square_vao)
        glDrawArraysInstanced(GL_TRIANGLE_FAN, 0, 4, 4)

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
    start = time.time()

    glutInit()
    
    
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)

    glutInitWindowSize(512, 512)

    w1 = glutCreateWindow('OpenGL SuperBible - Instanced Attributes')
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
