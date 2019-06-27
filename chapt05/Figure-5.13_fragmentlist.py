#!/usr/bin/python3

# dependency files for this example are found in the same github folder in dragon_support.zip

import sys
import time

sys.path.append("./shared")

from sbmloader import SBMObject    # location of sbm file format loader
from ktxloader import KTXObject    # location of ktx file format loader

from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate, m3dScaleMatrix44

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

clear_program = GLuint(0)
append_program = GLuint(0)
resolve_program = GLuint(0)

class textures:
    color = GLuint(0)
    normals = GLuint(0)

class uniforms_block:
    mv_matrix   = (GLfloat * 16)(*identityMatrix)
    view_matrix = (GLfloat * 16)(*identityMatrix)
    proj_matrix = (GLfloat * 16)(*identityMatrix)

uniforms_buffer = GLuint(0)

class uniforms:
    mvp = GLuint(0)

fragment_buffer = GLuint(0)
head_pointer_image = GLuint(0)
atomic_counter_buffer = GLuint(0)
dummy_vao = GLuint(0)

uniform = uniforms()
myobject = SBMObject()

def length(v):
    return math.sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])

def normalize(v):
    l = length(v)
    #if (v[0] == 0 and v[1] == 0 and v[2] ==0):
    #    return [0.0, 1/3, 0.0]
    return [v[0]/l, v[1]/l, v[2]/l]
    
def dot(v0, v1):
    return v0[0]*v1[0]+v0[1]*v1[1]+v0[2]*v1[2]

def cross(v0, v1):
    return [
        v0[1]*v1[2]-v1[1]*v0[2],
        v0[2]*v1[0]-v1[2]*v0[0],
        v0[0]*v1[1]-v1[0]*v0[1]]

def m3dLookAt(eye, target, up):
    mz = normalize( (eye[0]-target[0], eye[1]-target[1], eye[2]-target[2]) ) # inverse line of sight
    mx = normalize( cross( up, mz ) )
    my = normalize( cross( mz, mx ) )
    tx =  dot( mx, eye )
    ty =  dot( my, eye )
    tz = -dot( mz, eye )   
    return np.array([mx[0], my[0], mz[0], 0, mx[1], my[1], mz[1], 0, mx[2], my[2], mz[2], 0, tx, ty, tz, 1])

def scale(s):
    return [s,0,0,0, 0,s,0,0, 0,0,s,0, 0,0,0,1] 

def link_from_shaders(shaders, shader_count, delete_shaders, check_errors=False):

    program = GLuint(0)

    program = glCreateProgram()

    for i in range(0, shader_count):
        glAttachShader(program, shaders[i]);
    
    glLinkProgram(program);

    if (delete_shaders):

        for i in range(0, shader_count):
            glDeleteShader(shaders[i]);

    return program

    
def shader_load(filename, shader_type):
    
    result = GLuint(0)
    
    with open ( filename, "rb") as data:
        
        result = glCreateShader(shader_type)
        
        glShaderSource(result, data.read() )
        
    glCompileShader(result)
    
    return result
    
    
def load_shaders():
    global clear_program
    global append_program
    global resolve_program
    global uniform
    
    shaders = [GLuint(0), GLuint(0)]

    shaders[0] = shader_load("fragmentlist_shaders/clear.vs.glsl", GL_VERTEX_SHADER);
    
    shaders[1] = shader_load("fragmentlist_shaders/clear.fs.glsl", GL_FRAGMENT_SHADER);

    if (clear_program):
        glDeleteProgram(clear_program);

    clear_program = link_from_shaders(shaders, 2, True);

    shaders[0] = shader_load("fragmentlist_shaders/append.vs.glsl", GL_VERTEX_SHADER);
    shaders[1] = shader_load("fragmentlist_shaders/append.fs.glsl", GL_FRAGMENT_SHADER);

    if (append_program):
        glDeleteProgram(append_program);

    append_program = link_from_shaders(shaders, 2, True);

    uniform.mvp = glGetUniformLocation(append_program, "mvp");

    shaders[0] = shader_load("fragmentlist_shaders/resolve.vs.glsl", GL_VERTEX_SHADER);
    shaders[1] = shader_load("fragmentlist_shaders/resolve.fs.glsl", GL_FRAGMENT_SHADER);

    if (resolve_program):
        glDeleteProgram(resolve_program)

    resolve_program = link_from_shaders(shaders, 2, True);


class Scene:

    def __init__(self, width, height):
        
        global uniforms_buffer
        global fragment_buffer
        global atomic_counter_buffer
        global head_pointer_image
        global dummy_vao
        global myobject

        self.width = width
        self.height = height

        load_shaders()

        glGenBuffers(1, uniforms_buffer)
        glBindBuffer(GL_UNIFORM_BUFFER, uniforms_buffer)
        glBufferData(GL_UNIFORM_BUFFER, sizeof(GLfloat * 16 *3), None, GL_DYNAMIC_DRAW)

        myobject.load("dragon.sbm")

        glGenBuffers(1, fragment_buffer)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, fragment_buffer);
        glBufferData(GL_SHADER_STORAGE_BUFFER, 1024 * 1024 * 16, None, GL_DYNAMIC_COPY)

        glGenBuffers(1, atomic_counter_buffer);
        glBindBuffer(GL_ATOMIC_COUNTER_BUFFER, atomic_counter_buffer);
        glBufferData(GL_ATOMIC_COUNTER_BUFFER, 4, None, GL_DYNAMIC_COPY);

        head_pointer_image = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, head_pointer_image);
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_R32UI, 1024, 1024);

        glGenVertexArrays(1, dummy_vao);
        glBindVertexArray(dummy_vao);


    def display(self):

        green = [ 0.0, 0.1, 0.0, 0.0 ]
        currentTime = time.time()
        f = currentTime

        zeros = [ 0.0, 0.0, 0.0, 0.0 ]
        gray = [ 0.1, 0.1, 0.1, 0.0 ]
        ones = [ 1.0 ]

        glViewport(0, 0, self.width , self.height);

        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT | GL_ATOMIC_COUNTER_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT);

        glUseProgram(clear_program);
        glBindVertexArray(dummy_vao);
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);

        glUseProgram(append_program)

        model_matrix = (GLfloat * 16)(*identityMatrix)
        model_matrix = scale(6.0)
        
        view_matrix = (GLfloat * 16)(*identityMatrix)
        view_matrix = m3dLookAt([math.cos(f * 0.35) * 120.0, math.cos(f * 0.4) * 30.0, math.sin(f * 0.35) * 120.0], 
            [0.0, -20.0, 0.0], 
            [0.0, 1, 0.0])
        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(view_matrix , model_matrix)

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0)

        glUniformMatrix4fv(uniform.mvp, 1, GL_FALSE, m3dMultiply(proj_matrix , mv_matrix))

        zero = 0;
        glBindBufferBase(GL_ATOMIC_COUNTER_BUFFER, 0, atomic_counter_buffer)
        
        # next line not working ????
        #glBufferSubData(GL_ATOMIC_COUNTER_BUFFER, 0, sys.getsizeof(zero), zero);

        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, fragment_buffer)

        glBindImageTexture(0, head_pointer_image, 0, GL_FALSE, 0, GL_READ_WRITE, GL_R32UI)

        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT | GL_ATOMIC_COUNTER_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)

        myobject.render()

        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT | GL_ATOMIC_COUNTER_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)

        glUseProgram(resolve_program)

        glBindVertexArray(dummy_vao)

        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT | GL_ATOMIC_COUNTER_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

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

    w1 = glutCreateWindow('OpenGL SuperBible - Fragment List')
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
    