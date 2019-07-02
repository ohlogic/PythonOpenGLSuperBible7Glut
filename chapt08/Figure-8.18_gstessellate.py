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
mv_location = GLint(0)
mvp_location = GLint(0)
stretch_location = GLint(0)
vao = GLuint(0)
buffer = GLuint(0)

class Scene:

    def __init__(self, width, height):
        global program
        global mv_location
        global mvp_location
        global stretch_location
        global vao
        global buffer
        
        vs_source = '''
// Vertex Shader
// OpenGL SuperBible
#version 410 core

// Incoming per vertex... position and normal
in vec4 vVertex;

void main(void)
{
    gl_Position = vVertex;
}
'''

        gs_source = '''
// Geometry Shader
// Graham Sellers
// OpenGL SuperBible
#version 410 core


layout (triangles) in;
layout (triangle_strip, max_vertices = 12) out;

uniform float stretch = 0.7;

flat out vec4 color;

uniform mat4 mvpMatrix;
uniform mat4 mvMatrix;

void make_face(vec3 a, vec3 b, vec3 c)
{
    vec3 face_normal = normalize(cross(c - a, c - b));
    vec4 face_color = vec4(1.0, 0.4, 0.7, 1.0) * (mat3(mvMatrix) * face_normal).z;
    gl_Position = mvpMatrix * vec4(a, 1.0);
    color = face_color;
    EmitVertex();

    gl_Position = mvpMatrix * vec4(b, 1.0);
    color = face_color;
    EmitVertex();

    gl_Position = mvpMatrix * vec4(c, 1.0);
    color = face_color;
    EmitVertex();

    EndPrimitive();
}

void main(void)
{
    int n;
    vec3 a = gl_in[0].gl_Position.xyz;
    vec3 b = gl_in[1].gl_Position.xyz;
    vec3 c = gl_in[2].gl_Position.xyz;

    vec3 d = (a + b) * stretch;
    vec3 e = (b + c) * stretch;
    vec3 f = (c + a) * stretch;

    a *= (2.0 - stretch);
    b *= (2.0 - stretch);
    c *= (2.0 - stretch);

    make_face(a, d, f);
    make_face(d, b, e);
    make_face(e, c, f);
    make_face(d, e, f);

    EndPrimitive();
}
'''

        fs_source = '''
// Fragment Shader
// Graham Sellers
// OpenGL SuperBible
#version 410 core

flat in vec4 color;

out vec4 output_color;

void main(void)
{
    output_color = color;
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

        mv_location = glGetUniformLocation(program, "mvMatrix")
        mvp_location = glGetUniformLocation(program, "mvpMatrix")
        stretch_location = glGetUniformLocation(program, "stretch")

        tetrahedron_verts = np.array([
        
             0.000,  0.000,  1.000,
             0.943,  0.000, -0.333,
            -0.471,  0.816, -0.333,
            -0.471, -0.816, -0.333
        ], dtype=np.float32)

        tetrahedron_indices = np.array([
        
            0, 1, 2,
            0, 2, 3,
            0, 3, 1,
            3, 2, 1
        ], dtype=np.uint16)

        size_t_verts = ctypes.sizeof(ctypes.c_float)*len(tetrahedron_verts)
        size_t_indices = ctypes.sizeof(ctypes.c_ushort)*len(tetrahedron_indices)

        glGenVertexArrays(1, vao)
        glBindVertexArray(vao)

        glGenBuffers(1, buffer)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, buffer)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, size_t_verts + size_t_indices, None, GL_STATIC_DRAW)
        glBufferSubData(GL_ELEMENT_ARRAY_BUFFER, 0, size_t_indices, tetrahedron_indices)
        glBufferSubData(GL_ELEMENT_ARRAY_BUFFER, size_t_indices, size_t_verts, tetrahedron_verts)

        glBindBuffer(GL_ARRAY_BUFFER, buffer)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(size_t_indices) )
        glEnableVertexAttribArray(0)

        glEnable(GL_CULL_FACE)
        #// glDisable(GL_CULL_FACE)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)


    def display(self):

        currentTime = time.time()

        black = [ 0.0, 0.0, 0.0, 1.0 ]
        one = 1.0
        f = currentTime

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_DEPTH, 0, one)

        glUseProgram(program)

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), .1, 1000.0)

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, 0.0, -8.0)
    
        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, currentTime * m3dDegToRad(17.0), 0.0, 1.0, 0.0)
        
        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, currentTime * m3dDegToRad(10.0), 1.0, 0.0, 0.0)
        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(T, m3dMultiply(RY, RX))

        glUniformMatrix4fv(mvp_location, 1, GL_FALSE, m3dMultiply(proj_matrix , mv_matrix) )

        glUniformMatrix4fv(mv_location, 1, GL_FALSE, mv_matrix)

        glUniform1f(stretch_location, sin(f * 4.0) * 0.75 + 1.0)

        glBindVertexArray(vao);
        glDrawElements(GL_TRIANGLES, 12, GL_UNSIGNED_SHORT, None)



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
    w1 = glutCreateWindow('OpenGL SuperBible - Geometry Shader Tessellation')
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
