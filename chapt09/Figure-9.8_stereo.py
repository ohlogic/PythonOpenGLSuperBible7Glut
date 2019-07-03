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

view_program = GLuint(0)
show_light_depth_program = GLint(0)


class UNIFORMS_:

    class light:
        mvp = GLint(0)
    
    class view:
        mv_matrix = GLint(0)
        proj_matrix = GLint(0)
        shadow_matrix = GLint(0)
        full_shading = GLint(0)
        specular_albedo = GLint(0)
        diffuse_albedo = GLint(0)

uniforms = UNIFORMS_()

OBJECT_COUNT = 4

class OBJECTS_:
    def __init__(self):
        self.obj = SBMObject()
        self.model_matrix = glm.mat4
        
objects = [OBJECTS_() for _ in range(OBJECT_COUNT) ]

light_view_matrix = glm.mat4
light_proj_matrix = glm.mat4

camera_view_matrix = [glm.mat4 for _ in range(2) ]
camera_proj_matrix = glm.mat4

quad_vao = GLuint(0)

separation = 0.0

RENDER_FULL =0
RENDER_LIGHT = 1
RENDER_DEPTH = 2

paused = False
mode = 0

def glm_mat4x4_to_list(a):
    #aa = []
    #for i, e in enumerate(a):
    #    for j, ee in enumerate(e):
    #        aa.append(ee)

    #return aa

    aa = np.empty([len(a)*4], dtype='float32')
    for i, e in enumerate(aa):
        aa[i] = e
    return aa
    
def load_shaders():
    global view_program
    global uniforms

    vs = shader_load("stereo-render.vs.glsl", GL_VERTEX_SHADER);
    fs = shader_load("stereo-render.fs.glsl", GL_FRAGMENT_SHADER);

    if (view_program):
        glDeleteProgram(view_program)

    view_program = glCreateProgram()
    glAttachShader(view_program, vs)
    glAttachShader(view_program, fs)
    glLinkProgram(view_program)

    glDeleteShader(vs)
    glDeleteShader(fs)

    uniforms.view.proj_matrix = glGetUniformLocation(view_program, "proj_matrix");
    uniforms.view.mv_matrix = glGetUniformLocation(view_program, "mv_matrix");
    uniforms.view.shadow_matrix = glGetUniformLocation(view_program, "shadow_matrix");
    uniforms.view.full_shading = glGetUniformLocation(view_program, "full_shading");
    uniforms.view.specular_albedo = glGetUniformLocation(view_program, "specular_albedo");
    uniforms.view.diffuse_albedo = glGetUniformLocation(view_program, "diffuse_albedo");



