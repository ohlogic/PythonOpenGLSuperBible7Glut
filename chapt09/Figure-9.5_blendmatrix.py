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

program = GLuint(0)
vao = GLuint(0)
position_buffer = GLuint(0)
index_buffer = GLuint(0)
mv_location = GLint(0)
proj_location = GLint(0)

class Scene:

    def __init__(self, width, height):
        global program
        global vao
        global position_buffer
        global index_buffer
        global mv_location
        global proj_location
        
        vs_source = '''

#version 410 core

in vec4 position;

out VS_OUT
{
    vec4 color0;
    vec4 color1;
} vs_out;

uniform mat4 mv_matrix;
uniform mat4 proj_matrix;

void main(void)
{
    gl_Position = proj_matrix * mv_matrix * position;
    vs_out.color0 = position * 2.0 + vec4(0.5, 0.5, 0.5, 0.0);
    vs_out.color1 = vec4(0.5, 0.5, 0.5, 0.0) - position * 2.0;
}
'''

        fs_source = '''

#version 410 core

layout (location = 0, index = 0) out vec4 color0;
layout (location = 0, index = 1) out vec4 color1;

in VS_OUT
{
    vec4 color0;
    vec4 color1;
} fs_in;

void main(void)
{
    color0 = vec4(fs_in.color0.xyz, 1.0);
    color1 = vec4(fs_in.color0.xyz, 1.0);
}
'''

        program = glCreateProgram()
        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source)
        glCompileShader(fs)

        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)

        glAttachShader(program, vs)
        glAttachShader(program, fs)

        glLinkProgram(program)

        mv_location = glGetUniformLocation(program, "mv_matrix")
        proj_location = glGetUniformLocation(program, "proj_matrix")

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

        vertex_positions = np.array([
        
            -0.25, -0.25, -0.25,
            -0.25,  0.25, -0.25,
             0.25, -0.25, -0.25,
             0.25,  0.25, -0.25,
             0.25, -0.25,  0.25,
             0.25,  0.25,  0.25,
            -0.25, -0.25,  0.25,
            -0.25,  0.25,  0.25,
        ], dtype=np.float32) # GLfloat
        
        
        size_vertex_indices = ctypes.sizeof(ctypes.c_ushort)*len(vertex_indices)
        size_vertex_positions = ctypes.sizeof(ctypes.c_float)*len(vertex_positions)


        glGenBuffers(1, position_buffer)
        glBindBuffer(GL_ARRAY_BUFFER, position_buffer)
        glBufferData(GL_ARRAY_BUFFER,
                     size_vertex_positions,
                     vertex_positions,
                     GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)

        glGenBuffers(1, index_buffer)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, index_buffer)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                     size_vertex_indices,
                     vertex_indices,
                     GL_STATIC_DRAW)

        glEnable(GL_CULL_FACE)
        # // glFrontFace(GL_CW)

        # //glEnable(GL_DEPTH_TEST)
        # //glDepthFunc(GL_LEQUAL)




    def display(self):

        currentTime = time.time()



        orange = [ 0.6, 0.4, 0.1, 1.0 ]
        one = 1.0

        blend_func = [
        
            GL_ZERO,
            GL_ONE,
            GL_SRC_COLOR,
            GL_ONE_MINUS_SRC_COLOR,
            GL_DST_COLOR,
            GL_ONE_MINUS_DST_COLOR,
            GL_SRC_ALPHA,
            GL_ONE_MINUS_SRC_ALPHA,
            GL_DST_ALPHA,
            GL_ONE_MINUS_DST_ALPHA,
            GL_CONSTANT_COLOR,
            GL_ONE_MINUS_CONSTANT_COLOR,
            GL_CONSTANT_ALPHA,
            GL_ONE_MINUS_CONSTANT_ALPHA,
            GL_SRC_ALPHA_SATURATE,
            GL_SRC1_COLOR,
            GL_ONE_MINUS_SRC1_COLOR,
            GL_SRC1_ALPHA,
            GL_ONE_MINUS_SRC1_ALPHA
        ]
        
        num_blend_funcs = len (blend_func)
        
        x_scale = 20.0 / float(num_blend_funcs)
        y_scale = 16.0 / float(num_blend_funcs)
        t = currentTime

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, orange)
        glClearBufferfv(GL_DEPTH, 0, one)

        glUseProgram(program)


        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0)
        
                                                     
        glUniformMatrix4fv(proj_location, 1, GL_FALSE, proj_matrix)

        glEnable(GL_BLEND)
        glBlendColor(0.2, 0.5, 0.7, 0.5)
        
        for j in range(0, num_blend_funcs):

            for i in range(0, num_blend_funcs):

                T = (GLfloat * 16)(*identityMatrix)
                m3dTranslateMatrix44(T, 9.5 - x_scale * float(i), 7.5 - y_scale * float(j), -18.0)

                RY = (GLfloat * 16)(*identityMatrix)
                m3dRotationMatrix44(RY, t * m3dDegToRad(-45.0), 0.0, 1.0, 0.0)

                RX = (GLfloat * 16)(*identityMatrix)
                m3dRotationMatrix44(RX, t * m3dDegToRad(-21.0), 1.0, 0.0, 0.0)

                mv_matrix = (GLfloat * 16)(*identityMatrix)
                mv_matrix = m3dMultiply(T, m3dMultiply(RY, RX))    
                    
                    
                glUniformMatrix4fv(mv_location, 1, GL_FALSE, mv_matrix);
                glBlendFunc(blend_func[i], blend_func[j]);
                glDrawElements(GL_TRIANGLES, 36, GL_UNSIGNED_SHORT, None);



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
    w1 = glutCreateWindow('OpenGL SuperBible - Blending Functions')
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
