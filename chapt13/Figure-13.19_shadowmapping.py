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

DEPTH_TEXTURE_SIZE = 4096
FRUSTUM_DEPTH = 1000

light_program = GLuint(0)
view_program = GLuint(0)
show_light_depth_program = GLint(0) 

class uniforms_:
    class light:
        mvp = GLint(0)
    class view:
        mv_matrix = GLint(0)
        proj_matrix = GLint(0)
        shadow_matrix = GLint(0)
        full_shading = GLint(0)

uniforms = uniforms_()

depth_fbo = GLuint(0)
depth_tex = GLuint(0)
depth_debug_tex = GLuint(0)

OBJECT_COUNT = 4

class objects_:
    def __init__(self):
        self.obj = SBMObject()
        self.model_matrix = (GLfloat * 16)(*identityMatrix)

objects = [objects_() for _ in range(OBJECT_COUNT)]

light_view_matrix = (GLfloat * 16)(*identityMatrix)
light_proj_matrix = (GLfloat * 16)(*identityMatrix)

camera_view_matrix = (GLfloat * 16)(*identityMatrix)
camera_proj_matrix = (GLfloat * 16)(*identityMatrix)

quad_vao = GLuint(0)

RENDER_FULL = 0
RENDER_LIGHT = 1
RENDER_DEPTH = 2

mode = RENDER_FULL

paused = False



def glm_mat4x4_to_list(a):
    # aa = []
    # for i, e in enumerate(a):
       # for j, ee in enumerate(e):
           # aa.append(ee)

    # return (GLfloat * 16)(*aa)

    aa = np.empty([len(a)*4], dtype='float32')
    for i, e in enumerate(aa):
        aa[i] = e
    return aa
    


