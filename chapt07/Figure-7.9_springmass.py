#!/usr/bin/python3

import sys
import time
import ctypes

fullscreen = True

sys.path.append("./shared")

from sbmloader import SBMObject    # location of sbm file format loader

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

from array import array
from enum import Enum

import numpy as np 

import glm


from math import cos, sin 
identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

render_program = GLuint(0)

myobject = SBMObject()

POSITION_A = 0
POSITION_B = 1
VELOCITY_A = 2
VELOCITY_B = 3
CONNECTION = 4

POINTS_X            = 50
POINTS_Y            = 50
POINTS_TOTAL        = POINTS_X * POINTS_Y
CONNECTIONS_TOTAL = (POINTS_X - 1) * POINTS_Y + (POINTS_Y - 1) * POINTS_X


m_vao = [GLuint(0) for _ in range(2)]
m_vbo = [GLuint(0) for _ in range(5)]

m_index_buffer = GLuint(0)
m_pos_tbo = [GLuint(0), GLuint(0)]
m_update_program = GLuint(0)
m_render_program = GLuint(0)
m_C_loc = GLuint(0)
m_iteration_index = 0

draw_points = True
draw_lines = True
iterations_per_frame = 16


def shader_load(filename, shader_type):
    
    result = GLuint(0)
    
    with open ( filename, "rb") as data:
        
        result = glCreateShader(shader_type)
        
        glShaderSource(result, data.read() )
        
    glCompileShader(result)
    
    return result
    
    
