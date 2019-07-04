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

MAX_SCENE_WIDTH     = 2048
MAX_SCENE_HEIGHT    = 2048
SPHERE_COUNT        = 32


tex_src = GLuint(0)
tex_lut = GLuint(0)

render_fbo = GLuint(0)
filter_fbo = [ GLuint(0) for _ in range(2) ]

tex_scene = GLuint(0)
tex_brightpass = GLuint(0)
tex_depth = GLuint(0)
tex_filter = [ GLuint(0) for _ in range(2) ]

program_render  = GLuint(0)
program_filter  = GLuint(0)
program_resolve  = GLuint(0)
vao  = GLuint(0)
exposure = 1.0
mode = 0
paused = False
bloom_factor = 1.0
show_bloom = True
show_scene = True
show_prefilter = False
bloom_thresh_min = 0.8
bloom_thresh_max = 1.2

class UNIFORMS_:

    class scene:
        bloom_thresh_min = 0.8
        bloom_thresh_max = 1.2

    class resolve:
        exposure = 1.0
        bloom_factor = 1.0
        scene_factor = 0

uniforms = UNIFORMS_()

ubo_transform = GLuint(0)
ubo_material = GLuint(0)

def load_shaders():
    global program_render
    global program_filter
    global program_resolve
    global uniforms

    shaders = [GLuint(0), GLuint(0)]

    if (program_render):
        glDeleteProgram(program_render)

    shaders[0] = shader_load("hdrbloom-scene.vs.glsl", GL_VERTEX_SHADER)
    shaders[1] = shader_load("hdrbloom-scene.fs.glsl", GL_FRAGMENT_SHADER)
    program_render = link_from_shaders(shaders, 2, True)

    uniforms.scene.bloom_thresh_min = glGetUniformLocation(program_render, "bloom_thresh_min")
    uniforms.scene.bloom_thresh_max = glGetUniformLocation(program_render, "bloom_thresh_max")

    if (program_filter):
        glDeleteProgram(program_filter)

    shaders[0] = shader_load("hdrbloom-filter.vs.glsl", GL_VERTEX_SHADER)
    shaders[1] = shader_load("hdrbloom-filter.fs.glsl", GL_FRAGMENT_SHADER)
    program_filter = link_from_shaders(shaders, 2, True)

    if (program_resolve):
        glDeleteProgram(program_resolve)

    shaders[0] = shader_load("hdrbloom-resolve.vs.glsl", GL_VERTEX_SHADER)
    shaders[1] = shader_load("hdrbloom-resolve.fs.glsl", GL_FRAGMENT_SHADER)
    program_resolve = link_from_shaders(shaders, 2, True)

    uniforms.resolve.exposure = glGetUniformLocation(program_resolve, "exposure")
    uniforms.resolve.bloom_factor = glGetUniformLocation(program_resolve, "bloom_factor")
    uniforms.resolve.scene_factor = glGetUniformLocation(program_resolve, "scene_factor")



