#!/usr/bin/python3

# Copyright © 2012-2015 Graham Sellers

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice (including the next
# paragraph) shall be included in all copies or substantial portions of the
# Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


import sys

import time
import math
fullscreen = True

# sys.path.append("../shared")

# from math3d import m3dDegToRad, m3dRotationMatrix44, M3DMatrix44f, m3dLoadIdentity44, \
                                            # m3dTranslateMatrix44, m3dScaleMatrix44, \
                                            # m3dMatrixMultiply44, m3dTransposeMatrix44, \
                                            # m3dRadToDeg

import numpy.matlib 
import numpy as np 

try:
    from OpenGL.GLUT import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.raw.GL.ARB.vertex_array_object import glGenVertexArrays, \
                                                  glBindVertexArray
except:
    print ('''
    ERROR: PyOpenGL not installed properly.
        ''')
    sys.exit()

from math import cos, sin
from array import array

M3D_PI = 3.14159265358979323846
M3D_PI_DIV_180 = M3D_PI / 180.0
M3D_INV_PI_DIV_180 = 57.2957795130823229

# Translate matrix. Only 4x4 matrices supported
def m3dTranslateMatrix44(m, x, y, z):
    m[12] += x
    m[13] += y
    m[14] += z

def m3dDegToRad(num):
    return (num * M3D_PI_DIV_180)

def m3dRadToDeg(num):
    return (num * M3D_INV_PI_DIV_180)

def m3dOrtho(l, r, t, b, n, f):
    return (GLfloat * 16)(
        2/(r-l),      0,            0,            0,
        0,            2/(t-b),      0,            0,
        0,            0,            -2/(f-n),     0,
        -(r+l)/(r-l), -(t+b)/(t-b), -(f+n)/(f-n), 1)

def m3dPerspective(fov_y, aspect, n, f):
    a = aspect
    ta = math.tan( fov_y / 2 )
    return (GLfloat * 16)(
        1/(ta*a),  0,     0,              0,
        0,         1/ta,  0,              0,
        0,         0,    -(f+n)/(f-n),   -1,
        0,         0,    -2*f*n/(f-n),    0)

# Creates a 4x4 rotation matrix, takes radians NOT degrees
def m3dRotationMatrix44(m, angle, x, y, z):
    s = sin(angle)
    c = cos(angle)
    mag = float((x * x + y * y + z * z) ** 0.5)
    
    if mag == 0.0:
        m3dLoadIdentity(m)
        return
    
    x /= mag
    y /= mag
    z /= mag
    
    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    yz = y * z
    zx = z * x
    xs = x * s
    ys = y * s
    zs = z * s
    one_c = 1.0 - c
    
    m[0] = (one_c * xx) + c
    m[1] = (one_c * xy) - zs
    m[2] = (one_c * zx) + ys
    m[3] = 0.0
    
    m[4] = (one_c * xy) + zs
    m[5] = (one_c * yy) + c
    m[6] = (one_c * yz) - xs
    m[7] = 0.0
    
    m[8] = (one_c * zx) - ys
    m[9] = (one_c * yz) + xs
    m[10] = (one_c * zz) + c
    m[11]  = 0.0
    
    m[12] = 0.0
    m[13] = 0.0
    m[14] = 0.0
    m[15] = 1.0

def m3dMultiply(A, B):
    C = (GLfloat * 16)(*identityMatrix)
    for k in range(0, 4):
        for j in range(0, 4):
            C[k*4+j] = A[0*4+j] * B[k*4+0] + A[1*4+j] * B[k*4+1] + \
                       A[2*4+j] * B[k*4+2] + A[3*4+j] * B[k*4+3]
    return C

identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

mv_location = (GLfloat * 16)(*identityMatrix)
proj_location = (GLfloat * 16)(*identityMatrix)
proj_matrix = (GLfloat * 16)(*identityMatrix)

many_cubes = False

# Vertex program
vs_source = '''
    #version 410 core                                                  

    in vec4 position;                                                  

    out VS_OUT                                                         
    {                                                                  
        vec4 color;                                                    
    } vs_out;                                                          

    uniform mat4 mv_matrix;                                            
    uniform mat4 proj_matrix;                                          

    void main(void)                                                    
    {                                                                  
        gl_Position = proj_matrix * mv_matrix * position;              
        vs_out.color = position * 2.0 + vec4(0.5, 0.5, 0.5, 0.0);      
    }                                                                  
'''

# Fragment program
fs_source = '''
    #version 410 core                                                  

    out vec4 color;                                                    

    in VS_OUT                                                          
    {                                                                  
        vec4 color;                                                    
    } fs_in;                                                           

    void main(void)                                                    
    {                                                                  
        color = fs_in.color;                                           
    }                                                                  
'''


def compile_program(vertex_source, fragment_source):

    global mv_location
    global proj_location

    vertex_shader = None
    fragment_shader = None

    if vertex_source:

        vertex_shader = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vertex_shader, vertex_source)
        glCompileShader(vertex_shader)

        if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
                    raise Exception('failed to compile shader "%s":\n%s' % 
                    ('vertex_shader', glGetShaderInfoLog(vertex_shader)))

    if fragment_source:

        fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fragment_shader, fragment_source)
        glCompileShader(fragment_shader)

        if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
                    raise Exception('failed to compile shader "%s":\n%s' % 
                    ('fragment_shader', glGetShaderInfoLog(fragment_shader)))

    program = glCreateProgram()

    glAttachShader(program, vertex_shader)
    glAttachShader(program, fragment_shader)

    glLinkProgram(program)

    mv_location = glGetUniformLocation(program, "mv_matrix");
    proj_location = glGetUniformLocation(program, "proj_matrix");

    vao = GLuint(0)
    glGenVertexArrays(1, vao);
    glBindVertexArray(vao);

    vertex_positions = [
        -0.25,  0.25, -0.25,
        -0.25, -0.25, -0.25,
         0.25, -0.25, -0.25,

         0.25, -0.25, -0.25,
         0.25,  0.25, -0.25,
        -0.25,  0.25, -0.25,

         0.25, -0.25, -0.25,
         0.25, -0.25,  0.25,
         0.25,  0.25, -0.25,

         0.25, -0.25,  0.25,
         0.25,  0.25,  0.25,
         0.25,  0.25, -0.25,

         0.25, -0.25,  0.25,
        -0.25, -0.25,  0.25,
         0.25,  0.25,  0.25,

        -0.25, -0.25,  0.25,
        -0.25,  0.25,  0.25,
         0.25,  0.25,  0.25,

        -0.25, -0.25,  0.25,
        -0.25, -0.25, -0.25,
        -0.25,  0.25,  0.25,

        -0.25, -0.25, -0.25,
        -0.25,  0.25, -0.25,
        -0.25,  0.25,  0.25,

        -0.25, -0.25,  0.25,
         0.25, -0.25,  0.25,
         0.25, -0.25, -0.25,

         0.25, -0.25, -0.25,
        -0.25, -0.25, -0.25,
        -0.25, -0.25,  0.25,

        -0.25,  0.25, -0.25,
         0.25,  0.25, -0.25,
         0.25,  0.25,  0.25,

         0.25,  0.25,  0.25,
        -0.25,  0.25,  0.25,
        -0.25,  0.25, -0.25 ]

    buffer = GLuint(0)
    glGenBuffers(1, buffer);
    glBindBuffer(GL_ARRAY_BUFFER, buffer);

    #ar=numpy.array(vertex_positions, dtype='float32')
    ar=array("f",vertex_positions)
    glBufferData(GL_ARRAY_BUFFER, ar.tostring(), GL_STATIC_DRAW)

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None);
    glEnableVertexAttribArray(0);

    glEnable(GL_CULL_FACE);
    glFrontFace(GL_CW);

    glEnable(GL_DEPTH_TEST);
    glDepthFunc(GL_LEQUAL);

    return program


