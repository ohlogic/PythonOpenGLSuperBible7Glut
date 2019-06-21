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

sys.path.append("../shared")

from math3d import m3dDegToRad, m3dRotationMatrix44, M3DMatrix44f, m3dLoadIdentity44, \
                                            m3dTranslateMatrix44, m3dScaleMatrix44, \
                                            m3dMatrixMultiply44, m3dTransposeMatrix44, \
                                            m3dRadToDeg

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

def rotation_matrix(axis, theta):
    """
    Return the rotation matrix associated with counterclockwise rotation about
    the given axis by theta radians.
    """
    axis = np.asarray(axis)
    axis = axis / math.sqrt(np.dot(axis, axis))
    a = math.cos(theta / 2.0)
    b, c, d = -axis * math.sin(theta / 2.0)
    aa, bb, cc, dd = a * a, b * b, c * c, d * d
    bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
    return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                     [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                     [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])


identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

mv_location = (GLfloat * 16)(*identityMatrix)
proj_location = (GLfloat * 16)(*identityMatrix)
proj_matrix = (GLfloat * 16)(*identityMatrix)


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

    def __init__(self):
        pass

    def display(self):
        global mv_location
        global proj_location
        global proj_matrix

        currentTime = time.time()

        green = [ 0.0, 0.25, 0.0, 1.0 ]
        one = 1.0;

        glViewport(0, 0, int((1360/2)-(512/2)), int((768/2)-(512/2)))


        glClearBufferfv(GL_COLOR, 0, green);
        glClearBufferfv(GL_DEPTH, 0, one);        

        glUseProgram(compile_program(vs_source, fs_source))

        #proj_matrix = m3dOrtho(-1, 1, -1, 1, -10, 10)
        #proj_matrix = m3dPerspective(50.0*math.pi/180.0, 512/512, 0.1, 1000.0)
        glUniformMatrix4fv(proj_location, 1, GL_FALSE, proj_matrix);


        # supposed to render a spinny cube
        f = currentTime * 0.3;

        mv_matrix = (GLfloat * 16)(*identityMatrix)
        
        # next statements not exactly right
        m3dTranslateMatrix44(mv_matrix, 0.0, 0.0, -4.0)
        m3dTranslateMatrix44(mv_matrix, sin(2.1 * f) * 0.5, 
                                        cos(1.7 * f) * 0.5, 
                                        sin(1.3 * f) * cos(1.5 * f) * 2.0)
        
        m3dRotationMatrix44(mv_matrix, currentTime * m3dRadToDeg(45.0), 0.0, 1.0, 0.0)
        m3dRotationMatrix44(mv_matrix, currentTime * m3dRadToDeg(81.0), 1.0, 0.0, 0.0)
        
        # supposed to be something like the following, though c++ code
        # vmath::mat4 mv_matrix = vmath::translate(0.0f, 0.0f, -4.0f) *
                                # vmath::translate(sinf(2.1f * f) * 0.5f,
                                                    # cosf(1.7f * f) * 0.5f,
                                                    # sinf(1.3f * f) * cosf(1.5f * f) * 2.0f) *
                                # vmath::rotate((float)currentTime * 45.0f, 0.0f, 1.0f, 0.0f) *
                                # vmath::rotate((float)currentTime * 81.0f, 1.0f, 0.0f, 0.0f);
                                

        glUniformMatrix4fv(mv_location, 1, GL_FALSE, mv_matrix)
        

        glDrawArrays(GL_TRIANGLES, 0, 36)
        # ///////////////////////////////////////
        
        glutSwapBuffers()

    def reshape(self, width, height):
        global proj_matrix
        aspect = float(width / height);
        if proj_matrix == None:
            #proj_matrix = gluPerspective(50.0, aspect, 0.1, 1000.0);
            proj_matrix = m3dPerspective(50.0, aspect, 0.1, 1000.0);
            
            
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
        time.sleep(1/20.0)
     
if __name__ == '__main__':
    start = time.time()

    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)

    w1 = glutCreateWindow('OpenGL SuperBible - Spinny Cube')
    glutInitWindowPosition(int((1360/2)-(512/2)), int((768/2)-(512/2)))

    fullscreen = False
    #glutFullScreen()

    scene = Scene()
    glutReshapeFunc(scene.reshape)
    glutDisplayFunc(scene.display)
    glutKeyboardFunc(scene.keyboard)

    #glutIdleFunc(scene.display)
    glutTimerFunc( int(1/60), scene.timer, 0)
    
    scene.init()

    glutMainLoop()