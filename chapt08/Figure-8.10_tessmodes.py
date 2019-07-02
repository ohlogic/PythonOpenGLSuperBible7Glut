#!/usr/bin/python3

import sys
import time
import ctypes

fullscreen = True

sys.path.append("./shared")

#from sbmloader import SBMObject    # location of sbm file format loader
from ktxloader import KTXObject    # location of ktx file format loader

#from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate, m3dScaleMatrix44, \
#    scale, m3dLookAt, normalize

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
identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]


#myobject = SBMObject()
ktxobject = KTXObject()

program = [GLuint(0) for _ in range(4)]
program_index = 0
vao = GLuint(0)


class OVERLAY_():

    def __init__(self):
        self.dirty = False
        self.vao = GLuint(0)
        
        self.screen_buffer = []
        
    def print(self, str1):
    
        i = str(''.join(self.screen_buffer)).find('\0')
        for x in range(0, len(str1)):
            self.screen_buffer[i+x] = str1[x]

        self.dirty = True

    def drawText(self, str1, x, y):
    
        z = x + (y* self.buffer_width)
    
        for x in range(0, len(str1)):
            self.screen_buffer[z+x] = str1[x]
            
        self.dirty = True
        

    def moveCursor(self, x, y):
        self.cursor_x = x
        self.cursor_y = y
    
    def clear(self):
        
        self.screen_buffer = ['\0' for _ in range(self.buffer_width * self.buffer_height)]
        
        self.dirty = True
        self.cursor_x = 0
        self.cursor_y = 0
    
    
    def draw(self):
    
        glUseProgram(self.text_program)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.text_buffer)
        
        if (self.dirty):
        
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, self.buffer_width, self.buffer_height, GL_RED_INTEGER, GL_UNSIGNED_BYTE, str(''.join(self.screen_buffer)))
            dirty = False;
        
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D_ARRAY, self.font_texture)

        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    
    
    def init(self, width, height, font=''):

        vs = GLuint(0)
        fs = GLuint(0)

        self.buffer_width = width
        self.buffer_height = height

        vs = glCreateShader(GL_VERTEX_SHADER)
        fs = glCreateShader(GL_FRAGMENT_SHADER)

        vs_source = '''
#version 440 core
void main(void)
{
    gl_Position = vec4(float((gl_VertexID >> 1) & 1) * 2.0 - 1.0,
                       float((gl_VertexID & 1)) * 2.0 - 1.0,
                       0.0, 1.0);
}
'''

        fs_source = '''
#version 440 core
layout (origin_upper_left) in vec4 gl_FragCoord;
layout (location = 0) out vec4 o_color;
layout (binding = 0) uniform isampler2D text_buffer;
layout (binding = 1) uniform isampler2DArray font_texture;
void main(void)
{
    ivec2 frag_coord = ivec2(gl_FragCoord.xy);
    ivec2 char_size = textureSize(font_texture, 0).xy;
    ivec2 char_location = frag_coord / char_size;
    ivec2 texel_coord = frag_coord % char_size;
    int character = texelFetch(text_buffer, char_location, 0).x;
    float val = texelFetch(font_texture, ivec3(texel_coord, character), 0).x;
    if (val == 0.0)
        discard;
    o_color = vec4(1.0);
}
'''
        glShaderSource(vs, vs_source)
        glCompileShader(vs)

        glShaderSource(fs, fs_source)
        glCompileShader(fs)

        self.text_program = glCreateProgram()
        glAttachShader(self.text_program, vs)
        glAttachShader(self.text_program, fs)
        glLinkProgram(self.text_program)

        glDeleteShader(fs)
        glDeleteShader(vs)

        # glCreateVertexArrays(1, &vao);
        glGenVertexArrays(1, self.vao)
        glBindVertexArray(self.vao)

        # glCreateTextures(GL_TEXTURE_2D, 1, &text_buffer);
        self.text_buffer = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.text_buffer)
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_R8UI, width, height)
        
        if (font  == ''):
            font = "cp437_9x16.ktx"
        
        self.font_texture = ktxobject.ktx_load(font)

        self.screen_buffer = ['\0' for _ in range(width * height)]
        

overlay = OVERLAY_()

