#!/usr/bin/python3

import sys
import time 
import os
import time
import math
import ctypes

sys.path.append("./shared")

from sbmloader import SBMObject    # location of sbm file format loader
from ktxloader import KTXObject    # location of ktx file format loader

from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate

fullscreen = True

import numpy.matlib 
import numpy as np 

try:
    from OpenGL.GLUT import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
    #from OpenGL.raw.GL.ARB.vertex_array_object import glGenVertexArrays, glBindVertexArray
except:
    print ('''
    ERROR: PyOpenGL not installed properly.
        ''')
    sys.exit()


# Vertex program
vs_source = '''
#version 420 core
uniform mat4 mv_matrix;
uniform mat4 proj_matrix;
layout (location = 0) in vec4 position;
layout (location = 4) in vec2 tc;
out VS_OUT
{
    vec2 tc;
} vs_out;
void main(void)
{
    vec4 pos_vs = mv_matrix * position;
    vs_out.tc = tc;
    gl_Position = proj_matrix * pos_vs;
}
'''

# Fragment program
fs_source = '''
#version 420 core
layout (binding = 0) uniform sampler2D tex_object;
in VS_OUT
{
    vec2 tc;
} fs_in;
out vec4 color;
void main(void)
{
    color = texture(tex_object, fs_in.tc * vec2(3.0, 1.0));
}
'''

identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

render_prog = GLuint(0)

uniforms_mv_matrix = (GLfloat * 16)(*identityMatrix)
uniforms_proj_matrix = (GLfloat * 16)(*identityMatrix)

tex_index = 0
tex_object = []


def load_shaders():
        global render_prog
        global uniforms_mv_matrix
        global uniforms_proj_matrix

        if (render_prog):
            glDeleteProgram(render_prog);

        fs = glCreateShader(GL_FRAGMENT_SHADER);

        glShaderSource(fs, fs_source);
        glCompileShader(fs);

        vs = glCreateShader(GL_VERTEX_SHADER);

        glShaderSource(vs, vs_source);
        glCompileShader(vs);

        render_prog = glCreateProgram();
        glAttachShader(render_prog, vs);
        glAttachShader(render_prog, fs);
        glLinkProgram(render_prog);

        glDeleteShader(vs);
        glDeleteShader(fs);

        uniforms_mv_matrix = glGetUniformLocation(render_prog, "mv_matrix");
        uniforms_proj_matrix = glGetUniformLocation(render_prog, "proj_matrix");

