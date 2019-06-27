#!/usr/bin/python3

import sys
import time

sys.path.append("./shared")

#from sbmloader import SBMObject    # location of sbm file format loader
from ktxloader import KTXObject    # location of ktx file format loader

from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate, m3dScaleMatrix44

fullscreen = True

#import numpy.matlib
#import numpy as np

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

identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

render_prog = GLuint(0)
render_vao = GLuint(0)

class uniforms:
    mvp = GLint
    offset = GLint

tex_wall = GLuint(0)
tex_ceiling = GLuint(0)
tex_floor = GLuint(0)

uniform = uniforms()

class Scene:

    def __init__(self, width, height):
        global render_prog
        global render_vao
        global uniform
        
        global tex_wall, tex_ceiling, tex_floor
        
        self.width = width
        self.height = height

        vs = GLuint(0)
        fs = GLuint(0)

        vs_source = '''
#version 420 core

out VS_OUT
{
    vec2 tc;
} vs_out;

uniform mat4 mvp;
uniform float offset;

void main(void)
{
    const vec2[4] position = vec2[4](vec2(-0.5, -0.5),
                                     vec2( 0.5, -0.5),
                                     vec2(-0.5,  0.5),
                                     vec2( 0.5,  0.5));
    vs_out.tc = (position[gl_VertexID].xy + vec2(offset, 0.5)) * vec2(30.0, 1.0);
    gl_Position = mvp * vec4(position[gl_VertexID], 0.0, 1.0);
}
'''

        fs_source = '''
#version 420 core

layout (location = 0) out vec4 color;

in VS_OUT
{
    vec2 tc;
} fs_in;

layout (binding = 0) uniform sampler2D tex;

void main(void)
{
    color = texture(tex, fs_in.tc);
}
'''

        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, vs_source)
        glCompileShader(vs)

        glGetShaderInfoLog(vs)

        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, fs_source)
        glCompileShader(fs)

        glGetShaderInfoLog(vs)

        render_prog = glCreateProgram()
        glAttachShader(render_prog, vs)
        glAttachShader(render_prog, fs)
        glLinkProgram(render_prog)

        glDeleteShader(vs)
        glDeleteShader(fs)

        glGetProgramInfoLog(render_prog)
        
        uniform.mvp = glGetUniformLocation(render_prog, "mvp")
        uniform.offset = glGetUniformLocation(render_prog, "offset")

        glGenVertexArrays(1, render_vao)
        glBindVertexArray(render_vao)
        
        ktxobj = KTXObject()
        
        tex_wall = ktxobj.ktx_load("brick.ktx")
        tex_ceiling = ktxobj.ktx_load("ceiling.ktx")
        tex_floor = ktxobj.ktx_load("floor.ktx")
        
        
        textures = [ tex_floor, tex_wall, tex_ceiling ]

        for i in range (0, 3):
            glBindTexture(GL_TEXTURE_2D, textures[i])
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glBindVertexArray(render_vao)


    def display(self):

        green = [ 0.0, 0.1, 0.0, 0.0 ]
        currentTime = time.time()

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, green)

        glUseProgram(render_prog)
        
        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(60.0), float(self.width) / float(self.height), 0.1, 100.0)

        glUniform1f(uniform.offset, -(currentTime * 0.03) % 1) # negative sign to postive changes direction

        textures = [ tex_wall, tex_ceiling, tex_wall, tex_floor ]
 
        for i in range(0, 4):

            RZ = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RZ, i * m3dDegToRad(90.0), 0.0, 0.0, 1.0)

            T = (GLfloat * 16)(*identityMatrix)
            m3dTranslateMatrix44(T, -5, 0, -10)

            RY = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RY, m3dDegToRad(90.0), 0.0, 1.0, 0.0)
            
            S = (GLfloat * 16)(*identityMatrix)
            m3dScaleMatrix44(S, 300.0, 10.0, 1.0)
            
            mv_matrix = (GLfloat * 16)(*identityMatrix)
            mv_matrix = m3dMultiply(RZ, m3dMultiply(T, m3dMultiply(RY, S)))
            
            mvp = (GLfloat * 16)(*identityMatrix)
            mvp = m3dMultiply(proj_matrix , mv_matrix )

            glUniformMatrix4fv(uniform.mvp, 1, GL_FALSE, mvp)

            glBindTexture(GL_TEXTURE_2D, textures[i]);
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);

        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

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
        time.sleep(1/60.0)


if __name__ == '__main__':
    start = time.time()

    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)

    glutInitWindowSize(512, 512)

    w1 = glutCreateWindow('OpenGL SuperBible - Tunnel')
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
    