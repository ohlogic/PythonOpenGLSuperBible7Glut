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
from math import cos, sin, pow
import glm
identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

myobject = SBMObject()
ktxobject = KTXObject()
overlay = OVERLAY_()

per_fragment_program = GLuint(0)

class textures_:
    color = GLuint(0)
    normals = GLuint(0)

textures = textures_()

class uniforms_block_:
    mv_matrix = (GLfloat * 16)(*identityMatrix)
    view_matrix = (GLfloat * 16)(*identityMatrix)
    proj_matrix = (GLfloat * 16)(*identityMatrix)

uniforms_block = uniforms_block_()


uniforms_buffer = GLuint(0)

class uniforms_:
    def __init__(self):
        self.diffuse_albedo = GLint(0)
        self.specular_albedo = GLint(0)
        self.specular_power = GLint(0)
    
uniforms = [ uniforms_() for _ in range(2)]
    
MANY_OBJECTS = False
    
def load_shaders():
    global per_fragment_program
    global uniforms
    
    vs = GLuint(0)
    fs = GLuint(0)

    vs = shader_load("blinnphong.vs.glsl", GL_VERTEX_SHADER)
    fs =shader_load("blinnphong.fs.glsl", GL_FRAGMENT_SHADER)

    if (per_fragment_program):
        glDeleteProgram(per_fragment_program)

    per_fragment_program = glCreateProgram()
    glAttachShader(per_fragment_program, vs)
    glAttachShader(per_fragment_program, fs)
    glLinkProgram(per_fragment_program)

    uniforms[0].diffuse_albedo = glGetUniformLocation(per_fragment_program, "diffuse_albedo")
    uniforms[0].specular_albedo = glGetUniformLocation(per_fragment_program, "specular_albedo")
    uniforms[0].specular_power = glGetUniformLocation(per_fragment_program, "specular_power")


class Scene:

    def __init__(self, width, height):
        global myobject
        global uniforms_buffer
        
        self.width = width
        self.height = height
        
        load_shaders()

        size_uniforms_block = ctypes.sizeof(GLfloat) * 16 * 3

        uniforms_buffer = glGenBuffers(1)
        glBindBuffer(GL_UNIFORM_BUFFER, uniforms_buffer)
        glBufferData(GL_UNIFORM_BUFFER, size_uniforms_block, None, GL_DYNAMIC_DRAW)

        myobject.load("sphere.sbm")

        glEnable(GL_CULL_FACE)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        
    
    def display(self):
        global uniforms
        global per_fragment_program
        
        currentTime = time.time()

        zeros = [ 0.0, 0.0, 0.0, 0.0 ]
        gray = [ 0.1, 0.1, 0.1, 0.0 ]
        ones = [ 1.0 ]
        f = currentTime

        glUseProgram(per_fragment_program)
        glViewport(0, 0, self.width, self.height)

        glClearBufferfv(GL_COLOR, 0, gray)
        glClearBufferfv(GL_DEPTH, 0, ones)

        # /*
        # vmath::mat4 model_matrix = vmath::rotate((float)currentTime * 14.5f, 0.0f, 1.0f, 0.0f) *
                                   # vmath::rotate(180.0f, 0.0f, 0.0f, 1.0f) *
                                   # vmath::rotate(20.0f, 1.0f, 0.0f, 0.0f)
                                   # */

        view_position = [0.0, 0.0, 50.0]
        
        view_matrix = (GLfloat * 16)(*identityMatrix)
        view_matrix = m3dLookAt(view_position,
                                (0.0, 0.0, 0.0),
                                (0.0, 1.0, 0.0))

        light_position = [-20.0, -20.0, 0.0]

        light_proj_matrix = glm.frustum(-1.0, 1.0, -1.0, 1.0, 1.0, 200.0)
        
        light_view_matrix = (GLfloat * 16)(*identityMatrix)
        light_view_matrix = m3dLookAt(light_position,
                                      (0.0, 0.0, 0.0), 
                                      (0.0, 1.0, 0.0))

        if (MANY_OBJECTS):
            
            size_uniforms_block = ctypes.sizeof(GLfloat) * 16 * 3
            
            for j in range(0, 7):

                for i in range(0, 7):

                    glBindBufferBase(GL_UNIFORM_BUFFER, 0, uniforms_buffer)
                    block = glMapBufferRange(GL_UNIFORM_BUFFER,
                                            0,
                                            size_uniforms_block,
                                            GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

                    blockp = (GLfloat * 16 * 3).from_address(block)

                    model_matrix = (GLfloat * 16)(*identityMatrix)
                    m3dTranslateMatrix44(model_matrix, i * 2.75 - 8.25, 6.75 - j * 2.25, 0.0)

                    blockp[0] = m3dMultiply(view_matrix , model_matrix)
                    blockp[1] = (GLfloat * 16)(*view_matrix)
                    
                    proj_matrix = (GLfloat * 16)(*identityMatrix)
                    blockp[2] = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0)

                    glUnmapBuffer(GL_UNIFORM_BUFFER)
                    
                    per_vertex=1
                    glUniform1f(uniforms[1 if per_vertex==0 else 0].specular_power, pow(2.0, j + 2.0))
                    glUniform3fv(uniforms[1 if per_vertex==0 else 0].specular_albedo, 1, (i / 9.0 + 1.0 / 9.0))

                    myobject.render()
        else:
        
        
            size_uniforms_block = ctypes.sizeof(GLfloat) * 16 * 3
        
        
            glBindBufferBase(GL_UNIFORM_BUFFER, 0, uniforms_buffer)
            block = glMapBufferRange(GL_UNIFORM_BUFFER,
                                    0,
                                    size_uniforms_block,
                                    GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

            blockp = (GLfloat * 16 * 3).from_address(block)

            model_matrix = (GLfloat * 16)(*identityMatrix)
            model_matrix = scale(7.0)

            blockp[0] = m3dMultiply(view_matrix , model_matrix)


            blockp[1] = (GLfloat * 16)(*view_matrix)
            
            proj_matrix = (GLfloat * 16)(*identityMatrix)
            proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0);    
            
            blockp[2] = proj_matrix

            glUnmapBuffer(GL_UNIFORM_BUFFER)

            glUniform1f(uniforms[0].specular_power, 30.0)
            glUniform3fv(uniforms[0].specular_albedo, 1, (1.0,0.0, 0.0))

            myobject.render()



        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global MANY_OBJECTS
        
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
        elif key == b'm' or key == b'M':
            MANY_OBJECTS = not MANY_OBJECTS
            
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

    #glutInitContextVersion(4,1)
    #glutInitContextProfile(GLUT_CORE_PROFILE)    
    
    w1 = glutCreateWindow('OpenGL SuperBible - Blinn-Phong Shading')
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