class Scene:

    def __init__(self, width, height):
        global myobject
        global vao
        global render_fbo
        global tex_scene
        global tex_brightpass
        global tex_depth
        global filter_fbo
        global tex_filter
        global tex_lut
        global ubo_transform
        global ubo_material

        self.width = width
        self.height = height


        buffers = [ GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1 ]

        glGenVertexArrays(1, vao)
        glBindVertexArray(vao)

        load_shaders()

        exposureLUT   = [ 11.0, 6.0, 3.2, 2.8, 2.2, 1.90, 1.80, 1.80, 1.70, 1.70,  1.60, 1.60, 1.50, 1.50, 1.40, 1.40, 1.30, 1.20, 1.10, 1.00 ]

        glGenFramebuffers(1, render_fbo)
        glBindFramebuffer(GL_FRAMEBUFFER, render_fbo)

        tex_scene = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_scene)
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA16F, MAX_SCENE_WIDTH, MAX_SCENE_HEIGHT)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, tex_scene, 0)

        tex_brightpass = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_brightpass)
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA16F, MAX_SCENE_WIDTH, MAX_SCENE_HEIGHT)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, tex_brightpass, 0)

        tex_depth = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_depth)
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_DEPTH_COMPONENT32F, MAX_SCENE_WIDTH, MAX_SCENE_HEIGHT)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, tex_depth, 0)
        glDrawBuffers(2, buffers)

        #glGenFramebuffers(2, filter_fbo[0])
        filter_fbo = [ glGenFramebuffers(1) for _ in range(2)]

        #glGenTextures(2, tex_filter[0])
        tex_filter = [glGenTextures(1) for _ in range(2)]


        for i in range(0,2):

            glBindFramebuffer(GL_FRAMEBUFFER, filter_fbo[i])
            glBindTexture(GL_TEXTURE_2D, tex_filter[i])
            glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA16F, MAX_SCENE_WIDTH if i==0 else MAX_SCENE_HEIGHT, MAX_SCENE_HEIGHT if i==0 else MAX_SCENE_WIDTH)
            glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, tex_filter[i], 0)
            glDrawBuffers(1, buffers)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        tex_lut = glGenTextures(1)
        glBindTexture(GL_TEXTURE_1D, tex_lut)
        glTexStorage1D(GL_TEXTURE_1D, 1, GL_R32F, 20)
        glTexSubImage1D(GL_TEXTURE_1D, 0, 0, 20, GL_RED, GL_FLOAT, exposureLUT)
        glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)

        myobject.load("torus.sbm")

        glGenBuffers(1, ubo_transform)
        glBindBuffer(GL_UNIFORM_BUFFER, ubo_transform)
        glBufferData(GL_UNIFORM_BUFFER, (2 + SPHERE_COUNT) * glm.sizeof(glm.mat4), None, GL_DYNAMIC_DRAW)

        class material:
            diffuse_color = glm.vec3
            specular_color = glm.vec3
            specular_power = GLfloat(0)
            ambient_color = glm.vec3

        glGenBuffers(1, ubo_material)
        glBindBuffer(GL_UNIFORM_BUFFER, ubo_material)


        size_material = ctypes.sizeof(ctypes.c_float) * 12;

        glBufferData(GL_UNIFORM_BUFFER, SPHERE_COUNT * size_material, None, GL_STATIC_DRAW)

        mat = glMapBufferRange(GL_UNIFORM_BUFFER, 0, SPHERE_COUNT * size_material, GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)
        m = (GLfloat * 12 * SPHERE_COUNT).from_address(mat)

        ambient = 0.002
        for i in range(SPHERE_COUNT):

            fi = 3.14159267 * i / 8.0

            m[i][0:3]  = (ctypes.c_float * 3)(sin(fi) * 0.5 + 0.5, sin(fi + 1.345) * 0.5 + 0.5, sin(fi + 2.567) * 0.5 + 0.5)
            m[i][4:7]  = (ctypes.c_float * 3)(2.8, 2.8, 2.9)
            m[i][7]    = 30
            m[i][8:11] = (ctypes.c_float * 3)(ambient * 0.025, ambient * 0.025, ambient * 0.025)

            ambient *= 1.5

        glUnmapBuffer(GL_UNIFORM_BUFFER)

    def display(self):
        global program_filter
        global program_resolve
        global program_render
        global tex_filter
        global exposure
        global vao
        global filter_fbo
        global ubo_transform
        global ubo_material
        global bloom_thresh_min
        global bloom_thresh_max
        global uniforms
        global tex_brightpass
        global myobject
        global render_fbo

        currentTime = time.time()

        black = [ 0.0, 0.0, 0.0, 1.0 ]
        one = 1.0
        last_time = 0.0
        total_time = 0.0

        if (not paused):
            total_time += (currentTime - last_time)

        last_time = currentTime
        t = total_time

        glViewport(0, 0, self.width, self.height)

        glBindFramebuffer(GL_FRAMEBUFFER, render_fbo)
        glClearBufferfv(GL_COLOR, 0, black)
        glClearBufferfv(GL_COLOR, 1, black)
        glClearBufferfv(GL_DEPTH, 0, one)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        glUseProgram(program_render)

        glBindBufferBase(GL_UNIFORM_BUFFER, 0, ubo_transform)

        class transforms_t:
            mat_proj = glm.mat4
            mat_view = glm.mat4
            mat_model = [glm.mat4 for _ in range(SPHERE_COUNT)]

        size_transforms_t = glm.sizeof(glm.mat4) * (SPHERE_COUNT+2)

        mbuffer = glMapBufferRange(GL_UNIFORM_BUFFER, 0, size_transforms_t, GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)
        bufferp = (GLfloat * 16 * (SPHERE_COUNT+2)).from_address(mbuffer)

        mat_proj = (GLfloat * 16)(*identityMatrix)
        mat_proj = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 1.0, 1000.0)

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, 0.0, -20.0)

        bufferp[0] = mat_proj

        bufferp[1] = T

        for i in range(2, SPHERE_COUNT+2):

            fi = 3.141592 * i / 16.0
            # // float r = cosf(fi * 0.25f) * 0.4f + 1.0f
            r = 0.6 if (i & 2) else 1.5

            T1 = (GLfloat * 16)(*identityMatrix)
            m3dTranslateMatrix44(T1, cos(t + fi) * 5.0 * r, sin(t + fi * 4.0) * 4.0, sin(t + fi) * 5.0 * r)

            RY = (GLfloat * 16)(*identityMatrix)
            m3dRotationMatrix44(RY, currentTime * m3dDegToRad(30.0) * fi, sin(t + fi * 2.13) * 75.0, cos(t + fi * 1.37) * 92.0, 0.0)

            m_model = (GLfloat * 16)(*identityMatrix)
            m_model = m3dMultiply(T1, RY)            

            bufferp[i] = m_model


        glUnmapBuffer(GL_UNIFORM_BUFFER)
        glBindBufferBase(GL_UNIFORM_BUFFER, 1, ubo_material)

        glUniform1f(uniforms.scene.bloom_thresh_min, bloom_thresh_min)
        glUniform1f(uniforms.scene.bloom_thresh_max, bloom_thresh_max)

        myobject.render(SPHERE_COUNT)

        glDisable(GL_DEPTH_TEST)

        glUseProgram(program_filter)

        glBindVertexArray(vao)

        glBindFramebuffer(GL_FRAMEBUFFER, filter_fbo[0])
        glBindTexture(GL_TEXTURE_2D, tex_brightpass)
        glViewport(0, 0, self.height, self.width)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        glBindFramebuffer(GL_FRAMEBUFFER, filter_fbo[1])
        glBindTexture(GL_TEXTURE_2D, tex_filter[0])
        glViewport(0, 0, self.width, self.height)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        glUseProgram(program_resolve)

        glUniform1f(uniforms.resolve.exposure, exposure)

        if (show_prefilter):
            glUniform1f(uniforms.resolve.bloom_factor, 0.0)
            glUniform1f(uniforms.resolve.scene_factor, 1.0)

        else:
            glUniform1f(uniforms.resolve.bloom_factor, bloom_factor if show_bloom else 0.0)
            glUniform1f(uniforms.resolve.scene_factor, 1.0 if show_scene else  0.0 )


        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, tex_filter[1])
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, tex_brightpass if show_prefilter else tex_scene)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)


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
    w1 = glutCreateWindow('OpenGL SuperBible - HDR Bloom')
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