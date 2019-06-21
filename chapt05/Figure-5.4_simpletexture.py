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


# Vertex program
vs_source = '''
    #version 420 core                                                              
                                                                                   
    void main(void)                                                                
    {                                                                              
        const vec4 vertices[] = vec4[](vec4( 0.75, -0.75, 0.5, 1.0),               
                                       vec4(-0.75, -0.75, 0.5, 1.0),               
                                       vec4( 0.75,  0.75, 0.5, 1.0));              
                                                                                   
        gl_Position = vertices[gl_VertexID];                                       
    }                                                                              
'''

# Fragment program
fs_source = '''
    #version 430 core                                                              
                                                                                   
    uniform sampler2D s;                                                           
                                                                                   
    out vec4 color;                                                                
                                                                                   
    void main(void)                                                                
    {                                                                              
        color = texture(s, gl_FragCoord.xy / textureSize(s, 0));                   
    }                                                                              
'''

def generate_texture(data, width, height):

    aa = range(0, height)
    for n in aa:
        bb = range (0, width)
        for t in bb:
            data[(n * width + t) * 4 + 0] = float(((t & n) & 0xFF) / 255.0);
            data[(n * width + t) * 4 + 1] = float(((t | n) & 0xFF) / 255.0);
            data[(n * width + t) * 4 + 2] = float(((t ^ n) & 0xFF) / 255.0);
            data[(n * width + t) * 4 + 3] = 1.0;
        
            
            
def compile_program(vertex_source, fragment_source):
        
        texture =  glGenTextures(1)
        
        #// Generate a name for the texture
        glGenTextures(1, texture);

        #// Now bind it to the context using the GL_TEXTURE_2D binding point
        glBindTexture(GL_TEXTURE_2D, texture);

        #// Specify the amount of storage we want to use for the texture
        glTexStorage2D(GL_TEXTURE_2D,   #// 2D texture
                       8,               #// 8 mipmap levels
                       GL_RGBA32F,      #// 32-bit floating-point RGBA data
                       256, 256);       #// 256 x 256 texels


        #// Define some data to upload into the texture
        data = np.zeros(256 * 256 * 4);

        #// generate_texture() is a function that fills memory with image data
        generate_texture(data, 256, 256);

        #// Assume the texture is already bound to the GL_TEXTURE_2D target
        glTexSubImage2D(GL_TEXTURE_2D,  #// 2D texture
                        0,              #// Level 0
                        0, 0,           #// Offset 0, 0
                        256, 256,       #// 256 x 256 texels, replace entire image
                        GL_RGBA,        #// Four channel data
                        GL_FLOAT,       #// Floating point data
                        data);          #// Pointer to data

        #// Free the memory we allocated before - \GL now has our data
        #delete data;

        program = glCreateProgram();
        fs = glCreateShader(GL_FRAGMENT_SHADER);
        glShaderSource(fs, fragment_source);
        glCompileShader(fs);

        #print_shader_log(fs);

        vs = glCreateShader(GL_VERTEX_SHADER);
        glShaderSource(vs, vertex_source);
        glCompileShader(vs);

        #print_shader_log(vs);

        glAttachShader(program, vs);
        glAttachShader(program, fs);

        glLinkProgram(program);

        vao = GLuint(0)
        glGenVertexArrays(1, vao);
        glBindVertexArray(vao);

        return program





class Scene:

    def __init__(self):
        pass

    def display(self):
        green = [ 0.0, 0.25, 0.0, 1.0 ];
        glClearBufferfv(GL_COLOR, 0, green);

        glUseProgram(compile_program(vs_source, fs_source));
        
        glDrawArrays(GL_TRIANGLES, 0, 3);
        
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