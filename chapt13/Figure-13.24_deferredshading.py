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

from sbmath import m3dDegToRad, m3dRadToDeg, m3dTranslateMatrix44, m3dRotationMatrix44, \
    m3dMultiply, m3dOrtho, m3dPerspective, rotation_matrix, translate, m3dScaleMatrix44, \
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


MAX_DISPLAY_WIDTH       = 2048
MAX_DISPLAY_HEIGHT      = 2048
NUM_LIGHTS              = 64
NUM_INSTANCES           = (15 * 15)


gbuffer = GLuint(0)
gbuffer_tex = [GLuint(0) for _ in range(3)]
fs_quad_vao = GLuint(0)


render_program = GLuint(0)
render_program_nm = GLuint(0)
render_transform_ubo = GLuint(0)

light_program = GLuint(0)
light_ubo = GLuint(0)

vis_program = GLuint(0)


loc_vis_mode = GLint(0)

tex_diffuse = GLuint(0)

tex_nm = GLuint(0)

use_nm = False
paused = False


VIS_OFF = 0
VIS_NORMALS = 1
VIS_WS_COORDS = 2
VIS_DIFFUSE = 3
VIS_META = 4

vis_mode = VIS_OFF



class light_t_:
    position = glm.vec3         
    #unsigned int        : 32       // pad0
    color = glm.vec3         
    #unsigned int        : 32       // pad1

light_t = light_t_()


last_time = 0.0
total_time = 0.0

