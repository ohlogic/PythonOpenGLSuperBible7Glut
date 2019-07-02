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
proj_location = GLint(0)
explode_factor_location = GLint(0)



patch_data = [glm.vec3() for _ in range(16)]


class Scene:

    def __init__(self, width, height):
        global myobject
        global program
        global mv_location
        global proj_location
        global explode_factor_location
        
        vs_source = '''
#version 410 core

layout (location = 0) in vec4 position;
layout (location = 1) in vec3 normal;

out VS_OUT
{
    vec3 normal;
    vec4 color;
} vs_out;

uniform mat4 mv_matrix;
uniform mat4 proj_matrix;

void main(void)
{
    gl_Position = proj_matrix * mv_matrix * position;
    vs_out.color = position * 2.0 + vec4(0.5, 0.5, 0.5, 0.0);
    vs_out.normal = normalize(mat3(mv_matrix) * normal);
}
'''

        gs_source = '''
#version 410 core

layout (triangles) in;
layout (triangle_strip, max_vertices = 3) out;

in VS_OUT
{
    vec3 normal;
    vec4 color;
} gs_in[];

out GS_OUT
{
    vec3 normal;
    vec4 color;
} gs_out;

uniform float explode_factor = 0.2;

void main(void)
{
    vec3 ab = gl_in[1].gl_Position.xyz - gl_in[0].gl_Position.xyz;
    vec3 ac = gl_in[2].gl_Position.xyz - gl_in[0].gl_Position.xyz;
    vec3 face_normal = -normalize(cross(ab, ac));
    for (int i = 0; i < gl_in.length(); i++)
    {
        gl_Position = gl_in[i].gl_Position + vec4(face_normal * explode_factor, 0.0);
        gs_out.normal = gs_in[i].normal;
        gs_out.color = gs_in[i].color;
        EmitVertex();
    }
    EndPrimitive();
}
'''

        fs_source = '''
#version 410 core

out vec4 color;

in GS_OUT
{
    vec3 normal;
    vec4 color;
} fs_in;

void main(void)
{
    color = vec4(1.0) * abs(normalize(fs_in.normal).z);
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

        mv_location = glGetUniformLocation(program, "mv_matrix")
        proj_location = glGetUniformLocation(program, "proj_matrix")
        explode_factor_location = glGetUniformLocation(program, "explode_factor")

        myobject.load("torus.sbm")

        #// glEnable(GL_CULL_FACE)
        #//glCullFace(GL_FRONT)

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
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 1.0, 1000.0)

        # vmath::mat4 proj_matrix = vmath::perspective(50.0f,
                                                     # (float)info.windowWidth / (float)info.windowHeight,
                                                     # 0.1f,
                                                     # 1000.0f)
                                                     
                                                     
        glUniformMatrix4fv(proj_location, 1, GL_FALSE, proj_matrix)


        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, 0.0, -3.0)
        
        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, currentTime * m3dDegToRad(81.0), 0.0, 1.0, 0.0)  
        
        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, currentTime * m3dDegToRad(45.0), 1.0, 0.0, 0.0)


        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(T, m3dMultiply(RY, RX))

        # vmath::mat4 mv_matrix = vmath::translate(0.0f, 0.0f, -3.0f) *
                                # vmath::rotate((float)currentTime * 45.0f, 0.0f, 1.0f, 0.0f) *
                                # vmath::rotate((float)currentTime * 81.0f, 1.0f, 0.0f, 0.0f)
        
        
        glUniformMatrix4fv(mv_location, 1, GL_FALSE, mv_matrix)

        glUniform1f(explode_factor_location, sin(currentTime * 8.0) * cos(currentTime * 6.0) * 0.7 + 0.1)

        myobject.render()


        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global show_cage
        global show_points
        global wireframe
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
    w1 = glutCreateWindow('OpenGL SuperBible - Exploder')
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
