#!/usr/bin/python3

import sys
import time
import ctypes

fullscreen = True
sys.path.append("./shared")

from sbmloader import SBMObject    # location of sbm file format loader
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

myobject = SBMObject()
ktxobject = KTXObject()
overlay = OVERLAY_()


program = GLuint(0)
vao = GLuint(0)
tex_checker = GLuint(0)
paused = False
use_perspective = True

class UNIFORMS_:
    mvp = GLint(0)
    use_perspective = GLint(0)

uniforms = UNIFORMS_()

class Scene:

    def __init__(self, width, height):
        global program
        global vao
        global tex_checker
        global uniforms
        
        
        vs_source = '''
#version 410 core

out VS_OUT
{
    vec2 tc;
    noperspective vec2 tc_np;
} vs_out;

uniform mat4 mvp;

void main(void)
{
    const vec4 vertices[] = vec4[](vec4(-0.5, -0.5, 0.0, 1.0),
                                   vec4( 0.5, -0.5, 0.0, 1.0),
                                   vec4(-0.5,  0.5, 0.0, 1.0),
                                   vec4( 0.5,  0.5, 0.0, 1.0));

    vec2 tc = (vertices[gl_VertexID].xy + vec2(0.5));
    vs_out.tc = tc;
    vs_out.tc_np = tc;
    gl_Position = mvp * vertices[gl_VertexID];
}
'''

        fs_source = '''
#version 410 core

out vec4 color;

uniform sampler2D tex_checker;

uniform bool use_perspective = true;

in VS_OUT
{
    vec2 tc;
    noperspective vec2 tc_np;
} fs_in;

void main(void)
{
    vec2 tc = mix(fs_in.tc_np, fs_in.tc, bvec2(use_perspective));
    color = texture(tex_checker, tc).rrrr;
}
'''

        buffer=''

        program = glCreateProgram()
        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)

        glGetShaderInfoLog(vs)

        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source)
        glCompileShader(fs)

        glGetShaderInfoLog(fs)

        glAttachShader(program, vs)
        glAttachShader(program, fs)

        glLinkProgram(program)

        uniforms.mvp = glGetUniformLocation(program, "mvp")
        uniforms.use_perspective = glGetUniformLocation(program, "use_perspective")

        glGenVertexArrays(1, vao)
        glBindVertexArray(vao)
        
        checker_data = np.array([
        
            0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF,
            0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00,
            0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF,
            0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00,
            0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF,
            0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00,
            0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF,
            0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00,
            
        ], dtype=np.ubyte) # unsigned char 

        tex_checker = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_checker)
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_R8, 8, 8)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 8, 8, GL_RED, GL_UNSIGNED_BYTE, checker_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)




    def display(self):

        currentTime = time.time()


        black = [ 0.0, 0.0, 0.0, 0.0 ]
        one = 1.0
        last_time = 0.0
        total_time = 0.0

        if (not paused):
            total_time += (currentTime - last_time)
        last_time = currentTime

        t = total_time * 14.3

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_DEPTH, 0, one)


        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, 0.0, -1.5)
    
        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, m3dDegToRad(t), 0.0, 1.0, 0.0)
                            
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(T, RY)


        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(60.0), float(self.width) / float(self.height), 0.1, 1000.0)

        glUseProgram(program)

        glUniformMatrix4fv(uniforms.mvp, 1, GL_FALSE, m3dMultiply(proj_matrix , mv_matrix) )
        glUniform1i(uniforms.use_perspective, use_perspective)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global paused
        global use_perspective
        
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
            use_perspective = not use_perspective
        elif key == b'p' or key == b'P':
            paused = not paused
                
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
    w1 = glutCreateWindow('OpenGL SuperBible - Perspective')
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
