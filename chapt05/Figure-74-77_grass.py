#!/usr/bin/python3

# download grass_support.zip for file dependencies

import sys
import time

sys.path.append("./shared")

#from sbmloader import SBMObject    # location of sbm file format loader
from ktxloader import KTXObject    # location of ktx file format loader

from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate, m3dScaleMatrix44, \
    scale, m3dLookAt

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

from array import array
from math import sin, cos
identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]


grass_buffer = GLuint(0)
grass_vao = GLuint(0)
grass_program = GLuint(0)
tex_grass_color = GLuint(0)
tex_grass_length = GLuint(0)
tex_grass_orientation = GLuint(0)
tex_grass_bend = GLuint(0)

class uniforms:
    mvpMatrix = GLint

uniform = uniforms()

class Scene:

    def __init__(self, width, height):

        global grass_buffer
        global grass_vao
        global grass_program
        global tex_grass_color
        global tex_grass_length
        global tex_grass_orientation
        global tex_grass_bend
        global uniform

        self.width = width
        self.height = height

        grass_vs = GLuint(0)
        grass_fs = GLuint(0)

        grass_vs_source = '''
#version 420 core

// Incoming per vertex position
in vec4 vVertex;

// Output varyings
out vec4 color;

uniform mat4 mvpMatrix;

layout (binding = 0) uniform sampler1D grasspalette_texture;
layout (binding = 1) uniform sampler2D length_texture;
layout (binding = 2) uniform sampler2D orientation_texture;
layout (binding = 3) uniform sampler2D grasscolor_texture;
layout (binding = 4) uniform sampler2D bend_texture;

int random(int seed, int iterations)
{
    int value = seed;
    int n;

    for (n = 0; n < iterations; n++) {
        value = ((value >> 7) ^ (value << 9)) * 15485863;
    }

    return value;
}

vec4 random_vector(int seed)
{
    int r = random(gl_InstanceID, 4);
    int g = random(r, 2);
    int b = random(g, 2);
    int a = random(b, 2);

    return vec4(float(r & 0x3FF) / 1024.0,
                float(g & 0x3FF) / 1024.0,
                float(b & 0x3FF) / 1024.0,
                float(a & 0x3FF) / 1024.0);
}

mat4 construct_rotation_matrix(float angle)
{
    float st = sin(angle);
    float ct = cos(angle);

    return mat4(vec4(ct, 0.0, st, 0.0),
                vec4(0.0, 1.0, 0.0, 0.0),
                vec4(-st, 0.0, ct, 0.0),
                vec4(0.0, 0.0, 0.0, 1.0));
}

void main(void)
{
    vec4 offset = vec4(float(gl_InstanceID >> 10) - 512.0,
                       0.0f,
                       float(gl_InstanceID & 0x3FF) - 512.0,
                       0.0f);
    int number1 = random(gl_InstanceID, 3);
    int number2 = random(number1, 2);
    offset += vec4(float(number1 & 0xFF) / 256.0,
                   0.0f,
                   float(number2 & 0xFF) / 256.0,
                   0.0f);
    // float angle = float(random(number2, 2) & 0x3FF) / 1024.0;

    vec2 texcoord = offset.xz / 1024.0 + vec2(0.5);

    // float bend_factor = float(random(number2, 7) & 0x3FF) / 1024.0;
    float bend_factor = texture(bend_texture, texcoord).r * 2.0;
    float bend_amount = cos(vVertex.y);

    float angle = texture(orientation_texture, texcoord).r * 2.0 * 3.141592;
    mat4 rot = construct_rotation_matrix(angle);
    vec4 position = (rot * (vVertex + vec4(0.0, 0.0, bend_amount * bend_factor, 0.0))) + offset;

    position *= vec4(1.0, texture(length_texture, texcoord).r * 0.9 + 0.3, 1.0, 1.0);

    gl_Position = mvpMatrix * position; // (rot * position);
    // color = vec4(random_vector(gl_InstanceID).xyz * vec3(0.1, 0.5, 0.1) + vec3(0.1, 0.4, 0.1), 1.0);
    // color = texture(orientation_texture, texcoord);
    color = texture(grasspalette_texture, texture(grasscolor_texture, texcoord).r) +
            vec4(random_vector(gl_InstanceID).xyz * vec3(0.1, 0.5, 0.1), 1.0);
}
'''

        grass_fs_source = '''
#version 420 core

in vec4 color;

out vec4 output_color;

void main(void)
{
    output_color = color;
}
'''

        grass_blade = [
            -0.3, 0.0,
             0.3, 0.0,
            -0.20, 1.0,
             0.1, 1.3,
            -0.05, 2.3,
             0.0, 3.3]

        glGenBuffers(1, grass_buffer)
        glBindBuffer(GL_ARRAY_BUFFER, grass_buffer)
        
        ar=array("f",grass_blade)

        glBufferData(GL_ARRAY_BUFFER, ar.tostring(), GL_STATIC_DRAW)

        glGenVertexArrays(1, grass_vao)
        glBindVertexArray(grass_vao)

        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)

        grass_program = glCreateProgram()
        grass_vs = glCreateShader(GL_VERTEX_SHADER)
        grass_fs = glCreateShader(GL_FRAGMENT_SHADER)

        glShaderSource(grass_vs, grass_vs_source)
        glShaderSource(grass_fs, grass_fs_source)

        glCompileShader(grass_vs)
        glCompileShader(grass_fs)

        glAttachShader(grass_program, grass_vs)
        glAttachShader(grass_program, grass_fs)

        glLinkProgram(grass_program)
        glDeleteShader(grass_fs)
        glDeleteShader(grass_vs)

        uniform.mvpMatrix = glGetUniformLocation(grass_program, "mvpMatrix");
        
        ktx = KTXObject()
        
        glActiveTexture(GL_TEXTURE1)
        tex_grass_length = ktx.ktx_load("grass_length.ktx")
        glActiveTexture(GL_TEXTURE2)
        tex_grass_orientation = ktx.ktx_load("grass_orientation.ktx")
        glActiveTexture(GL_TEXTURE3)
        tex_grass_color = ktx.ktx_load("grass_color.ktx")
        glActiveTexture(GL_TEXTURE4)
        tex_grass_bend = ktx.ktx_load("grass_bend.ktx")



    def display(self):

        currentTime = time.time()
        t = currentTime * 0.02

        r = 550.0

        black = [ 0.0, 0.0, 0.0, 1.0 ]
        one = 1.0;
        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_DEPTH, 0, one)

        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dLookAt([sin(t) * r, 25.0, cos(t) * r], [0.0, -50.0, 0.0], [0.0, 1.0, 0.0])

        prj_matrix = (GLfloat * 16)(*identityMatrix)
        prj_matrix = m3dPerspective(m3dDegToRad(45.0), float(self.width) / float(self.height), 0.1, 1000.0)

        glUseProgram(grass_program)
        glUniformMatrix4fv(uniform.mvpMatrix, 1, GL_FALSE, m3dMultiply(prj_matrix , mv_matrix))

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

        glViewport(0, 0, self.width, self.height)

        glBindVertexArray(grass_vao);
        glDrawArraysInstanced(GL_TRIANGLE_STRIP, 0, 6, 1024 * 1024)

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

    w1 = glutCreateWindow('OpenGL SuperBible - Grass')
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
