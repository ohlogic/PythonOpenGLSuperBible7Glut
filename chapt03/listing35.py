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
except:
    print ('''
    ERROR: PyOpenGL not installed properly.
        ''')
    sys.exit()


from math import cos, sin



# Vertex program
vertex_shader_source = '''
#version 450 core
// 'offset' is an input vertex attribute
layout (location = 0) in vec4 offset;
layout (location = 1) in vec4 color;

// Declare VS_OUT as an output interface block
out VS_OUT
{
    vec4 color;
    // Send color to the next stage
} vs_out;

void main(void)
{
    const vec4 vertices[3] = vec4[3](vec4(0.25, -0.25, 0.5, 1.0),
    vec4(-0.25, -0.25, 0.5, 1.0),
    vec4(0.25, 0.25, 0.5, 1.0));
    // Add 'offset' to our hard-coded vertex position
    gl_Position = vertices[gl_VertexID] + offset;
    // Output a fixed value for vs_color
    vs_out.color = color;
}
'''



# Fragment program
fragment_shader_source = '''
#version 450 core

// Declare VS_OUT as an input interface block
in VS_OUT
{
    vec4 color;
    // Send color to the next stage
} fs_in;
// Output to the framebuffer
out vec4 color;

void main(void)
{
    // Simply assign the color we were given by the vertex shader to our output
    color = fs_in.color;
}
'''


def compile_program(vertex_source, fragment_source):
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

    if vertex_shader:
        glDeleteShader(vertex_shader)
    if fragment_shader:
        glDeleteShader(fragment_shader)

    return program





class Scene:

    def __init__(self):
        pass
        
    def display(self):

        currentTime = time.time()

        color = [ 0.0, 0.2, 0.0, 1.0 ];
        
        glClearBufferfv(GL_COLOR, 0, color)

        glUseProgram(compile_program(vertex_shader_source, fragment_shader_source))
        
        attrib = [ sin(currentTime) * 0.5,
        cos(currentTime) * 0.6,
        0.0, 0.0 ];
        
        # Update the value of input attribute 0
        glVertexAttrib4fv(0, attrib);
                
        
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

if __name__ == '__main__':
    start = time.time()

    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    
    w1 = glutCreateWindow('Listing 3.5 and Listing 3.6')
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

