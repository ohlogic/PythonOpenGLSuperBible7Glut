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


class Scene:

    def __init__(self):
        pass
        
    def display(self):

        currentTime = time.time()

        color = [ sin(currentTime) * 0.5 + 0.5,
        cos(currentTime) * 0.5 + 0.5,
        0.0,
        1.0 ]
        
        glClearBufferfv(GL_COLOR, 0, color);

        
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
    
    w1 = glutCreateWindow('Listing 2.2')
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

