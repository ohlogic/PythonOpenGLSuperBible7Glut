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

view_program = GLuint(0)
filter_program = GLuint(0)
display_program = GLuint(0)

class uniforms_:
    class dof:
        focal_distance = GLint(0)
        focal_depth = GLint(0)
    class view:
        mv_matrix = GLint(0)
        proj_matrix = GLint(0)
        full_shading = GLint(0)
        diffuse_albedo = GLint(0)

uniforms = uniforms_()

depth_fbo = GLuint(0)
depth_tex = GLuint(0)
color_tex = GLuint(0)
temp_tex = GLuint(0)

OBJECT_COUNT = 5
FBO_SIZE              =  2048
FRUSTUM_DEPTH         =  1000

class objects_:
    def __init__(self):
        self.obj = SBMObject()
        self.model_matrix =  (GLfloat * 16)(*identityMatrix)
        self.diffuse_albedo =  (GLfloat * 16)(*identityMatrix)

objects = [objects_() for _ in range(OBJECT_COUNT)]

camera_view_matrix = (GLfloat * 16)(*identityMatrix)
camera_proj_matrix = (GLfloat * 16)(*identityMatrix)

quad_vao = GLuint(0)

paused = False

focal_distance = 40.0
focal_depth = 50.0



def load_shaders():
    global view_program
    global display_program
    global filter_program
    
    shaders = [GLuint(0) for _ in range(4)]

    shaders[0] = shader_load("render.vs.glsl", GL_VERTEX_SHADER)
    shaders[1] = shader_load("render.fs.glsl", GL_FRAGMENT_SHADER)

    if (view_program):
        glDeleteProgram(view_program)

    view_program = link_from_shaders(shaders, 2, True)

    uniforms.view.proj_matrix = glGetUniformLocation(view_program, "proj_matrix")
    uniforms.view.mv_matrix = glGetUniformLocation(view_program, "mv_matrix")
    uniforms.view.full_shading = glGetUniformLocation(view_program, "full_shading")
    uniforms.view.diffuse_albedo = glGetUniformLocation(view_program, "diffuse_albedo")

    shaders[0] = shader_load("display.vs.glsl", GL_VERTEX_SHADER)
    shaders[1] = shader_load("display.fs.glsl", GL_FRAGMENT_SHADER)

    if (display_program):
        glDeleteProgram(display_program)

    display_program = link_from_shaders(shaders, 2, True)

    uniforms.dof.focal_distance = glGetUniformLocation(display_program, "focal_distance")
    uniforms.dof.focal_depth = glGetUniformLocation(display_program, "focal_depth")

    shaders[0] = shader_load("gensat.cs.glsl", GL_COMPUTE_SHADER)

    if (filter_program):
        glDeleteProgram(filter_program)

    filter_program = link_from_shaders(shaders, 1, True)



