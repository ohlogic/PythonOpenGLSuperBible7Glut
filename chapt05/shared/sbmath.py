#!/usr/bin/python3

import sys
import time 
import os
import time
import math
import ctypes
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

M3D_PI = 3.14159265358979323846
M3D_PI_DIV_180 = M3D_PI / 180.0
M3D_INV_PI_DIV_180 = 57.2957795130823229

identityMatrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]


def m3dDegToRad(num):
    return (num * M3D_PI_DIV_180)

def m3dRadToDeg(num):
    return (num * M3D_INV_PI_DIV_180)

# Translate matrix. Only 4x4 matrices supported
def m3dTranslateMatrix44(m, x, y, z):
    m[12] += x
    m[13] += y
    m[14] += z

# Creates a 4x4 rotation matrix, takes radians NOT degrees
def m3dRotationMatrix44(m, angle, x, y, z):
    s = math.sin(angle)
    c = math.cos(angle)
    mag = float((x * x + y * y + z * z) ** 0.5)

    if mag == 0.0:
        m3dLoadIdentity(m)
        return

    x /= mag
    y /= mag
    z /= mag

    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    yz = y * z
    zx = z * x
    xs = x * s
    ys = y * s
    zs = z * s
    one_c = 1.0 - c

    m[0] = (one_c * xx) + c
    m[1] = (one_c * xy) - zs
    m[2] = (one_c * zx) + ys
    m[3] = 0.0

    m[4] = (one_c * xy) + zs
    m[5] = (one_c * yy) + c
    m[6] = (one_c * yz) - xs
    m[7] = 0.0

    m[8] = (one_c * zx) - ys
    m[9] = (one_c * yz) + xs
    m[10] = (one_c * zz) + c
    m[11]  = 0.0

    m[12] = 0.0
    m[13] = 0.0
    m[14] = 0.0
    m[15] = 1.0

def m3dMultiply(A, B):
    C = (GLfloat * 16)(*identityMatrix)
    for k in range(0, 4):
        for j in range(0, 4):
            C[k*4+j] = A[0*4+j] * B[k*4+0] + A[1*4+j] * B[k*4+1] + \
                       A[2*4+j] * B[k*4+2] + A[3*4+j] * B[k*4+3]
    return C

def m3dOrtho(l, r, t, b, n, f):
    return (GLfloat * 16)(
        2/(r-l),      0,            0,            0,
        0,            2/(t-b),      0,            0,
        0,            0,            -2/(f-n),     0,
        -(r+l)/(r-l), -(t+b)/(t-b), -(f+n)/(f-n), 1)

def m3dPerspective(fov_y, aspect, n, f):
    a = aspect
    ta = math.tan( fov_y / 2 )
    return (GLfloat * 16)(
        1/(ta*a),  0,     0,              0,
        0,         1/ta,  0,              0,
        0,         0,    -(f+n)/(f-n),   -1,
        0,         0,    -2*f*n/(f-n),    0)

def rotation_matrix(axis, theta):
    """
    Return the rotation matrix associated with counterclockwise rotation about
    the given axis by theta radians.
    """
    axis = np.asarray(axis)
    axis = axis / math.sqrt(np.dot(axis, axis))
    a = math.cos(theta / 2.0)
    b, c, d = -axis * math.sin(theta / 2.0)
    aa, bb, cc, dd = a * a, b * b, c * c, d * d
    bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
    return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac), 0],
                     [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab), 0],
                     [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc, 0],
                     [0,0,0,1]])

def translate(tx, ty, tz):
    """creates the matrix equivalent of glTranslate"""
    return np.array([1.0, 0.0, 0.0, 0.0, 
                     0.0, 1.0, 0.0, 0.0, 
                     0.0, 0.0, 1.0, 0.0, 
                        tx, ty, tz, 1.0], np.float32)

# Scale matrix. Only 4x4 matrices supported
def m3dScaleMatrix44(m, x, y, z):
    m[0] *= x
    m[5] *= y
    m[10] *= z



def length(v):
    return math.sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])

def normalize(v):
    l = length(v)
    #if (v[0] == 0 and v[1] == 0 and v[2] ==0):
    #    return [0.0, 1/3, 0.0]
    return [v[0]/l, v[1]/l, v[2]/l]
    
def dot(v0, v1):
    return v0[0]*v1[0]+v0[1]*v1[1]+v0[2]*v1[2]

def cross(v0, v1):
    return [
        v0[1]*v1[2]-v1[1]*v0[2],
        v0[2]*v1[0]-v1[2]*v0[0],
        v0[0]*v1[1]-v1[0]*v0[1]]

def m3dLookAt(eye, target, up):
    mz = normalize( (eye[0]-target[0], eye[1]-target[1], eye[2]-target[2]) ) # inverse line of sight
    mx = normalize( cross( up, mz ) )
    my = normalize( cross( mz, mx ) )
    tx =  dot( mx, eye )
    ty =  dot( my, eye )
    tz = -dot( mz, eye )   
    return np.array([mx[0], my[0], mz[0], 0, mx[1], my[1], mz[1], 0, mx[2], my[2], mz[2], 0, tx, ty, tz, 1])

def scale(s):
    return [s,0,0,0, 0,s,0,0, 0,0,s,0, 0,0,0,1]     
    
    