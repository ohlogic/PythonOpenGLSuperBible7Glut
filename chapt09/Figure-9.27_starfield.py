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
from math import cos, sin, floor
import glm
identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

myobject = SBMObject()
ktxobject = KTXObject()
overlay = OVERLAY_()

render_prog = GLuint(0)
star_texture = GLuint(0)
star_vao = GLuint(0)
star_buffer = GLuint(0)

debugcontext=True
errors_only=True 

class UNIFORMS_:
    time=0
    proj_matrix=0

uniforms = UNIFORMS_()

NUM_STARS = 2000

import random
random.seed (0x13371337)

def random_float():
    return random.random()

def checkGLError():
    status = glGetError()
    if status != GL_NO_ERROR:
        raise RuntimeError('gl error %s' % (status,))

@GLDEBUGPROC
def CB_OpenGL_DebugMessage(source, type, id, severity, length, message, userParam):
    msg = message[0:length]
    print('debug:', msg)

class Scene:
    def __init__(self, width, height):
        global render_prog
        global star_vao
        global star_buffer
        global uniforms
        global star_texture

        self.width = width
        self.height = height

        vs = GLuint(0)
        fs = GLuint(0)


        fs_source = '''
#version 410 core

layout (location = 0) out vec4 color;

uniform sampler2D tex_star;
flat in vec4 starColor;

void main(void)
{
    color = starColor * texture(tex_star, gl_PointCoord);
    //color.r = 1.0;
}
'''

        vs_source = '''
#version 410 core

layout (location = 0) in vec4 position;
layout (location = 1) in vec4 color;

uniform float time;
uniform mat4 proj_matrix;

flat out vec4 starColor;

void main(void)
{
    vec4 newVertex = position;

    newVertex.z += time;
    newVertex.z = fract(newVertex.z);

    float size = (20.0 * newVertex.z * newVertex.z);

    starColor = smoothstep(1.0, 7.0, size) * color;

    newVertex.z = (999.9 * newVertex.z) - 1000.0;
    gl_Position = proj_matrix * newVertex;
    gl_PointSize = size;
}
'''
        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)
        if not glGetShaderiv(vs, GL_COMPILE_STATUS):
            print( 'compile error:' )
            print( glGetShaderInfoLog(vs) )

        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source)
        glCompileShader(fs)
        if not glGetShaderiv(fs, GL_COMPILE_STATUS):
            print( 'compile error:' )
            print( glGetShaderInfoLog(fs) )

        render_prog = glCreateProgram()
        glAttachShader(render_prog, vs)
        glAttachShader(render_prog, fs)
        glLinkProgram(render_prog)
        if not glGetProgramiv(render_prog, GL_LINK_STATUS):
            print( 'link error:' )
            print( glGetProgramInfoLog(render_prog) )

        glDeleteShader(vs)
        glDeleteShader(fs)

        uniforms.time = glGetUniformLocation(render_prog, "time")
        uniforms.proj_matrix = glGetUniformLocation(render_prog, "proj_matrix")

        star_texture = ktxobject.ktx_load("star.ktx")

        glGenVertexArrays(1, star_vao)
        glBindVertexArray(star_vao)

        class star_t:
            position = glm.vec3
            color = glm.vec3

        size_star_t = ctypes.sizeof(ctypes.c_float) * 6;      # same as glm.sizeof(glm.vec3) * 2

        glGenBuffers(1, star_buffer)
        glBindBuffer(GL_ARRAY_BUFFER, star_buffer)
        glBufferData(GL_ARRAY_BUFFER, NUM_STARS * size_star_t, None, GL_STATIC_DRAW)

        star = glMapBufferRange(GL_ARRAY_BUFFER, 0, NUM_STARS * size_star_t, GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

        m = (GLfloat * 6 * NUM_STARS).from_address(star)

        for i in range(0, 1000):

            m[i][0] = (random_float() * 2.0 - 1.0) * 100.0
            m[i][1] = (random_float() * 2.0 - 1.0) * 100.0
            m[i][2] = random_float()
            m[i][3] = 0.8 + random_float() * 0.2
            m[i][4] = 0.8 + random_float() * 0.2
            m[i][5] = 0.8 + random_float() * 0.2

        glUnmapBuffer(GL_ARRAY_BUFFER)

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, size_star_t, None)

        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, size_star_t, ctypes.c_void_p(glm.sizeof(glm.vec3) )  )
        glEnableVertexAttribArray(0)
        glEnableVertexAttribArray(1)


    def display(self):
        global render_prog
        global star_vao
        global uniforms

        currentTime = time.time()

        black = [ 0.0, 0.0, 0.0, 0.0 ]
        one = [ 1.0 ]
        t = currentTime

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0)

        t *= 0.1
        t -= floor(t)

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_DEPTH, 0, one)

        glUseProgram(render_prog)

        glUniform1f(uniforms.time, t)
        glUniformMatrix4fv(uniforms.proj_matrix, 1, GL_FALSE, proj_matrix)


        glEnable(GL_BLEND)

        glBlendFunc(GL_ONE, GL_ONE)


        glBindVertexArray(star_vao)

        glEnable(GL_PROGRAM_POINT_SIZE)
        glDrawArrays(GL_POINTS, 0, NUM_STARS)



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

    glutInitContextVersion(4,1)
    glutInitContextProfile(GLUT_CORE_PROFILE)

    w1 = glutCreateWindow('OpenGL SuperBible - Starfield')

    if debugcontext:

        glDebugMessageCallback(CB_OpenGL_DebugMessage, None)

        if errors_only:
            glDebugMessageControl(GL_DONT_CARE, GL_DONT_CARE, GL_DONT_CARE, 0, None, GL_FALSE)
            glDebugMessageControl(GL_DEBUG_SOURCE_API, GL_DEBUG_TYPE_ERROR, GL_DONT_CARE, 0, None, GL_TRUE)
        else:
            glDebugMessageControl(GL_DONT_CARE, GL_DONT_CARE, GL_DONT_CARE, 0, None, GL_TRUE)

        glEnable(GL_DEBUG_OUTPUT)
        glEnable(GL_DEBUG_OUTPUT_SYNCHRONOUS)
        glDebugMessageInsert(GL_DEBUG_SOURCE_APPLICATION, GL_DEBUG_TYPE_MARKER, 0, GL_DEBUG_SEVERITY_NOTIFICATION, -1, "Starting debug messaging service")



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