class Scene:
    class flags:
        fullscreen=0
        stereo=0
        
    def __init__(self, width, height):
        global objects
        global quad_vao
        
        
        self.width = width
        self.height = height
        self.flags.fullscreen = 0
        self.flags.stereo = 1

        
        load_shaders()

        object_names = [
            "cube.sbm",
            "sphere.sbm",
            "dragon.sbm",
            "torus.sbm"
        ]
        
        for i in range(0, OBJECT_COUNT):
            objects[i].obj.load(object_names[i]);

        glEnable(GL_DEPTH_TEST)
        

        glGenVertexArrays(1, quad_vao)
        glBindVertexArray(quad_vao)
        

    
    def render_scene(self, currentTime):
        global light_proj_matrix

        ones = [ 1.0 ]
        zero = [ 0.0 ]
        gray = [ 0.1, 0.1, 0.1, 0.0 ]
        scale_bias_matrix = [0.5, 0.0, 0.0, 0.0,
                            0.0, 0.5, 0.0, 0.0,
                            0.0, 0.0, 0.5, 0.0,
                            0.5, 0.5, 0.5, 1.0]
                                                     
        light_proj_matrix = glm_mat4x4_to_list(light_proj_matrix)
                                           
        light_vp_matrix = m3dMultiply(light_proj_matrix , light_view_matrix)
        shadow_sbpv_matrix = m3dMultiply(scale_bias_matrix , light_vp_matrix )

        glViewport(0, 0, self.width, self.height)
        glClearBufferfv(GL_COLOR, 0, gray)
        glUseProgram(view_program)
        glActiveTexture(GL_TEXTURE0)
        glUniformMatrix4fv(uniforms.view.proj_matrix, 1, GL_FALSE, camera_proj_matrix)
        glDrawBuffer(GL_BACK)


        diffuse_colors = [
        
            1.0, 0.6, 0.3,
            0.2, 0.8, 0.9,
            0.3, 0.9, 0.4,
            0.5, 0.2, 1.0
        ]
        
        for j in range(0, 2):
            buffs = [ GL_BACK_LEFT, GL_BACK_RIGHT ]
            glDrawBuffer(GL_BACK_LEFT)
            glClearBufferfv(GL_COLOR, 0, gray)
            glClearBufferfv(GL_DEPTH, 0, ones)
            
            for i in range( 0, 4):

                model_matrix = objects[i].model_matrix;
                shadow_matrix = m3dMultiply(shadow_sbpv_matrix , model_matrix)
                glUniformMatrix4fv(uniforms.view.shadow_matrix, 1, GL_FALSE, shadow_matrix)
                glUniformMatrix4fv(uniforms.view.mv_matrix, 1, GL_FALSE, m3dMultiply(camera_view_matrix[j] , objects[i].model_matrix) )
                
                glUniform1i(uniforms.view.full_shading, 1 if mode == RENDER_FULL else 0)
                
                glUniform3fv(uniforms.view.diffuse_albedo, 1, diffuse_colors[i])
                objects[i].obj.render()
                

    def display(self):
        global light_proj_matrix
        global light_view_matrix
        global camera_proj_matrix
        global camera_view_matrix
        
        currentTime = time.time()


        zeros = [ 0.0, 0.0, 0.0, 0.0 ]
        
        last_time = 0.0
        total_time = 0.0

        if (not paused):
            total_time += (currentTime - last_time)
        last_time = currentTime

        f = float(total_time + 30.0)

        light_position = [20.0, 20.0, 20.0]
        view_position = [0.0, 0.0, 40.0]

        light_proj_matrix = glm.frustum(-1.0, 1.0, -1.0, 1.0, 1.0, 200.0)

        light_view_matrix = (GLfloat * 16)(*identityMatrix)
        light_view_matrix = m3dLookAt(light_position,
                                (0.0, 0.0, 0.0), 
                                (0.0, 1.0, 0.0))

        camera_proj_matrix = (GLfloat * 16)(*identityMatrix)
        camera_proj_matrix = m3dPerspective(m3dDegToRad(50.0), float(self.width) / float(self.height), 1.0, 200.0)                               
                                                
                                                
        camera_view_matrix[0] = (GLfloat * 16)(*identityMatrix)
        camera_view_matrix[0] = m3dLookAt(view_position - glm.vec3(separation, 0.0, 0.0),
                                (0.0, 0.0, -50.0), 
                                (0.0, 1.0, 0.0))


        camera_view_matrix[1] = (GLfloat * 16)(*identityMatrix)
        camera_view_matrix[1] = m3dLookAt(view_position - glm.vec3(separation, 0.0, 0.0),
                                (0.0, 0.0, -50.0), 
                                (0.0, 1.0, 0.0))



        objects[0].model_matrix = (GLfloat * 16)(*identityMatrix)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * 14.5, 0.0, 1.0, 0.0)
           
        RX = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RX, 20.0, 1.0, 0.0, 0.0)
        
        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, 0.0, -4.0, 0.0) 
        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(RY, m3dMultiply(RX, T))
        
        objects[0].model_matrix = mv_matrix


        objects[1].model_matrix = (GLfloat * 16)(*identityMatrix)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * 3.7, 0.0, 1.0, 0.0)
           
        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, sin(f * 0.37) * 12.0, cos(f * 0.37) * 12.0, 0.0) 
        
        S = (GLfloat * 16)(*identityMatrix)
        S = scale(2.0)
        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(RY, m3dMultiply(T, S))
        
        objects[1].model_matrix = mv_matrix



        objects[2].model_matrix = (GLfloat * 16)(*identityMatrix)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * 6.45, 0.0, 1.0, 0.0)

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, sin(f * 0.25) * 10.0, cos(f * 0.25) * 10.0, 0.0) 
        
        RZ = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RZ, f * 99.0, 0.0, 0.0, 1.0)

        S = (GLfloat * 16)(*identityMatrix)
        S = scale(2.0)
        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(RY, m3dMultiply(T, m3dMultiply(RZ, S)))
        
        objects[2].model_matrix = mv_matrix


        objects[3].model_matrix = (GLfloat * 16)(*identityMatrix)

        RY = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RY, f * 5.25, 0.0, 1.0, 0.0)

        T = (GLfloat * 16)(*identityMatrix)
        m3dTranslateMatrix44(T, sin(f * 0.51) * 14.0, cos(f * 0.51) * 14.0, 0.0) 
        
        RDOUBLE = (GLfloat * 16)(*identityMatrix)
        m3dRotationMatrix44(RDOUBLE, f * 120.3, 0.707106, 0.0, 0.707106)
        
        S = (GLfloat * 16)(*identityMatrix)
        S = scale(2.0)
        
        mv_matrix = (GLfloat * 16)(*identityMatrix)
        mv_matrix = m3dMultiply(RY, m3dMultiply(T, m3dMultiply(RDOUBLE, S)))

        objects[3].model_matrix = mv_matrix

        glEnable(GL_DEPTH_TEST)

        self.render_scene(total_time)

        glutSwapBuffers()


    def reshape(self, width, height):
        self.width = width
        self.height = height

    def keyboard(self, key, x, y ):
        global fullscreen
        global mode 
        global separation
        
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
            mode = RENDER_FULL
        elif key == b'2':
            mode = RENDER_LIGHT
        elif key == b'3':
            mode = RENDER_DEPTH
        elif key == b'z' or key == 'Z':
            separation += 0.05
        elif key == b'x' or key == 'X':
            separation -= 0.05
        elif key == b'r' or key == 'R':
            load_shaders()
        
    def init(self):
        pass

    def timer(self, blah):
        glutPostRedisplay()
        glutTimerFunc( int(1/60), self.timer, 0)
        time.sleep(1/60.0)

if __name__ == '__main__':
    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH) # glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH | GLUT_STEREO)
    glutInitWindowSize(512, 512)
    w1 = glutCreateWindow('OpenGL SuperBible - Texture Coordinates')
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