def load_shaders():
    global light_program
    global view_program
    global show_light_depth_program
    global uniforms
    
    vs = shader_load("shadowmapping-light.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("shadowmapping-light.fs.glsl", GL_FRAGMENT_SHADER)

    if (light_program):
        glDeleteProgram(light_program)

    light_program = glCreateProgram()
    glAttachShader(light_program, vs)
    glAttachShader(light_program, fs)
    glLinkProgram(light_program)

    glDeleteShader(vs)
    glDeleteShader(fs)

    uniforms.light.mvp = glGetUniformLocation(light_program, "mvp")

    vs = shader_load("shadowmapping-camera.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("shadowmapping-camera.fs.glsl", GL_FRAGMENT_SHADER)

    if (light_program):
        glDeleteProgram(view_program)

    view_program = glCreateProgram()
    glAttachShader(view_program, vs)
    glAttachShader(view_program, fs)
    glLinkProgram(view_program)

    glDeleteShader(vs)
    glDeleteShader(fs)

    uniforms.view.proj_matrix = glGetUniformLocation(view_program, "proj_matrix")
    uniforms.view.mv_matrix = glGetUniformLocation(view_program, "mv_matrix")
    uniforms.view.shadow_matrix = glGetUniformLocation(view_program, "shadow_matrix")
    uniforms.view.full_shading = glGetUniformLocation(view_program, "full_shading")

    if (show_light_depth_program):
        glDeleteProgram(show_light_depth_program)

    show_light_depth_program = glCreateProgram()

    vs = shader_load("shadowmapping-light-view.vs.glsl", GL_VERTEX_SHADER)
    fs = shader_load("shadowmapping-light-view.fs.glsl", GL_FRAGMENT_SHADER)

    glAttachShader(show_light_depth_program, vs)
    glAttachShader(show_light_depth_program, fs)
    glLinkProgram(show_light_depth_program)

    glDeleteShader(vs)
    glDeleteShader(fs)





class Scene:

    def __init__(self, width, height):
        global depth_fbo
        global objects
        global depth_tex
        global depth_debug_tex
        global quad_vao
        
        load_shaders()

        object_names = [
        
            "dragon.sbm",
            "sphere.sbm",
            "cube.sbm",
            "torus.sbm"
        ]

        for i in range(0, OBJECT_COUNT):
        
            objects[i].obj.load(object_names[i])

        glGenFramebuffers(1, depth_fbo)
        glBindFramebuffer(GL_FRAMEBUFFER, depth_fbo)

        depth_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, depth_tex)
        glTexStorage2D(GL_TEXTURE_2D, 11, GL_DEPTH_COMPONENT32F, DEPTH_TEXTURE_SIZE, DEPTH_TEXTURE_SIZE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_REF_TO_TEXTURE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL)

        glFramebufferTexture(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, depth_tex, 0)

        depth_debug_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, depth_debug_tex)
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_R32F, DEPTH_TEXTURE_SIZE, DEPTH_TEXTURE_SIZE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, depth_debug_tex, 0)

        glBindTexture(GL_TEXTURE_2D, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glEnable(GL_DEPTH_TEST)

        glGenVertexArrays(1, quad_vao)
        glBindVertexArray(quad_vao)


    def display(self):
        global light_proj_matrix
        global light_view_matrix
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

        light_position = (20.0, 20.0, 20.0)
        view_position = (0.0, 0.0, 40.0)

        light_proj_matrix = glm_mat4x4_to_list(glm.frustum(-1.0, 1.0, -1.0, 1.0, 1.0, 200.0))
        
        light_view_matrix = (GLfloat * 16)(*identityMatrix)
        light_view_matrix = m3dLookAt(light_position,
                                     (0.0, 0.0,0.0), 
                                     (0.0, 1.0, 0.0))


        camera_proj_matrix = (GLfloat * 16)(*identityMatrix)
        camera_proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 1.0, 200.0);  
        
        
        camera_view_matrix = (GLfloat * 16)(*identityMatrix)
        camera_view_matrix = m3dLookAt(view_position,
                                     (0.0, 0.0,0.0), 
                                     (0.0, 1.0, 0.0))


        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(14.5), 0.0, 1.0, 0.0)        

        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, m3dDegToRad(20.0), 1.0, 0.0, 0.0)
       
        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, -4.0, 0.0)        
        
        objects[0].model_matrix = m3dMultiply(RY, m3dMultiply(RX, T))
        
        
        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(3.7), 0.0, 1.0, 0.0)  
        
        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, sin(f * 0.37) * 12.0, cos(f * 0.37) * 12.0, 0.0)  
        
        S = (GLfloat * 16)(*identityMatrix)
        S = scale(2.0)

        objects[1].model_matrix = m3dMultiply(RY, m3dMultiply( T, S ))


        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(6.45), 0.0, 1.0, 0.0)  

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, sin(f * 0.25) * 10.0, cos(f * 0.25) * 10.0, 0.0)  

        RZ = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RZ, f * m3dDegToRad(99.0), 0.0, 0.0, 1.0)  
        
        S = (GLfloat * 16)(*identityMatrix)
        S = scale(2.0)
        
        objects[2].model_matrix = m3dMultiply(RY, m3dMultiply(T, m3dMultiply( RZ, S )))
        
        
        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * m3dDegToRad(5.25), 0.0, 1.0, 0.0)  

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, sin(f * 0.51) * 14.0, cos(f * 0.51) * 14.0, 0.0)  

        RZ = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RZ, f * m3dDegToRad(120.3), 0.707106, 0.0, 0.707106)  
        
        S = (GLfloat * 16)(*identityMatrix)
        S = scale(2.0)
        
        objects[3].model_matrix = m3dMultiply(RY, m3dMultiply(T, m3dMultiply( RZ, S )))


        glEnable(GL_DEPTH_TEST)
        self.render_scene(total_time, True)

        if (mode == RENDER_DEPTH):
        
            glDisable(GL_DEPTH_TEST)
            glBindVertexArray(quad_vao)
            glUseProgram(show_light_depth_program)
            glBindTexture(GL_TEXTURE_2D, depth_debug_tex)
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        
        else:
            self.render_scene(total_time, False)
        




        glutSwapBuffers()




    def render_scene(self, currentTime, from_light):

        ones = [ 1.0 ]
        zero = [ 0.0 ]
        gray = [ 0.1, 0.1, 0.1, 0.0 ]
        scale_bias_matrix = [0.5, 0.0, 0.0, 0.0,
                             0.0, 0.5, 0.0, 0.0,
                             0.0, 0.0, 0.5, 0.0,
                             0.5, 0.5, 0.5, 1.0]
        scale_bias_matrix = (GLfloat * 16)(*scale_bias_matrix)
        
        light_vp_matrix = m3dMultiply(light_proj_matrix , light_view_matrix)
        shadow_sbpv_matrix = m3dMultiply(scale_bias_matrix , m3dMultiply(light_proj_matrix , light_view_matrix))

        if (from_light):
        
            glBindFramebuffer(GL_FRAMEBUFFER, depth_fbo)
            glViewport(0, 0, DEPTH_TEXTURE_SIZE, DEPTH_TEXTURE_SIZE)
            glEnable(GL_POLYGON_OFFSET_FILL)
            glPolygonOffset(4.0, 4.0)
            glUseProgram(light_program)
            buffs = [ GL_COLOR_ATTACHMENT0 ]
            glDrawBuffers(1, buffs)
            glClearBufferfv(GL_COLOR, 0, zero)
        
        else:
        
            glViewport(0, 0, self.width, self.height)
            glClearBufferfv(GL_COLOR, 0, gray)
            glUseProgram(view_program)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, depth_tex)
            glUniformMatrix4fv(uniforms.view.proj_matrix, 1, GL_FALSE, camera_proj_matrix)
            glDrawBuffer(GL_BACK)
        

        glClearBufferfv(GL_DEPTH, 0, ones)

        for i in range(0, 4):

            model_matrix = objects[i].model_matrix
            
            if (from_light):

                glUniformMatrix4fv(uniforms.light.mvp, 1, GL_FALSE, m3dMultiply(light_vp_matrix , objects[i].model_matrix))
            
            else:
            

                glUniformMatrix4fv(uniforms.view.shadow_matrix, 1, GL_FALSE, m3dMultiply(shadow_sbpv_matrix , model_matrix))
                glUniformMatrix4fv(uniforms.view.mv_matrix, 1, GL_FALSE, m3dMultiply(camera_view_matrix , objects[i].model_matrix))
                glUniform1i(uniforms.view.full_shading,1 if mode == RENDER_FULL else 0)
            
            objects[i].obj.render()


        if (from_light):
        
            glDisable(GL_POLYGON_OFFSET_FILL)
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
        
        else:
        
            glBindTexture(GL_TEXTURE_2D, 0)


    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global mode 
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
        elif key == b'1':
            mode = RENDER_FULL;
        elif key == b'2':
            mode = RENDER_LIGHT;
        elif key == b'3':
            mode = RENDER_DEPTH;
        elif key == b'r' or key == b'R': 
            load_shaders();
        elif key == b'p' or key == b'P':
            paused = not paused;



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
    
    w1 = glutCreateWindow('OpenGL SuperBible - Shadow Mapping')
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