class Scene:

    def __init__(self, width, height):
        global program
        global vao
        global overlay
        
        vs_source = '''
#version 420 core

void main(void)
{
    const vec4 vertices[] = vec4[](vec4( 0.4, -0.4, 0.5, 1.0),
                                   vec4(-0.4, -0.4, 0.5, 1.0),
                                   vec4( 0.4,  0.4, 0.5, 1.0),
                                   vec4(-0.4,  0.4, 0.5, 1.0));

    gl_Position = vertices[gl_VertexID];
}
'''

        tcs_source_triangles = '''

#version 420 core

layout (vertices = 3) out;

void main(void)
{
    if (gl_InvocationID == 0)
    {
        gl_TessLevelInner[0] = 5.0;
        gl_TessLevelOuter[0] = 8.0;
        gl_TessLevelOuter[1] = 8.0;
        gl_TessLevelOuter[2] = 8.0;
    }
    gl_out[gl_InvocationID].gl_Position = gl_in[gl_InvocationID].gl_Position;
}
'''

        tes_source_triangles = '''
#version 420 core

layout (triangles) in;

void main(void)
{
    gl_Position = (gl_TessCoord.x * gl_in[0].gl_Position) +
                  (gl_TessCoord.y * gl_in[1].gl_Position) +
                  (gl_TessCoord.z * gl_in[2].gl_Position);
}
'''

        tes_source_triangles_as_points = '''
#version 420 core

layout (triangles, point_mode) in;

void main(void)
{
    gl_Position = (gl_TessCoord.x * gl_in[0].gl_Position) +
                  (gl_TessCoord.y * gl_in[1].gl_Position) +
                  (gl_TessCoord.z * gl_in[2].gl_Position);
}
'''

        tcs_source_quads = '''
#version 420 core

layout (vertices = 4) out;

void main(void)
{
    if (gl_InvocationID == 0)
    {
        gl_TessLevelInner[0] = 9.0;
        gl_TessLevelInner[1] = 7.0;
        gl_TessLevelOuter[0] = 3.0;
        gl_TessLevelOuter[1] = 5.0;
        gl_TessLevelOuter[2] = 3.0;
        gl_TessLevelOuter[3] = 5.0;
    }
    gl_out[gl_InvocationID].gl_Position = gl_in[gl_InvocationID].gl_Position;
}
'''

        tes_source_quads = '''
#version 420 core

layout (quads) in;

void main(void)
{
    vec4 p1 = mix(gl_in[0].gl_Position, gl_in[1].gl_Position, gl_TessCoord.x);
    vec4 p2 = mix(gl_in[2].gl_Position, gl_in[3].gl_Position, gl_TessCoord.x);
    gl_Position = mix(p1, p2, gl_TessCoord.y);
}
'''

        tcs_source_isolines = '''
#version 420 core

layout (vertices = 4) out;

void main(void)
{
    if (gl_InvocationID == 0)
    {
        gl_TessLevelOuter[0] = 5.0;
        gl_TessLevelOuter[1] = 5.0;
    }
    gl_out[gl_InvocationID].gl_Position = gl_in[gl_InvocationID].gl_Position;
}
'''

        tes_source_isolines = '''
#version 420 core

layout (isolines) in;

void main(void)
{
    float r = (gl_TessCoord.y + gl_TessCoord.x / gl_TessLevelOuter[0]);
    float t = gl_TessCoord.x * 2.0 * 3.14159;
    gl_Position = vec4(sin(t) * r, cos(t) * r, 0.5, 1.0);
}
'''

        fs_source = '''
#version 420 core

out vec4 color;

void main(void)
{
    color = vec4(1.0);
}
'''

        i = 0
        
        vs_sources = [
            vs_source, vs_source, vs_source, vs_source
        ]

        tcs_sources = [
            tcs_source_quads, tcs_source_triangles, tcs_source_triangles, tcs_source_isolines
        ]

        tes_sources = [
            tes_source_quads, tes_source_triangles, tes_source_triangles_as_points, tes_source_isolines
        ]

        fs_sources = [
            fs_source, fs_source, fs_source, fs_source
        ]

        overlay.init(80, 50);
        
        for i in range(0, 4):

            program[i] = glCreateProgram()
            
            vs = glCreateShader(GL_VERTEX_SHADER)
            glShaderSource(vs, vs_sources[i])
            glCompileShader(vs)

            tcs = glCreateShader(GL_TESS_CONTROL_SHADER)
            glShaderSource(tcs, tcs_sources[i])
            glCompileShader(tcs)

            tes = glCreateShader(GL_TESS_EVALUATION_SHADER)
            glShaderSource(tes, tes_sources[i])
            glCompileShader(tes)

            fs = glCreateShader(GL_FRAGMENT_SHADER)
            glShaderSource(fs, fs_sources[i])
            glCompileShader(fs)

            glAttachShader(program[i], vs)
            glAttachShader(program[i], tcs)
            glAttachShader(program[i], tes)
            glAttachShader(program[i], fs)
            glLinkProgram(program[i])

            glDeleteShader(vs)
            glDeleteShader(tcs)
            glDeleteShader(tes)
            glDeleteShader(fs)

        glGenVertexArrays(1, vao)
        glBindVertexArray(vao)

        glPatchParameteri(GL_PATCH_VERTICES, 4)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)


    def display(self):

        currentTime = time.time()

        black = [0.0,0.0,0.0]
        
        glClearBufferfv(GL_COLOR, 0, black)

        glUseProgram(program[program_index])
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glDrawArrays(GL_PATCHES, 0, 4)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        mode_names = [
            "QUADS", "TRIANGLES", "QUADS AS POINTS", "ISOLINES"
        ]


        overlay.clear()
        overlay.print("Mode: ")
        overlay.print(mode_names[program_index])
        overlay.print(" (M toggles)")
        overlay.draw()

        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global program_index
        
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
            program_index = (program_index + 1) % 4;

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

    w1 = glutCreateWindow('OpenGL SuperBible - Tessellation Modes')
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