def load_shaders():
    global render_program
    global light_program
    global render_program_nm
    global vis_program
    global loc_vis_mode
    
    if (render_program):
        glDeleteProgram(render_program)
    if (light_program):
        glDeleteProgram(light_program)

    vs = shader_load("render.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("render.fs.glsl", GL_FRAGMENT_SHADER)

    render_program = glCreateProgram()
    glAttachShader(render_program, vs)
    glAttachShader(render_program, fs)
    glLinkProgram(render_program)

    glDeleteShader(vs)
    glDeleteShader(fs)

    vs = shader_load("render-nm.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("render-nm.fs.glsl", GL_FRAGMENT_SHADER)

    render_program_nm = glCreateProgram()
    glAttachShader(render_program_nm, vs)
    glAttachShader(render_program_nm, fs)
    glLinkProgram(render_program_nm)

    glDeleteShader(vs)
    glDeleteShader(fs)

    vs = shader_load("light.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("light.fs.glsl", GL_FRAGMENT_SHADER)

    light_program = glCreateProgram()
    glAttachShader(light_program, vs)
    glAttachShader(light_program, fs)
    glLinkProgram(light_program)

    glDeleteShader(fs)

    fs = shader_load("render-vis.fs.glsl", GL_FRAGMENT_SHADER)

    vis_program = glCreateProgram()
    glAttachShader(vis_program, vs)
    glAttachShader(vis_program, fs)
    glLinkProgram(vis_program)

    loc_vis_mode = glGetUniformLocation(vis_program, "vis_mode")

    glDeleteShader(vs)
    glDeleteShader(fs)



class Scene:

    def __init__(self, width, height):
        global gbuffer_tex
        global gbuffer
        global fs_quad_vao
        global light_ubo
        global render_transform_ubo
        global myobject
        global tex_nm
        global tex_diffuse
        
        glGenFramebuffers(1, gbuffer)
        glBindFramebuffer(GL_FRAMEBUFFER, gbuffer)

        gbuffer_tex = [glGenTextures(1) for _ in range(3)]
        glBindTexture(GL_TEXTURE_2D, gbuffer_tex[0])
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA32UI, MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT) 
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        glBindTexture(GL_TEXTURE_2D, gbuffer_tex[1])
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA32F, MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT) 
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        glBindTexture(GL_TEXTURE_2D, gbuffer_tex[2])
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_DEPTH_COMPONENT32F, MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT) 

        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, gbuffer_tex[0], 0)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, gbuffer_tex[1], 0)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, gbuffer_tex[2], 0)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glGenVertexArrays(1, fs_quad_vao)
        glBindVertexArray(fs_quad_vao)

        myobject.load("ladybug.sbm")
        tex_nm = ktxobject.ktx_load("ladybug_nm.ktx")
        tex_diffuse = ktxobject.ktx_load("ladybug_co.ktx")

        load_shaders()

        light_ubo = glGenBuffers(1)
        glBindBuffer(GL_UNIFORM_BUFFER, light_ubo)
        
        size_light_t = ctypes.sizeof(ctypes.c_float) * 6

        glBufferData(GL_UNIFORM_BUFFER, NUM_LIGHTS * size_light_t, None, GL_DYNAMIC_DRAW)

        render_transform_ubo = glGenBuffers(1)
        glBindBuffer(GL_UNIFORM_BUFFER, render_transform_ubo)
        glBufferData(GL_UNIFORM_BUFFER, (2 + NUM_INSTANCES) * glm.sizeof(glm.mat4), None, GL_DYNAMIC_DRAW)




    def display(self):
        global last_time
        global total_time
        
        currentTime = time.time()

        uint_zeros = [ 0, 0, 0, 0 ]
        float_zeros = [ 0.0, 0.0, 0.0, 0.0 ]
        float_ones = [ 1.0, 1.0, 1.0, 1.0 ]
        draw_buffers = [ GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1 ]



        if (not paused):
        
            total_time += (currentTime - last_time)

        last_time = currentTime

        t = total_time

        glBindFramebuffer(GL_FRAMEBUFFER, gbuffer)
        glViewport(0, 0, self.width, self.height)
        glDrawBuffers(2, draw_buffers)
        glClearBufferuiv(GL_COLOR, 0, uint_zeros)
        glClearBufferuiv(GL_COLOR, 1, uint_zeros)
        glClearBufferfv(GL_DEPTH, 0, float_ones)

        glBindBufferBase(GL_UNIFORM_BUFFER, 0, render_transform_ubo)
        
        
        matrices = glMapBufferRange(GL_UNIFORM_BUFFER,
                                    0,
                                    (2 + NUM_INSTANCES) * glm.sizeof(glm.mat4),
                                    GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

        matricesp = (GLfloat * 16 * (2 + NUM_INSTANCES) ).from_address(matrices)

        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 0.1, 1000.0)
        
        matricesp[0] = proj_matrix

                                         
                                         
        d = (sin(t * 0.131) + 2.0) * 0.15
        eye_pos = (d * 120.0 * sin(t * 0.11),  5.5,  d * 120.0 * cos(t * 0.01))
                                          
                                          
        view_matrix = (GLfloat * 16)(*identityMatrix)
        view_matrix = m3dLookAt(eye_pos,
                                (0.0, -20.0, 0.0),
                                (0.0, 1.0, 0.0))
                                
        matricesp[1] = (GLfloat * 16)(*view_matrix)
        
        
        for j in range(0, 15):

            j_f = float(j)
            
            for i in range(0, 15):

                i_f = float(i)

                T = (GLfloat * 16)(*identityMatrix)
                m3dTranslateMatrix44(T, (i - 7.5) * 7.0, 0.0, (j - 7.5) * 11.0)
                
                matricesp[j * 15 + i + 2] = T
            
        

        glUnmapBuffer(GL_UNIFORM_BUFFER)

        glUseProgram(render_program_nm if use_nm else render_program)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, tex_diffuse)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, tex_nm)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

        myobject.render(NUM_INSTANCES)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, self.width, self.height)
        glDrawBuffer(GL_BACK)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, gbuffer_tex[0])

        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, gbuffer_tex[1])

        if (vis_mode == VIS_OFF):
        
            glUseProgram(light_program)
        
        else:
        
            glUseProgram(vis_program)
            glUniform1i(loc_vis_mode, vis_mode)
        

        glDisable(GL_DEPTH_TEST)

        glBindBufferBase(GL_UNIFORM_BUFFER, 0, light_ubo)
        
        size_light_t = ctypes.sizeof(ctypes.c_float) * 6
        
        lights = glMapBufferRange(GL_UNIFORM_BUFFER,
                                    0,
                                    NUM_LIGHTS * size_light_t,
                                    GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)


        lightsp = (GLfloat * 6 * NUM_LIGHTS ).from_address(lights)
                                 
        for i in range(0, NUM_LIGHTS):

            i_f = (i - 7.5) * 0.1 + 0.3

            lightsp[i][0:3] = glm.vec3(100.0 * sin(t * 1.1 + (5.0 * i_f)) * cos(t * 2.3 + (9.0 * i_f)),
                                             15.0,
                                             100.0 * sin(t * 1.5 + (6.0 * i_f)) * cos(t * 1.9 + (11.0 * i_f)))
                                            
            lightsp[i][3:6] = glm.vec3(cos(i_f * 14.0) * 0.5 + 0.8,
                                          sin(i_f * 17.0) * 0.5 + 0.8,
                                          sin(i_f * 13.0) * cos(i_f * 19.0) * 0.5 + 0.8)


        glUnmapBuffer(GL_UNIFORM_BUFFER)

        glBindVertexArray(fs_quad_vao)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        glBindTexture(GL_TEXTURE_2D, 0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)
        

        glutSwapBuffers()

    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global vis_mode
        
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
                
        elif key == b'r' or key == b'R':
            load_shaders()
            
        elif key == b'p' or key == b'P': 
            paused = not paused
            
        elif key == b'n' or key == b'N': 
            use_nm = not use_nm
            
        elif key == b'1': 
            vis_mode = VIS_OFF
            
        elif key == b'2': 
            vis_mode = VIS_NORMALS
            
        elif key == b'3': 
            vis_mode = VIS_WS_COORDS
            
        elif key == b'4': 
            vis_mode = VIS_DIFFUSE
            
        elif key == b'5': 
            vis_mode = VIS_META
            





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

    #glutInitContextVersion(4,1)
    #glutInitContextProfile(GLUT_CORE_PROFILE)    
    
    w1 = glutCreateWindow('OpenGL SuperBible - Deferred Shading')
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
