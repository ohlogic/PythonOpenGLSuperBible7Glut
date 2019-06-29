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
from math import cos, sin 
identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]


render_program = GLuint(0)

myobject = SBMObject()

indirect_draw_buffer = GLuint(0)
draw_index_buffer = GLuint(0)

class uniforms():
    time = GLint(0)
    view_matrix  = GLint(0)
    proj_matrix = GLint(0)
    viewproj_matrix  = GLint(0)

uniform = uniforms()


mode = 1
MODE_MULTIDRAW = 1
MODE_SEPARATE_DRAWS = 2


paused = False
vsync=True

NUM_DRAWS           = 50000


class DrawArraysIndirectCommand:
    count = GLuint(0)
    primCount = GLuint(0)
    first = GLuint(0)
    baseInstance = GLuint(0)




def shader_load(filename, shader_type):
    
    result = GLuint(0)
    
    with open ( filename, "rb") as data:
        
        result = glCreateShader(shader_type)
        
        glShaderSource(result, data.read() )
        
    glCompileShader(result)
    
    return result


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



def load_shaders():
    
    global render_program
    global uniform
    
    shaders = [GLuint(0), GLuint(0)]

    shaders[0] = shader_load("render.vs.glsl", GL_VERTEX_SHADER)
    shaders[1] = shader_load("render.fs.glsl", GL_FRAGMENT_SHADER)

    if (render_program):
        glDeleteProgram(render_program)

    render_program = link_from_shaders(shaders, 2, True)

    uniform.time            = glGetUniformLocation(render_program, "time")
    uniform.view_matrix     = glGetUniformLocation(render_program, "view_matrix")
    uniform.proj_matrix     = glGetUniformLocation(render_program, "proj_matrix")
    uniform.viewproj_matrix = glGetUniformLocation(render_program, "viewproj_matrix")




class Scene:

    def __init__(self, width, height):
    
        global myobject
        global indirect_draw_buffer
        global draw_index_buffer
        
        i=0

        load_shaders()


        
        myobject.load("asteroids.sbm")

        sizeOfDrawIndCmd = ctypes.sizeof(GLuint*4)

        glGenBuffers(1, indirect_draw_buffer)
        glBindBuffer(GL_DRAW_INDIRECT_BUFFER, indirect_draw_buffer)
        glBufferData(GL_DRAW_INDIRECT_BUFFER,
                        NUM_DRAWS * sizeOfDrawIndCmd,
                        None,
                        GL_STATIC_DRAW)


        cmd_memory = glMapBufferRange(GL_DRAW_INDIRECT_BUFFER,
                                0,
                                NUM_DRAWS * sizeOfDrawIndCmd,
                                GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)


        cmd_buffer = ((GLuint * 4) * NUM_DRAWS).from_address(cmd_memory) 

        for i in range(0, NUM_DRAWS):
            first, count = myobject.get_sub_object_info(i % myobject.get_sub_object_count())
            cmd_buffer[i][0] = count
            cmd_buffer[i][1] = 1
            cmd_buffer[i][2] = first
            cmd_buffer[i][3] = i

        glUnmapBuffer(GL_DRAW_INDIRECT_BUFFER)

        glBindVertexArray(myobject.get_vao())

        glGenBuffers(1, draw_index_buffer)
        glBindBuffer(GL_ARRAY_BUFFER, draw_index_buffer)
        glBufferData(GL_ARRAY_BUFFER,
                        NUM_DRAWS * ctypes.sizeof(GLuint),
                        None,
                        GL_STATIC_DRAW)

        draw_index = glMapBufferRange(GL_ARRAY_BUFFER,
                                        0,
                                        NUM_DRAWS * ctypes.sizeof(GLuint),
                                        GL_MAP_WRITE_BIT |
                                        GL_MAP_INVALIDATE_BUFFER_BIT)


        int_array = (GLuint * NUM_DRAWS).from_address(draw_index) 

        for i in range(0, NUM_DRAWS):
            int_array[i] = i

        glUnmapBuffer(GL_ARRAY_BUFFER)

        glVertexAttribIPointer(10, 1, GL_UNSIGNED_INT, 0, None)
        glVertexAttribDivisor(10, 1)
        glEnableVertexAttribArray(10)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

        glEnable(GL_CULL_FACE)




    def display(self):
        
        global myobject
        
        currentTime = time.time()

        j=0
        one = 1.0;
        black = [ 0.0, 0.0, 0.0, 0.0 ]

            
        last_time = 0.0;
        total_time = 0.0;

        if (paused == False):
            total_time += (currentTime - last_time)
        last_time = currentTime

        t = float(total_time)
        i = int(total_time * 3.0)

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_DEPTH, 0, one)

        view_matrix = (GLfloat * 16)(*identityMatrix)
        view_matrix = m3dLookAt([100.0 * cos(t * 0.023), 100.0 * cos(t * 0.023), 300.0 * sin(t * 0.037) - 600.0],
                                [0.0, 0.0, 260.0], 
                                normalize([0.1 - cos(t * 0.1) * 0.3, 1.0, 0.0]))

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 1.0, 2000.0)

        glUseProgram(render_program)

        glUniform1f(uniform.time, t)
        glUniformMatrix4fv(uniform.view_matrix, 1, GL_FALSE, view_matrix)
        glUniformMatrix4fv(uniform.proj_matrix, 1, GL_FALSE, proj_matrix)
        glUniformMatrix4fv(uniform.viewproj_matrix, 1, GL_FALSE, m3dMultiply(proj_matrix , view_matrix))

        glBindVertexArray(myobject.get_vao());


        if (mode == MODE_MULTIDRAW):

            glMultiDrawArraysIndirect(GL_TRIANGLES, None, NUM_DRAWS, 0);
        
        elif (mode == MODE_SEPARATE_DRAWS):
        
            for j in range(0, NUM_DRAWS):
            
                first, count = myobject.get_sub_object_info(j % myobject.get_sub_object_count())
                glDrawArraysInstancedBaseInstance(GL_TRIANGLES,
                                                  first,
                                                  count,
                                                  1, j)

        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global paused
        global mode
        global vsync
        
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

        elif key == b'p' or key == b'P': #fullscreen toggle
            paused = not paused   # a toggle technique

        elif key == b'v' or key == b'V': #fullscreen toggle
            # if (vsync==1):
                # toggle_vsync()
                # vsync=0
            # else:
                # toggle_vsync()
                # vsync=1
            pass
            
        elif key == b'd' or key == b'D': #fullscreen toggle
                
                mode += 1
                if (mode  > 2):
                    mode = 1


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

    w1 = glutCreateWindow('OpenGL SuperBible - Asteroids')
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