class Scene:

    def __init__(self, width, height):
    
        self.width = width
        self.height = height

    def display(self):
        global mv_location
        global proj_location
        global proj_matrix
        global many_cubes
        
        currentTime = time.time()

        green = [ 0.0, 0.25, 0.0, 1.0 ]
        one = 1.0;

        glViewport(0, 0, int((1360/2)-(512/2)), int((768/2)-(512/2)))


        glClearBufferfv(GL_COLOR, 0, green);
        glClearBufferfv(GL_DEPTH, 0, one);        

        glUseProgram(compile_program(vs_source, fs_source))

        #proj_matrix = m3dOrtho(-1, 1, -1, 1, -10, 10)
        #proj_matrix = m3dPerspective(50.0*math.pi/180.0, 512/512, 0.1, 1000.0)
        #proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0);

        glUniformMatrix4fv(proj_location, 1, GL_FALSE, proj_matrix)
        
        if (many_cubes == True):
        
            for i in range(0, 24):
                f = i + currentTime * 0.3;
                
                mv_matrix = (GLfloat * 16)(*identityMatrix)
                
                T = (GLfloat * 16)(*identityMatrix)
                m3dTranslateMatrix44(T, 0, 0, -4)

                W = (GLfloat * 16)(*identityMatrix)
                m3dTranslateMatrix44(W, sin(2.1 * f) * 0.5, cos(1.7 * f) * 0.5, sin(1.3 * f) * cos(1.5 * f) * 2.0)

                RX = (GLfloat * 16)(*identityMatrix)
                m3dRotationMatrix44(RX, currentTime * m3dDegToRad(45.0), 0.0, 1.0, 0.0)

                RY = (GLfloat * 16)(*identityMatrix)
                m3dRotationMatrix44(RY, currentTime * m3dDegToRad(81.0), 1.0, 0.0, 0.0)


                mv_matrix = m3dMultiply(W, m3dMultiply(T, m3dMultiply(RY, RX)))
                
                # or can multiply with numpy
                #R = np.matmul(np.array(W).reshape(4,4) , np.matmul(np.array(RX).reshape(4,4), np.array(RY).reshape(4,4)))
                #mv_matrix = np.matmul(R, np.array(T).reshape(4,4))

                glUniformMatrix4fv(mv_location, 1, GL_FALSE, mv_matrix)
            
                glDrawArrays(GL_TRIANGLES, 0, 36)
                
        else:
            f = currentTime * 0.3;

            mv_matrix = (GLfloat * 16)(*identityMatrix)
            
            T = (GLfloat * 16)(*identityMatrix)
            m3dTranslateMatrix44(T, 0, 0, -4)

            W = (GLfloat * 16)(*identityMatrix)
            m3dTranslateMatrix44(W, sin(2.1 * f) * 0.5, cos(1.7 * f) * 0.5, sin(1.3 * f) * cos(1.5 * f) * 2.0)

            RX = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RX, currentTime * m3dDegToRad(45.0), 0.0, 1.0, 0.0)

            RY = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RY, currentTime * m3dDegToRad(81.0), 1.0, 0.0, 0.0)

            mv_matrix = m3dMultiply(W, m3dMultiply(T, m3dMultiply(RY, RX)))
            
            # or can multiply with numpy
            #R = np.matmul(np.array(W).reshape(4,4) , np.matmul(np.array(RX).reshape(4,4), np.array(RY).reshape(4,4)))
            #mv_matrix = np.matmul(R, np.array(T).reshape(4,4))

            glUniformMatrix4fv(mv_location, 1, GL_FALSE, mv_matrix)
        
            glDrawArrays(GL_TRIANGLES, 0, 36)

        glutSwapBuffers()

    def reshape(self, width, height):
        global proj_matrix
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0);
        
        self.width = width
        self.height = height
            
    def keyboard(self, key, x, y ):
        global fullscreen
        global many_cubes
        
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

            if (many_cubes == True):
                many_cubes = False
            else:
                many_cubes = True
                
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

    w1 = glutCreateWindow('OpenGL SuperBible - Spinny Cube')
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