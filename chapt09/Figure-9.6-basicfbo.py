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


program1 = GLuint(0)
program2 = GLuint(0)
vao = GLuint(0)
position_buffer = GLuint(0)
index_buffer = GLuint(0)
fbo = GLuint(0)
color_texture = GLuint(0)
depth_texture = GLuint(0)

mv_location = GLint(0)
proj_location = GLint(0)

mv_location2 = GLuint(0)
proj_location2 = GLuint(0)



class Scene:

    def __init__(self, width, height):
        global program1
        global program2
        global vao
        global position_buffer
        global index_buffer
        global fbo
        global color_texture
        global depth_texture
        global mv_location
        global proj_location
        global mv_location2
        global proj_location2

        vs_source = '''
#version 410 core

layout (location = 0) in vec4 position;
layout (location = 1) in vec2 texcoord;

out VS_OUT
{
    vec4 color;
    vec2 texcoord;
} vs_out;

uniform mat4 mv_matrix;
uniform mat4 proj_matrix;

void main(void)
{
    gl_Position = proj_matrix * mv_matrix * position;
    vs_out.color = position * 2.0 + vec4(0.5, 0.5, 0.5, 0.0);
    vs_out.texcoord = texcoord;
}
'''

        fs_source1 = '''
#version 410 core

in VS_OUT
{
    vec4 color;
    vec2 texcoord;
} fs_in;

out vec4 color;

void main(void)
{
    color = sin(fs_in.color * vec4(40.0, 20.0, 30.0, 1.0)) * 0.5 + vec4(0.5);
}
'''

        fs_source2 = '''
#version 420 core

uniform sampler2D tex;

out vec4 color;

in VS_OUT
{
    vec4 color;
    vec2 texcoord;
} fs_in;

void main(void)
{
    color = mix(fs_in.color, texture(tex, fs_in.texcoord), 0.7);
}
'''

        program1 = glCreateProgram()
        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source1)
        glCompileShader(fs)

        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)

        glAttachShader(program1, vs)
        glAttachShader(program1, fs)

        glLinkProgram(program1)

        glDeleteShader(vs)
        glDeleteShader(fs)

        program2 = glCreateProgram()
        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source2)
        glCompileShader(fs)

        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)

        glAttachShader(program2, vs)
        glAttachShader(program2, fs)

        glLinkProgram(program2)

        glDeleteShader(vs)
        glDeleteShader(fs)

        mv_location = glGetUniformLocation(program1, "mv_matrix")
        proj_location = glGetUniformLocation(program1, "proj_matrix")
        mv_location2 = glGetUniformLocation(program2, "mv_matrix")
        proj_location2 = glGetUniformLocation(program2, "proj_matrix")

        glGenVertexArrays(1, vao)
        glBindVertexArray(vao)

        vertex_indices = np.array([
        
            0, 1, 2,
            2, 1, 3,
            2, 3, 4,
            4, 3, 5,
            4, 5, 6,
            6, 5, 7,
            6, 7, 0,
            0, 7, 1,
            6, 0, 2,
            2, 4, 6,
            7, 5, 3,
            7, 3, 1
        ], dtype=np.uint16) # GLushort

        vertex_data = np.array([
        
             # // Position            Tex Coord
            -0.25, -0.25,  0.25,      0.0, 1.0,
            -0.25, -0.25, -0.25,      0.0, 0.0,
             0.25, -0.25, -0.25,      1.0, 0.0,

             0.25, -0.25, -0.25,      1.0, 0.0,
             0.25, -0.25,  0.25,      1.0, 1.0,
            -0.25, -0.25,  0.25,      0.0, 1.0,

             0.25, -0.25, -0.25,      0.0, 0.0,
             0.25,  0.25, -0.25,      1.0, 0.0,
             0.25, -0.25,  0.25,      0.0, 1.0,

             0.25,  0.25, -0.25,      1.0, 0.0,
             0.25,  0.25,  0.25,      1.0, 1.0,
             0.25, -0.25,  0.25,      0.0, 1.0,

             0.25,  0.25, -0.25,      1.0, 0.0,
            -0.25,  0.25, -0.25,      0.0, 0.0,
             0.25,  0.25,  0.25,      1.0, 1.0,

            -0.25,  0.25, -0.25,      0.0, 0.0,
            -0.25,  0.25,  0.25,      0.0, 1.0,
             0.25,  0.25,  0.25,      1.0, 1.0,

            -0.25,  0.25, -0.25,      1.0, 0.0,
            -0.25, -0.25, -0.25,      0.0, 0.0,
            -0.25,  0.25,  0.25,      1.0, 1.0,

            -0.25, -0.25, -0.25,      0.0, 0.0,
            -0.25, -0.25,  0.25,      0.0, 1.0,
            -0.25,  0.25,  0.25,      1.0, 1.0,

            -0.25,  0.25, -0.25,      0.0, 1.0,
             0.25,  0.25, -0.25,      1.0, 1.0,
             0.25, -0.25, -0.25,      1.0, 0.0,

             0.25, -0.25, -0.25,      1.0, 0.0,
            -0.25, -0.25, -0.25,      0.0, 0.0,
            -0.25,  0.25, -0.25,      0.0, 1.0,

            -0.25, -0.25,  0.25,      0.0, 0.0,
             0.25, -0.25,  0.25,      1.0, 0.0,
             0.25,  0.25,  0.25,      1.0, 1.0,

             0.25,  0.25,  0.25,      1.0, 1.0,
            -0.25,  0.25,  0.25,      0.0, 1.0,
            -0.25, -0.25,  0.25,      0.0, 0.0,
        ], dtype=np.float32) # GLfloat

        size_vertex_indices = ctypes.sizeof(ctypes.c_ushort)*len(vertex_indices)
        size_vertex_data = ctypes.sizeof(ctypes.c_float)*len(vertex_data)


        glGenBuffers(1, position_buffer)
        glBindBuffer(GL_ARRAY_BUFFER, position_buffer)
        glBufferData(GL_ARRAY_BUFFER,
                     size_vertex_data,
                     vertex_data,
                     GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * ctypes.sizeof(GLfloat), None)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * ctypes.sizeof(GLfloat), ctypes.c_void_p((3 * ctypes.sizeof(GLfloat))))
        glEnableVertexAttribArray(1)

        glGenBuffers(1, index_buffer)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, index_buffer)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                     size_vertex_indices,
                     vertex_indices,
                     GL_STATIC_DRAW)

        glEnable(GL_CULL_FACE)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

        glGenFramebuffers(1, fbo)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)

        color_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, color_texture)
        glTexStorage2D(GL_TEXTURE_2D, 9, GL_RGBA8, 512, 512)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        depth_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, depth_texture)
        glTexStorage2D(GL_TEXTURE_2D, 9, GL_DEPTH_COMPONENT32F, 512, 512)

        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, color_texture, 0)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, depth_texture, 0)

        draw_buffers = [ GL_COLOR_ATTACHMENT0 ]
        glDrawBuffers(1, draw_buffers)



    def display(self):

        currentTime = time.time()

        blue = [ 0.0, 0.0, 0.3, 1.0 ]
        one = 1.0

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0)
        
        f = currentTime * 0.3

        T1 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T1, 0.0, 0.0, -4.0)

        T2 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T2, sin(2.1 * f) * 0.5, cos(1.7 * f) * 0.5, sin(1.3 * f) * cos(1.5 * f) * 2.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, currentTime * m3dDegToRad(45.0), 0.0, 1.0, 0.0)

        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, currentTime * m3dDegToRad(81.0), 1.0, 0.0, 0.0)

        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(T1, m3dMultiply(T2, m3dMultiply(RY, RX)))


        glBindFramebuffer(GL_FRAMEBUFFER, fbo)

        glViewport(0, 0, 512, 512)
        glClearBufferfv(GL_COLOR, 0, [0.0, 1.0, 0.0])
        glClearBufferfi(GL_DEPTH_STENCIL, 0, 1.0, 0)

        glUseProgram(program1)

        glUniformMatrix4fv(proj_location, 1, GL_FALSE, proj_matrix)
        glUniformMatrix4fv(mv_location, 1, GL_FALSE, mv_matrix)
        glDrawArrays(GL_TRIANGLES, 0, 36)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, blue)
        glClearBufferfv(GL_DEPTH, 0, one)

        glBindTexture(GL_TEXTURE_2D, color_texture)

        glUseProgram(program2)

        glUniformMatrix4fv(proj_location2, 1, GL_FALSE, proj_matrix)
        glUniformMatrix4fv(mv_location2, 1, GL_FALSE, mv_matrix)

        glDrawArrays(GL_TRIANGLES, 0, 36)

        glBindTexture(GL_TEXTURE_2D, 0)

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
    w1 = glutCreateWindow('OpenGL SuperBible - Basic Framebuffer Object')
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
