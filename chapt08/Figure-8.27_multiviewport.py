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
vao = GLuint(0)
position_buffer = GLuint(0)
index_buffer = GLuint(0)
uniform_buffer = GLuint(0)
mv_location = GLint(0)
proj_location = GLint(0)


class Scene:

    def __init__(self, width, height):
        global program
        global vao
        global position_buffer
        global index_buffer
        global uniform_buffer
        
        
        vs_source = '''
#version 420 core

in vec4 position;

out VS_OUT
{
    vec4 color;
} vs_out;

void main(void)
{
    gl_Position = position;
    vs_out.color = position * 2.0 + vec4(0.5, 0.5, 0.5, 0.0);
}
'''

        gs_source = '''
#version 420 core

layout (triangles, invocations = 4) in;
layout (triangle_strip, max_vertices = 3) out;

layout (std140, binding = 0) uniform transform_block
{
    mat4 mvp_matrix[4];
};

in VS_OUT
{
    vec4 color;
} gs_in[];

out GS_OUT
{
    vec4 color;
} gs_out;

void main(void)
{
    for (int i = 0; i < gl_in.length(); i++)
    {
        gs_out.color = gs_in[i].color;
        gl_Position = mvp_matrix[gl_InvocationID] *
                      gl_in[i].gl_Position;
        gl_ViewportIndex = gl_InvocationID;
        EmitVertex();
    }
    EndPrimitive();
}
'''

        fs_source = '''
#version 420 core

out vec4 color;

in GS_OUT
{
    vec4 color;
} fs_in;

void main(void)
{
    color = fs_in.color;
}
'''

        program = glCreateProgram()
        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)

        gs = glCreateShader(GL_GEOMETRY_SHADER)
        glShaderSource(gs, gs_source)
        glCompileShader(gs)

        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source)
        glCompileShader(fs)

        glAttachShader(program, vs)
        glAttachShader(program, gs)
        glAttachShader(program, fs)

        glLinkProgram(program)

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

        glGenBuffers(1, uniform_buffer)
        glBindBuffer(GL_UNIFORM_BUFFER, uniform_buffer)
        glBufferData(GL_UNIFORM_BUFFER, 4 * glm.sizeof(glm.mat4()), None, GL_DYNAMIC_DRAW)

        glEnable(GL_CULL_FACE)
        #// glFrontFace(GL_CW)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)



    def display(self):

        currentTime = time.time()


        i=0
        black = [ 0.0, 0.0, 0.0, 1.0 ]
        one = 1.0

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_DEPTH, 0, one)

        # // Each rectangle will be 7/16 of the screen
        viewport_width = (7 * self.width) / 16.0
        viewport_height = (7 * self.height) / 16.0

        # // Four rectangles - lower left first...
        glViewportIndexedf(0, 0, 0, viewport_width, viewport_height);

        # // Lower right...
        glViewportIndexedf(1,
                           self.width - viewport_width, 0,
                           viewport_width, viewport_height);

        # // Upper left...
        glViewportIndexedf(2,
                           0, self.height - viewport_height,
                           viewport_width, viewport_height);

        # // Upper right...
        glViewportIndexedf(3,
                           self.width - viewport_width,
                           self.height - viewport_height,
                           viewport_width, viewport_height);


        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), .1, 1000.0)


        f = currentTime * 0.3;

        glBindBufferBase(GL_UNIFORM_BUFFER, 0, uniform_buffer)
        
        mv_matrix_array = glMapBufferRange(GL_UNIFORM_BUFFER,
                                           0,
                                           4 * glm.sizeof(glm.mat4()),
                                           GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

        mv_matrix_array_p = (GLfloat * 16 * 4).from_address(mv_matrix_array) 
        
        for i in range(0, 4):

            T = (GLfloat * 16)(*identityMatrix)
            m3dTranslateMatrix44(T, 0.0, 0.0, -2.0)
        
            RY = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RY, currentTime * m3dDegToRad(17.0)*(i+1), 0.0, 1.0, 0.0)
            
            RX = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RX, currentTime * m3dDegToRad(10.0)*(i+1), 1.0, 0.0, 0.0)
            
            mv_matrix = (GLfloat * 16)(*identityMatrix)
            mv_matrix = m3dMultiply(T, m3dMultiply(RY, RX))
            
            mvp_matrix = m3dMultiply(proj_matrix , mv_matrix)
            
            mv_matrix_array_p[i][:] = mvp_matrix


        glUnmapBuffer(GL_UNIFORM_BUFFER)
        glUseProgram(program)
        glDrawElements(GL_TRIANGLES, 36, GL_UNSIGNED_SHORT, 0)

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
    w1 = glutCreateWindow('OpenGL SuperBible - Multiple Viewports')
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
