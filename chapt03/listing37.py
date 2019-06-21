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

fullscreen = True

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


vs_source = '''
#version 410 core                                                 

void main(void)                                                   
{                                                                 
    const vec4 vertices[] = vec4[](vec4( 0.25, -0.25, 0.5, 1.0),  
                                   vec4(-0.25, -0.25, 0.5, 1.0),  
                                   vec4( 0.25,  0.25, 0.5, 1.0)); 

    gl_Position = vertices[gl_VertexID];                          
}                                                                 
'''


tcs_source = '''
#version 410 core                                                                 

layout (vertices = 3) out;                                                        

void main(void)                                                                   
{                                                                                 
    if (gl_InvocationID == 0)                                                     
    {                                                                             
        gl_TessLevelInner[0] = 5.0;                                               
        gl_TessLevelOuter[0] = 5.0;                                               
        gl_TessLevelOuter[1] = 5.0;                                               
        gl_TessLevelOuter[2] = 5.0;                                               
    }                                                                             
    gl_out[gl_InvocationID].gl_Position = gl_in[gl_InvocationID].gl_Position;     
}                                                                                 
'''


tes_source = '''
#version 410 core                                                                 

layout (triangles, equal_spacing, cw) in;                                         

void main(void)                                                                   
{                                                                                 
    gl_Position = (gl_TessCoord.x * gl_in[0].gl_Position) +                       
                  (gl_TessCoord.y * gl_in[1].gl_Position) +                       
                  (gl_TessCoord.z * gl_in[2].gl_Position);                        
}                                                                                 
'''


fs_source = '''
#version 410 core                                                 

out vec4 color;                                                   

void main(void)                                                   
{                                                                 
    color = vec4(0.0, 0.8, 1.0, 1.0);                             
}                                                                 
'''


def compile_program():

    program = glCreateProgram()

    vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, vs_source);
    glCompileShader(vs);

    tcs = glCreateShader(GL_TESS_CONTROL_SHADER);
    glShaderSource(tcs, tcs_source);
    glCompileShader(tcs);

    tes = glCreateShader(GL_TESS_EVALUATION_SHADER);
    glShaderSource(tes, tes_source);
    glCompileShader(tes);

    fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, fs_source);
    glCompileShader(fs);

    glAttachShader(program, vs);
    glAttachShader(program, tcs);
    glAttachShader(program, tes);
    glAttachShader(program, fs);

    glLinkProgram(program);
    
    vao = GLuint(0)
    glGenVertexArrays(1, vao);
    glBindVertexArray(vao);

    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE);

    return program





class Scene:

    def __init__(self):
        pass
        
    def display(self):

        green = [ 0.0, 0.25, 0.0, 1.0 ]
        glClearBufferfv(GL_COLOR, 0, green)

        glUseProgram(compile_program())
        glDrawArrays(GL_PATCHES, 0, 3)
        
        glutSwapBuffers()

    def reshape(self, width, height):
        pass

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

if __name__ == '__main__':
    start = time.time()

    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    
    w1 = glutCreateWindow('Listing 3.7 and Listing 3.8')
    glutInitWindowPosition(int((1360/2)-(512/2)), int((768/2)-(512/2)))

    fullscreen = False
    #glutFullScreen()
    
    scene = Scene()
    glutReshapeFunc(scene.reshape)
    glutDisplayFunc(scene.display)
    glutKeyboardFunc(scene.keyboard)

    glutIdleFunc(scene.display)

    scene.init()
    
    glutMainLoop()

