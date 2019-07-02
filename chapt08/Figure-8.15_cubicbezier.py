#!/usr/bin/python3

import sys
import time
import ctypes

fullscreen = True
sys.path.append("./shared")

#from sbmloader import SBMObject    # location of sbm file format loader
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

#myobject = SBMObject()
ktxobject = KTXObject()
overlay = OVERLAY_()

tess_program = GLuint(0)
draw_cp_program = GLuint(0)
patch_vao = GLuint(0)
patch_buffer = GLuint(0)
cage_indices = GLuint(0)

patch_data = [glm.vec3() for _ in range(16)] 

show_points=False
show_cage=False
wireframe=False
paused=False

class uniforms:
    class patch:
        mv_matrix=0
        proj_matrix=0
        mvp=0
    
    class control_point:
        draw_color=0
        mvp=0

uniform = uniforms()

def load_shaders():
    global uniform
    global tess_program
    global draw_cp_program
    
    if (tess_program):
        glDeleteProgram(tess_program)

    shaders = [GLuint(0) for _ in range(4)]

    shaders[0] = shader_load("cubicbezier.vs.glsl", GL_VERTEX_SHADER)
    shaders[1] = shader_load("cubicbezier.tcs.glsl", GL_TESS_CONTROL_SHADER)
    shaders[2] = shader_load("cubicbezier.tes.glsl", GL_TESS_EVALUATION_SHADER)
    shaders[3] = shader_load("cubicbezier.fs.glsl", GL_FRAGMENT_SHADER)

    tess_program = link_from_shaders(shaders, 4, True)

    uniform.patch.mv_matrix = glGetUniformLocation(tess_program, "mv_matrix")
    uniform.patch.proj_matrix = glGetUniformLocation(tess_program, "proj_matrix")
    uniform.patch.mvp = glGetUniformLocation(tess_program, "mvp")

    if (draw_cp_program):
        glDeleteProgram(draw_cp_program)

    shaders[0] = shader_load("draw-control-points.vs.glsl", GL_VERTEX_SHADER)
    shaders[1] = shader_load("draw-control-points.fs.glsl", GL_FRAGMENT_SHADER)

    draw_cp_program = link_from_shaders(shaders, 2, True)

    uniform.control_point.draw_color = glGetUniformLocation(draw_cp_program, "draw_color")
    uniform.control_point.mvp = glGetUniformLocation(draw_cp_program, "mvp")

class Scene:

    def __init__(self, width, height):
        global patch_vao
        global patch_buffer
        global cage_indices

        load_shaders()

        glGenVertexArrays(1, patch_vao)
        glBindVertexArray(patch_vao)

        glGenBuffers(1, patch_buffer)
        glBindBuffer(GL_ARRAY_BUFFER, patch_buffer)
        
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(ctypes.c_float)*3*16, None, GL_DYNAMIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)

        indices = [
            0, 1, 1, 2, 2, 3,
            4, 5, 5, 6, 6, 7,
            8, 9, 9, 10, 10, 11,
            12, 13, 13, 14, 14, 15,

            0, 4, 4, 8, 8, 12,
            1, 5, 5, 9, 9, 13,
            2, 6, 6, 10, 10, 14,
            3, 7, 7, 11, 11, 15
        ]
        
        ar = np.array(indices, dtype=np.uint16)
        
        glGenBuffers(1, cage_indices)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, cage_indices)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, ctypes.sizeof(ctypes.c_ushort)*len(indices), ar, GL_STATIC_DRAW)

        overlay.init(80, 50)
        overlay.clear()
        overlay.drawText("W: Toggle wireframe", 0, 0)
        overlay.drawText("C: Toggle control cage", 0, 1)
        overlay.drawText("X: Toggle control points", 0, 2)
        overlay.drawText("P: Pause", 0, 3)

    def display(self):
        
        currentTime = time.time()

        gray = [ 0.1, 0.1, 0.1, 0.0 ]
        one = 1.0

        last_time = 0.0
        total_time = 0.0

        if (not paused):
            total_time += (currentTime - last_time)
        last_time = currentTime

        t = total_time

        patch_initializer = [
            -1.0,  -1.0,  0.0,
            -0.33, -1.0,  0.0,
             0.33, -1.0,  0.0,
             1.0,  -1.0,  0.0,

            -1.0,  -0.33, 0.0,
            -0.33, -0.33, 0.0,
             0.33, -0.33, 0.0,
             1.0,  -0.33, 0.0,

            -1.0,   0.33, 0.0,
            -0.33,  0.33, 0.0,
             0.33,  0.33, 0.0,
             1.0,   0.33, 0.0,

            -1.0,   1.0,  0.0,
            -0.33,  1.0,  0.0,
             0.33,  1.0,  0.0,
             1.0,   1.0,  0.0,
        ]

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, gray)
        glClearBufferfv(GL_DEPTH, 0, one)

        glEnable(GL_DEPTH_TEST)

        p = glMapBufferRange(GL_ARRAY_BUFFER, 0, ctypes.sizeof(ctypes.c_float)*3*16, GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

        ppp = ((ctypes.c_float * 3) * 16).from_address(p) 

        for i in range(0, 16):

            fi = float(i) / 16.0
            
            ppp[i][0] = patch_initializer[i*3]
            ppp[i][1] = patch_initializer[(i*3)+1]
            
            ppp[i][2] = sin(t * (0.2 + fi * 0.3))
        
        glUnmapBuffer(GL_ARRAY_BUFFER)

        glBindVertexArray(patch_vao)

        glUseProgram(tess_program)

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 1.0, 1000.0)

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, 0.0, -4.0)
    
        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, t * m3dDegToRad(10.0), 1.0, 0.0, 0.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, t * m3dDegToRad(17.0), 0.0, 1.0, 0.0)
        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(T, m3dMultiply(RX, RY))
        
        glUniformMatrix4fv(uniform.patch.mv_matrix, 1, GL_FALSE, mv_matrix)
        glUniformMatrix4fv(uniform.patch.proj_matrix, 1, GL_FALSE, proj_matrix)
        glUniformMatrix4fv(uniform.patch.mvp, 1, GL_FALSE, m3dMultiply(proj_matrix , mv_matrix))

        if (wireframe):
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
       
        glPatchParameteri(GL_PATCH_VERTICES, 16)
        glDrawArrays(GL_PATCHES, 0, 16)

        glUseProgram(draw_cp_program)
        glUniformMatrix4fv(uniform.control_point.mvp, 1, GL_FALSE, m3dMultiply(proj_matrix , mv_matrix))

        if (show_points):
            glPointSize(9.0)
            glUniform4fv(uniform.control_point.draw_color, 1, [0.2, 0.7, 0.9, 1.0])
            glDrawArrays(GL_POINTS, 0, 16)
        
        if (show_cage):
            glUniform4fv(uniform.control_point.draw_color, 1, [0.7, 0.9, 0.2, 1.0])
            glDrawElements(GL_LINES, 48, GL_UNSIGNED_SHORT, None)
        
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        overlay.draw()

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
        elif key == b'c' or key == b'C':
            show_cage = not show_cage
        elif key == b'x' or key == b'X':
            show_points = not show_points
        elif key == b'w' or key == b'W':
            wireframe = not wireframe
        elif key == b'p' or key == b'P':
            paused = not paused
        elif key == b'r' or key == b'R':
            load_shaders()

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
    w1 = glutCreateWindow('OpenGL SuperBible - Cubic Bezier Patch')
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