def load_shaders():
    global m_update_program
    global m_render_program
    
    vs = GLuint(0)
    fs = GLuint(0)
    buffer = ''

    vs = shader_load("update.vs.glsl", GL_VERTEX_SHADER)

    if (m_update_program):
        glDeleteProgram(m_update_program)
        
    m_update_program = glCreateProgram()
    glAttachShader(m_update_program, vs)


    # static const char * tf_varyings[] = 
    # {
        # "tf_position_mass",
        # "tf_velocity"
    # }
    

    # tricky to convert string array to string pointer

    tf_varyings = ["tf_position_mass", "tf_velocity"]

    # Prepare ctypes data containing the list tf_varyings of strings
    array_type = ctypes.c_char_p * len(tf_varyings)
    buff = array_type()
    for i, e in enumerate(tf_varyings):
        buff[i] = e.encode()
                                                                            #       ctypes.c_char
    tf_varyings_chrpp = ctypes.cast(ctypes.pointer(buff), ctypes.POINTER(ctypes.POINTER(GLchar)))


    glTransformFeedbackVaryings(m_update_program, 2, tf_varyings_chrpp, GL_SEPARATE_ATTRIBS)

    glLinkProgram(m_update_program)

    glGetShaderInfoLog(vs)
    glGetProgramInfoLog(m_update_program)

    glDeleteShader(vs)

    vs = shader_load("render.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("render.fs.glsl", GL_FRAGMENT_SHADER)

    if (m_render_program):
        glDeleteProgram(m_render_program)
    m_render_program = glCreateProgram()
    glAttachShader(m_render_program, vs)
    glAttachShader(m_render_program, fs)
    
    glLinkProgram(m_render_program)



class Scene:

    def __init__(self, width, height):
        global m_vao
        global m_vbo
        
        i = 0
        j = 0

        load_shaders()


        initial_positions = [glm.vec4() for _ in range(POINTS_TOTAL)]
        initial_velocities = [glm.vec3() for _ in range(POINTS_TOTAL)]
        connection_vectors = [glm.ivec3() for _ in range(POINTS_TOTAL)]
        
        
        n=0
        for j in range(0, POINTS_Y):
            fj = float(j) / float(POINTS_Y)
            
            for i in range(0, POINTS_X):
            
                fi = float(i) / float(POINTS_X)

                initial_positions[n] = glm.vec4((fi - 0.5) * float(POINTS_X), (fj - 0.5) * float(POINTS_Y), 0.6 * sin(fi) * cos(fj), 1.0)
                initial_velocities[n] = glm.vec3(0.0)
                connection_vectors[n] = glm.ivec4(-1)

                if (j != (POINTS_Y - 1)):
                
                    if (i != 0):
                        connection_vectors[n][0] = n - 1

                    if (j != 0):
                        connection_vectors[n][1] = n - POINTS_X

                    if (i != (POINTS_X - 1)):
                        connection_vectors[n][2] = n + 1

                    if (j != (POINTS_Y - 1)):
                        connection_vectors[n][3] = n + POINTS_X
                n+=1


        for i in range(0, 2):
            glGenVertexArrays(1, m_vao[i])
        
        for i in range(0, 5):
            glGenBuffers(i+1, m_vbo[i])

        for i in range(0, 2):

            glBindVertexArray(m_vao[i])

            glBindBuffer(GL_ARRAY_BUFFER, m_vbo[POSITION_A + i])


            # POSITION_A
            glBindBuffer(GL_ARRAY_BUFFER, m_vbo[POSITION_A + i])
            
            ar_position = np.empty([POINTS_TOTAL, 4], dtype='float32')
            for j, e in enumerate(initial_positions):
                ar_position[j] = e

            glBufferData(GL_ARRAY_BUFFER, POINTS_TOTAL * glm.sizeof(glm.vec4()), ar_position, GL_DYNAMIC_COPY)
            glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(0)
            
            # VELOCITY_A
            glBindBuffer(GL_ARRAY_BUFFER, m_vbo[VELOCITY_A + i])

            ar_velocities = np.empty([POINTS_TOTAL, 3], dtype='float32')
            for j, e in enumerate(initial_velocities):
                ar_velocities[j] = e

            glBufferData(GL_ARRAY_BUFFER, POINTS_TOTAL * glm.sizeof(glm.vec3()), ar_velocities, GL_DYNAMIC_COPY)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(1)

            # CONNECTION
            glBindBuffer(GL_ARRAY_BUFFER, m_vbo[CONNECTION])
            
            ar_connection = np.empty([POINTS_TOTAL, 4], dtype='uint32')
            for j, e in enumerate(connection_vectors):
                ar_connection[j] = e
            
            glBufferData(GL_ARRAY_BUFFER, POINTS_TOTAL * glm.sizeof(glm.ivec4()), ar_connection, GL_STATIC_DRAW)
            glVertexAttribIPointer(2, 4, GL_INT, 0, None)
            glEnableVertexAttribArray(2)

        glGenTextures(2, m_pos_tbo)
        glBindTexture(GL_TEXTURE_BUFFER, m_pos_tbo[0])
        glTexBuffer(GL_TEXTURE_BUFFER, GL_RGBA32F, m_vbo[POSITION_A])
        glBindTexture(GL_TEXTURE_BUFFER, m_pos_tbo[1])
        glTexBuffer(GL_TEXTURE_BUFFER, GL_RGBA32F, m_vbo[POSITION_B])

        lines = (POINTS_X - 1) * POINTS_Y + (POINTS_Y - 1) * POINTS_X

        glGenBuffers(1, m_index_buffer)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, m_index_buffer)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, lines * 2 * ctypes.sizeof(ctypes.c_int), None, GL_STATIC_DRAW)

        e = glMapBufferRange(GL_ELEMENT_ARRAY_BUFFER, 0, lines * 2 * ctypes.sizeof(ctypes.c_int), GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

        int_array = (ctypes.c_int * (4 * lines * 2)).from_address(e) 
        n = 0
        for j in range(0, POINTS_Y):
            for i in range(0, POINTS_X - 1):
                int_array[n] = i + j * POINTS_X
                n+=1

                int_array[n] = 1 + i + j * POINTS_X
                n+=1

        for i in range(0, POINTS_X):

            for j in range(0, POINTS_Y - 1):
                int_array[n] = i + j * POINTS_X
                n+=1

                int_array[n] = POINTS_X + i + j * POINTS_X
                n+=1


        glUnmapBuffer(GL_ELEMENT_ARRAY_BUFFER)
        
        
    def display(self):
        global m_iteration_index

        glUseProgram(m_update_program)

        glEnable(GL_RASTERIZER_DISCARD)


        for i in range( iterations_per_frame, 0, -1):

            glBindVertexArray(m_vao[m_iteration_index & 1])
            glBindTexture(GL_TEXTURE_BUFFER, m_pos_tbo[m_iteration_index & 1])
            m_iteration_index +=1
            glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, m_vbo[POSITION_A + (m_iteration_index & 1)])
            glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 1, m_vbo[VELOCITY_A + (m_iteration_index & 1)])

            glBeginTransformFeedback(GL_POINTS)
            glDrawArrays(GL_POINTS, 0, POINTS_TOTAL)
            glEndTransformFeedback()

        glDisable(GL_RASTERIZER_DISCARD)

        black = [ 0.0, 0.0, 0.0, 0.0 ]

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, black)

        glUseProgram(m_render_program)

        if (draw_points):
            glPointSize(4.0)
            glDrawArrays(GL_POINTS, 0, POINTS_TOTAL)

        if (draw_lines):
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, m_index_buffer)
            glDrawElements(GL_LINES, CONNECTIONS_TOTAL * 2, GL_UNSIGNED_INT, None)

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

    w1 = glutCreateWindow('OpenGL SuperBible - Spring-Mass Simulator')
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