class Scene:

    def __init__(self, width, height):
        
        global quad_vao
        global temp_tex
        global color_tex
        global depth_tex
        global depth_fbo
        global objects
        
        self.width = width
        self.height = height
        
        load_shaders()

        object_names = [
        
            "dragon.sbm",
            "sphere.sbm",
            "cube.sbm",
            "cube.sbm",
            "cube.sbm"
        ]

        object_colors = [ 
        
            [1.0, 0.7, 0.8, 1.0],
            [0.7, 0.8, 1.0, 1.0],
            [0.3, 0.9, 0.4, 1.0],
            [0.6, 0.4, 0.9, 1.0],
            [0.8, 0.2, 0.1, 1.0],
        ]

        for i in range(0, OBJECT_COUNT):
            objects[i].obj.load(object_names[i])
            objects[i].diffuse_albedo = object_colors[i]

        glGenFramebuffers(1, depth_fbo)
        glBindFramebuffer(GL_FRAMEBUFFER, depth_fbo)

        depth_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, depth_tex)
        glTexStorage2D(GL_TEXTURE_2D, 11, GL_DEPTH_COMPONENT32F, FBO_SIZE, FBO_SIZE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        color_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, color_tex)
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA32F, FBO_SIZE, FBO_SIZE)

        temp_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, temp_tex)
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA32F, FBO_SIZE, FBO_SIZE)

        glFramebufferTexture(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, depth_tex, 0)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, color_tex, 0)

        glBindTexture(GL_TEXTURE_2D, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glEnable(GL_DEPTH_TEST)

        glGenVertexArrays(1, quad_vao)
        glBindVertexArray(quad_vao)

        overlay.init(80, 50)
        overlay.clear()
        overlay.drawText("Q: Increase focal distance", 0, 0)
        overlay.drawText("A: Decrease focal distance", 0, 1)
        overlay.drawText("W: Increase focal depth", 0, 2)
        overlay.drawText("S: Decrease focal depth", 0, 3)
        overlay.drawText("P: Pause", 0, 4)



    def display(self):
    
        global camera_view_matrix
        global camera_proj_matrix
        global objects
        
        currentTime = time.time()


        zeros = [ 0.0, 0.0, 0.0, 0.0 ]
        
        last_time = 0.0
        total_time = 0.0

        if (not paused):
            total_time += (currentTime - last_time)
        last_time = currentTime

        f = total_time + 30.0

        view_position = [0.0, 0.0, 40.0]

        camera_proj_matrix = (GLfloat * 16)(*identityMatrix)
        camera_proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 2.0, 300.0)


        camera_view_matrix = (GLfloat * 16)(*identityMatrix)
        camera_view_matrix = m3dLookAt(view_position,
                                [0.0,0.0,0.0], 
                                [0.0, 1.0, 0.0])


        T1 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T1, 5.0, 0.0, 20.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(14.5), 0.0, 1.0, 0.0)

        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, m3dDegToRad(20.0), 1.0, 0.0, 0.0)

        T2 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T2, 0.0, -4.0, 0.0)

        model_matrix = (GLfloat * 16)(*identityMatrix)
        model_matrix = m3dMultiply(T1, m3dMultiply(RY, m3dMultiply(RX, T2)) )
        
        objects[0].model_matrix = model_matrix



        T1 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T1, -5.0, 0.0, 0.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(14.5), 0.0, 1.0, 0.0)

        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, m3dDegToRad(20.0), 1.0, 0.0, 0.0)

        T2 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T2, 0.0, -4.0, 0.0)

        model_matrix = (GLfloat * 16)(*identityMatrix)
        model_matrix = m3dMultiply(T1, m3dMultiply(RY, m3dMultiply(RX, T2)) )
        
        objects[1].model_matrix = model_matrix



        T1 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T1, -15.0, 0.0, 0.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(14.5), 0.0, 1.0, 0.0)

        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, m3dDegToRad(20.0), 1.0, 0.0, 0.0)

        T2 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T2, 0.0, -4.0, 0.0)

        model_matrix = (GLfloat * 16)(*identityMatrix)
        model_matrix = m3dMultiply(T1, m3dMultiply(RY, m3dMultiply(RX, T2)) )
        
        objects[2].model_matrix = model_matrix




        T1 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T1, -25.0, 0.0, -40.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(14.5), 0.0, 1.0, 0.0)

        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, m3dDegToRad(20.0), 1.0, 0.0, 0.0)

        T2 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T2, 0.0, -4.0, 0.0)

        model_matrix = (GLfloat * 16)(*identityMatrix)
        model_matrix = m3dMultiply(T1, m3dMultiply(RY, m3dMultiply(RX, T2)) )
        
        objects[3].model_matrix = model_matrix



        T1 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T1, -35.0, 0.0, -60.0)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(14.5), 0.0, 1.0, 0.0)

        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, f * m3dDegToRad(20.0), 1.0, 0.0, 0.0)

        T2 = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T2, 0.0, -4.0, 0.0)

        model_matrix = (GLfloat * 16)(*identityMatrix)
        model_matrix = m3dMultiply(T1, m3dMultiply(RY, m3dMultiply(RX, T2)) )
        
        objects[4].model_matrix = model_matrix


        glEnable(GL_DEPTH_TEST)
        self.render_scene(total_time)

        glUseProgram(filter_program)

        glBindImageTexture(0, color_tex, 0, GL_FALSE, 0, GL_READ_ONLY, GL_RGBA32F)
        glBindImageTexture(1, temp_tex, 0, GL_FALSE, 0, GL_WRITE_ONLY, GL_RGBA32F)

        glDispatchCompute(self.height, 1, 1)

        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        glBindImageTexture(0, temp_tex, 0, GL_FALSE, 0, GL_READ_ONLY, GL_RGBA32F)
        glBindImageTexture(1, color_tex, 0, GL_FALSE, 0, GL_WRITE_ONLY, GL_RGBA32F)

        glDispatchCompute(self.width, 1, 1)

        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, color_tex)
        glDisable(GL_DEPTH_TEST)
        glUseProgram(display_program)
        glUniform1f(uniforms.dof.focal_distance, focal_distance)
        glUniform1f(uniforms.dof.focal_depth, focal_depth)
        glBindVertexArray(quad_vao)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        overlay.draw()




        glutSwapBuffers()


    def render_scene(self, currentTime):
        global view_program

        ones = [ 1.0 ]
        zero = [ 0.0 ]
        gray = [ 0.1, 0.1, 0.1, 0.0 ]
        attachments = [ GL_COLOR_ATTACHMENT0 ]
        scale_bias_matrix = [[0.5, 0.0, 0.0, 0.0],
                             [0.0, 0.5, 0.0, 0.0],
                             [0.0, 0.0, 0.5, 0.0],
                             [0.5, 0.5, 0.5, 1.0]]

        glBindFramebuffer(GL_FRAMEBUFFER, depth_fbo)

        glDrawBuffers(1, attachments)
        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, gray)
        glClearBufferfv(GL_DEPTH, 0, ones)
        glUseProgram(view_program)
        
        glUniformMatrix4fv(uniforms.view.proj_matrix, 1, GL_FALSE, camera_proj_matrix)

        glClearBufferfv(GL_DEPTH, 0, ones)

        for i in range (0, OBJECT_COUNT):
            glUniformMatrix4fv(uniforms.view.mv_matrix, 1, GL_FALSE, m3dMultiply(camera_view_matrix , objects[i].model_matrix))
            glUniform3fv(uniforms.view.diffuse_albedo, 1, objects[i].diffuse_albedo)
            objects[0].obj.render()

        glBindFramebuffer(GL_FRAMEBUFFER, 0)



    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global focal_distance
        global focal_depth
        global paused
        
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
        elif key == b'q' or key == b'Q':
            focal_distance *= 1.1;
        elif key == b'a' or key == b'A':
            focal_distance /= 1.1;
        elif key == b'w' or key == b'W':
            focal_depth *= 1.1;
        elif key == b's' or key == b'S':
            focal_depth /= 1.1;
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

    #glutInitContextVersion(4,1)
    #glutInitContextProfile(GLUT_CORE_PROFILE)    
    
    w1 = glutCreateWindow('OpenGL SuperBible - Depth Of Field')
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
