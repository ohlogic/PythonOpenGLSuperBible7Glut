#!/usr/bin/python3

import sys
import time
import ctypes

fullscreen = True

sys.path.append("./shared")

from sbmloader import SBMObject    # location of sbm file format loader
from ktxloader import KTXObject

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
identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]


myobject = SBMObject()

render_program = GLuint(0)
paused = False

class uniforms:
    proj_matrix = GLint(0)
    mv_matrix = GLint(0)
    clip_plane = GLint(0)
    clip_sphere = GLint(0)

uniform = uniforms()


def shader_load(filename, shader_type):
    result = GLuint(0)
    with open ( filename, "rb") as data:
        result = glCreateShader(shader_type)
        glShaderSource(result, data.read() )
        
    glCompileShader(result)
    if not glGetShaderiv(result, GL_COMPILE_STATUS):
        print( 'compile error:' )
        print( glGetShaderInfoLog(result) )
    return result

def link_from_shaders(shaders, shader_count, delete_shaders, check_errors=False):
    program = GLuint(0)
    program = glCreateProgram()
    
    for i in range(0, shader_count):
        glAttachShader(program, shaders[i])
    
    glLinkProgram(program)
    if not glGetProgramiv(program, GL_LINK_STATUS):
        print( 'link error:' )
        print( glGetProgramInfoLog(program) )
    
    if (delete_shaders):
        for i in range(0, shader_count):
            glDeleteShader(shaders[i])
    return program


def load_shaders():
    global render_program
    global uniform
    
    if (render_program):
        glDeleteProgram(render_program);

    shaders = [
        shader_load("render.vs.glsl", GL_VERTEX_SHADER),
        shader_load("render.fs.glsl", GL_FRAGMENT_SHADER)
    ]

    render_program = link_from_shaders(shaders, 2, True)

    uniform.proj_matrix = glGetUniformLocation(render_program, "proj_matrix");
    uniform.mv_matrix = glGetUniformLocation(render_program, "mv_matrix");
    uniform.clip_plane = glGetUniformLocation(render_program, "clip_plane");
    uniform.clip_sphere = glGetUniformLocation(render_program, "clip_sphere");

tex_dragon=None

class Scene:

    def __init__(self, width, height):
        global myobject, tex_dragon
        
        myobject.load("dragon.sbm");

        load_shaders()

        ktxobj = KTXObject()
        tex_dragon = ktxobj.ktx_load("pattern1.ktx")

    def display(self):
        global paused
        
        currentTime = time.time()

        black = [ 0.0, 0.0, 0.0, 0.0 ]
        one = 1.0

        last_time = 0.0
        total_time = 0.0

        if (not paused):
            total_time += (currentTime - last_time)
        last_time = currentTime

        f = total_time

        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_DEPTH, 0, one)

        glUseProgram(render_program)

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0)

        T1 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T1, 0.0, 0.0, -15.0)
           
        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * 0.34, 0.0, 1.0, 0.0)
           
        T2 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T2, 0.0, -4.0, 0.0)
        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(T1, m3dMultiply(RY, T2))


        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, f * 6.0, 1.0, 0.0, 0.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * 7.3, 0.0, 1.0, 0.0)

        plane_matrix = (GLfloat * 16)(*identityMatrix)
        plane_matrix = m3dMultiply(RX , RY )

        plane = plane_matrix[0:4]
        plane[3] = 0
        plane = normalize(plane)

        clip_sphere = [sin(f * 0.7) * 3.0, cos(f * 1.9) * 3.0, sin(f * 0.1) * 3.0, cos(f * 1.7) + 2.5]

        glUniformMatrix4fv(uniform.proj_matrix, 1, GL_FALSE, proj_matrix)
        glUniformMatrix4fv(uniform.mv_matrix, 1, GL_FALSE, mv_matrix)
        glUniform4fv(uniform.clip_plane, 1, plane)
        glUniform4fv(uniform.clip_sphere, 1, clip_sphere)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CLIP_DISTANCE0)
        glEnable(GL_CLIP_DISTANCE1)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, tex_dragon)
        myobject.render()
        
        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
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
        
        elif key == b'p' or key == b'P':
            paused = not paused
        
        elif key == b'r' or key == b'R':
            pass 
            
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

    w1 = glutCreateWindow('OpenGL SuperBible - Clip Distance')
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