class Scene:
    def __init__(self, width, height):

        self.width = width
        self.height = height

        B = (0x00, 0x00, 0x00, 0x00)
        W = (0xFF, 0xFF, 0xFF, 0xFF)
        tex_data = [
            B, W, B, W, B, W, B, W, B, W, B, W, B, W, B, W,
            W, B, W, B, W, B, W, B, W, B, W, B, W, B, W, B,
            B, W, B, W, B, W, B, W, B, W, B, W, B, W, B, W,
            W, B, W, B, W, B, W, B, W, B, W, B, W, B, W, B,
            B, W, B, W, B, W, B, W, B, W, B, W, B, W, B, W,
            W, B, W, B, W, B, W, B, W, B, W, B, W, B, W, B,
            B, W, B, W, B, W, B, W, B, W, B, W, B, W, B, W,
            W, B, W, B, W, B, W, B, W, B, W, B, W, B, W, B,
            B, W, B, W, B, W, B, W, B, W, B, W, B, W, B, W,
            W, B, W, B, W, B, W, B, W, B, W, B, W, B, W, B,
            B, W, B, W, B, W, B, W, B, W, B, W, B, W, B, W,
            W, B, W, B, W, B, W, B, W, B, W, B, W, B, W, B,
            B, W, B, W, B, W, B, W, B, W, B, W, B, W, B, W,
            W, B, W, B, W, B, W, B, W, B, W, B, W, B, W, B,
            B, W, B, W, B, W, B, W, B, W, B, W, B, W, B, W,
            W, B, W, B, W, B, W, B, W, B, W, B, W, B, W, B,
        ]

        tex_object.append( glGenTextures(1) )

        #glGenTextures(1, tex_object[0]);
        glBindTexture(GL_TEXTURE_2D, tex_object[0]);
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGB8, 16, 16);
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 16, 16, GL_RGBA, GL_UNSIGNED_BYTE, tex_data);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

        tex_object.append (  glGenTextures(1) )
        
        ktxobj = KTXObject()
        
        tex_object[1] = ktxobj.ktx_load("pattern1.ktx")
        #tex_object[1] = sb7::ktx::file::load("pattern1.ktx");

        myobject.load("torus_nrms_tc.sbm");

        load_shaders();

        glEnable(GL_DEPTH_TEST);
        glDepthFunc(GL_LEQUAL);


    def display(self):

        global uniforms_mv_matrix
        global uniforms_proj_matrix

        currentTime = time.time()

        gray = [ 0.2, 0.2, 0.2, 1.0 ];
        ones = [ 1.0 ];

        glClearBufferfv(GL_COLOR, 0, gray);
        glClearBufferfv(GL_DEPTH, 0, ones);

        glViewport(0, 0, self.width, self.height);

        glBindTexture(GL_TEXTURE_2D, tex_object[tex_index]);

        glUseProgram(render_prog);

        T = (GLfloat * 16)(*identityMatrix)
        RX = (GLfloat * 16)(*identityMatrix)
        RY = (GLfloat * 16)(*identityMatrix)
        R = (GLfloat * 16)(*identityMatrix)

        # other ways to matrix multiply can be found at https://stackoverflow.com/questions/56711138/how-to-read-parse-the-sbm-file-format-from-superbible-opengl
        # Matrix multiplication is not commutative, order matters when multiplying matrices
        T  = np.matrix(translate(0.0, 0.0, -4.0)).reshape(4,4)
        RX = np.matrix(rotation_matrix( [1.0, 0.0, 0.0], currentTime * m3dDegToRad(17.0)))
        RY = np.matrix(rotation_matrix( [0.0, 1.0, 0.0], currentTime * m3dDegToRad(13.0)))
        mv_matrix = RX * RY * T

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(60.0), float(self.width) / float(self.height), 0.1, 100.0);    

        glUniformMatrix4fv(uniforms_mv_matrix, 1, GL_FALSE, mv_matrix);
        glUniformMatrix4fv(uniforms_proj_matrix, 1, GL_FALSE, proj_matrix);

        myobject.render() # renders the torus

        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global tex_index

        print ('key:' , key)
        if key == b'\x1b': # ESC
            sys.exit()

        elif key == b'f' or key == b'F': #fullscreen toggle

            if (fullscreen == True):
                glutReshapeWindow(self.width, self.height)
                glutPositionWindow(int((1360/2)-(512/2)), int((768/2)-(512/2)))
                fullscreen = False
            else:
                glutFullScreen()
                fullscreen = True

        elif key == b'r' or key == b'R': 
            load_shaders()

        elif key == b't' or key == b'T': 
            tex_index+=1
            if (tex_index > 1):
                tex_index = 0

        print('done')

    def init(self):
        pass

    def timer(self, blah):

        glutPostRedisplay()
        glutTimerFunc( int(1/60), self.timer, 0)
        time.sleep(1/20.0)

myobject = SBMObject()
if __name__ == '__main__':
    start = time.time()

    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    glutInitWindowSize(512, 512)
    w1 = glutCreateWindow('OpenGL SuperBible - Texture Coordinates')

    fullscreen = False
    #glutFullScreen()

    scene = Scene(512, 512)
    glutReshapeFunc(scene.reshape)
    glutDisplayFunc(scene.display)
    glutKeyboardFunc(scene.keyboard)

    glutIdleFunc(scene.display)
    #glutTimerFunc( int(1/60), scene.timer, 0)

    scene.init()

glutMainLoop()