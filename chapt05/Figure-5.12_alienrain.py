#!/usr/bin/python3

import sys
import time

sys.path.append("./shared")

#from sbmloader import SBMObject    # location of sbm file format loader
from ktxloader import KTXObject    # location of ktx file format loader

#from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate, m3dScaleMatrix44

fullscreen = True

import numpy.matlib
import numpy as np
import math 

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

identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

render_prog = GLuint(0)
render_vao = GLuint(0)

tex_alien_array = GLuint(0)
rain_buffer = GLuint(0)

droplet_x_offset = []
droplet_rot_speed = []
droplet_fall_speed = []


seed = 0x13371337
import random
import ctypes
random.seed (0x13371337)
def random_float():
    # global seed
    # res=0.0
    # tmp=0

    # seed *= 16807;

    # tmp = seed ^ (seed >> 4) ^ (seed << 15);

    # res = (tmp >> 9) | 0x3F800000;

    # return (res - 1.0);
    return (random.random() - 1.0)

class Scene:

    def __init__(self, width, height):
        global render_prog
        global render_vao
        global tex_alien_array
        global rain_buffer

        global droplet_x_offset, droplet_rot_speed, droplet_fall_speed

        self.width = width
        self.height = height

        vs = GLuint(0)
        fs = GLuint(0)

        vs_source = '''
#version 410 core

layout (location = 0) in int alien_index;

out VS_OUT
{
    flat int alien;
    vec2 tc;
} vs_out;

struct droplet_t
{
    float x_offset;
    float y_offset;
    float orientation;
    float unused;
};

layout (std140) uniform droplets
{
    droplet_t droplet[256];
};

void main(void)
{
    const vec2[4] position = vec2[4](vec2(-0.5, -0.5),
                                     vec2( 0.5, -0.5),
                                     vec2(-0.5,  0.5),
                                     vec2( 0.5,  0.5));
    vs_out.tc = position[gl_VertexID].xy + vec2(0.5);
    float co = cos(droplet[alien_index].orientation);
    float so = sin(droplet[alien_index].orientation);
    mat2 rot = mat2(vec2(co, so),
                    vec2(-so, co));
    vec2 pos = 0.25 * rot * position[gl_VertexID];
    gl_Position = vec4(pos.x + droplet[alien_index].x_offset,
                       pos.y + droplet[alien_index].y_offset,
                       0.5, 1.0);
    vs_out.alien = alien_index % 64;
}

'''

        fs_source = '''
#version 410 core

layout (location = 0) out vec4 color;

in VS_OUT
{
    flat int alien;
    vec2 tc;
} fs_in;

uniform sampler2DArray tex_aliens;

void main(void)
{
    color = texture(tex_aliens, vec3(fs_in.tc, float(fs_in.alien)));
}

'''

        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)

        glGetShaderInfoLog(vs)

        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source)
        glCompileShader(fs)

        glGetShaderInfoLog(vs)

        render_prog = glCreateProgram()
        glAttachShader(render_prog, vs)
        glAttachShader(render_prog, fs)
        glLinkProgram(render_prog)

        glDeleteShader(vs)
        glDeleteShader(fs)

        glGetProgramInfoLog(render_prog)

        glGenVertexArrays(1, render_vao)
        glBindVertexArray(render_vao)

        ktxobj = KTXObject()

        tex_alien_array = ktxobj.ktx_load("aliens.ktx")

        glBindTexture(GL_TEXTURE_2D_ARRAY, tex_alien_array)
        glTexParameteri(GL_TEXTURE_2D_ARRAY, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)

        glGenBuffers(1, rain_buffer)
        glBindBuffer(GL_UNIFORM_BUFFER, rain_buffer)
        

        glBufferData(GL_UNIFORM_BUFFER, 256*4*4, None, GL_DYNAMIC_DRAW)


        for i in range(0, 256):
            droplet_x_offset.append(random_float() * 2.0 - 1.0)
            droplet_rot_speed.append( (random_float() + 0.5) * (-3.0 if (i & 1) else 3.0)  )
            droplet_fall_speed.append ( random_float() + 0.2 )
            
        glBindVertexArray(render_vao);
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    def display(self):
        global rain_buffer

        green = [ 0.0, 0.1, 0.0, 0.0 ]
        currentTime = time.time()
        t = currentTime
        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, green)

        glUseProgram(render_prog);

        glBindBufferBase(GL_UNIFORM_BUFFER, 0, rain_buffer);
        droplet = glMapBufferRange(GL_UNIFORM_BUFFER, 0, 256*4*4, GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)
        float_array = ((ctypes.c_float * 4) * 256).from_address(droplet) 
        
        for i in range(0, 256):
            float_array[i][0] =  droplet_x_offset[i] + 2
            float_array[i][1] =  2.0-math.fmod((t + float(i)) * droplet_fall_speed[i], 4.31 ) * random_float()
            float_array[i][2] =  droplet_rot_speed[i] * t * random_float() * math.pi
            float_array[i][3] = 0.0
            
        glUnmapBuffer(GL_UNIFORM_BUFFER);

        for alien_index in range(0, 256):
            glVertexAttribI1i(0, alien_index);
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);


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

    w1 = glutCreateWindow('OpenGL SuperBible - Alien Rain')
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
