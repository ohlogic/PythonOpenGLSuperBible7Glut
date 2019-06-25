import sys
import time 
import os
import time
import math
import ctypes

currentWDir = os.getcwd()
print( 'current working directory: {}'.format( str(currentWDir) ) )
fileDir = os.path.dirname(os.path.abspath(__file__)) # det the directory of this file
print( 'current location of self: {}'.format( str(fileDir) ) )
parentDir = os.path.abspath(os.path.join(fileDir, os.pardir)) # get the parent directory of this file
sys.path.insert(0, parentDir)
print( 'insert system directory: {}'.format( str(parentDir) ) )
os.chdir( fileDir )
baseWDir = os.getcwd()
print( 'changed current working directory: {}'.format( str(baseWDir) ) )
print ( '' )

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

def SB6M_FOURCC(a,b,c,d):
    return ( (ord(a) << 0) | (ord(b) << 8) | (ord(c) << 16) | (ord(d) << 24) )

SB6M_MAGIC = SB6M_FOURCC('S','B','6','M')

SB6M_CHUNK_TYPE_INDEX_DATA      = SB6M_FOURCC('I','N','D','X')
SB6M_CHUNK_TYPE_VERTEX_DATA     = SB6M_FOURCC('V','R','T','X')
SB6M_CHUNK_TYPE_VERTEX_ATTRIBS  = SB6M_FOURCC('A','T','R','B')
SB6M_CHUNK_TYPE_SUB_OBJECT_LIST = SB6M_FOURCC('O','L','S','T')
SB6M_CHUNK_TYPE_COMMENT         = SB6M_FOURCC('C','M','N','T')
SB6M_CHUNK_TYPE_DATA            = SB6M_FOURCC('D','A','T','A')

class SB6M_HEADER:
    def __init__(self, data):
        int_data = np.frombuffer(np.array(data[:16], dtype=np.byte), dtype=np.uint32)
        self.magic, self.size, self.num_chunks, self.flags = int_data 
        print(self.magic, self.size, self.num_chunks, self.flags)

class SB6M_CHUNK_HEADER:
    def __init__(self, data, offset):
        int_data = np.frombuffer(np.array(data[offset:offset+8], dtype=np.byte), dtype=np.uint32)
        self.type, self.size = int_data

class SB6M_CHUNK_INDEX_DATA(SB6M_CHUNK_HEADER):
     def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+20], dtype=np.byte), dtype=np.uint32)
        self.index_type, self.index_count, self.index_data_offset = int_data

class SB6M_CHUNK_VERTEX_DATA(SB6M_CHUNK_HEADER):
     def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+20], dtype=np.byte), dtype=np.uint32)
        self.data_size, self.data_offset, self.total_vertices = int_data

class SB6M_CHUNK_VERTEX_DATA(SB6M_CHUNK_HEADER):
     def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+20], dtype=np.byte), dtype=np.uint32)
        self.data_size, self.data_offset, self.total_vertices = int_data

SB6M_VERTEX_ATTRIB_FLAG_NORMALIZED = 0x00000001
SB6M_VERTEX_ATTRIB_FLAG_INTEGER    = 0x00000002

class SB6M_VERTEX_ATTRIB_DECL:
    def __init__(self, data, offset):
        self.name = ''.join([chr(n) for n in data[offset:offset+64] if n > 30])
        int_data = np.frombuffer(np.array(data[offset+64:offset+84], dtype=np.byte), dtype=np.uint32)
        self.size, self.type, self.stride, self.flags, self.data_offset = int_data

class SB6M_VERTEX_ATTRIB_CHUNK(SB6M_CHUNK_HEADER):
    def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+12], dtype=np.byte), dtype=np.uint32)
        self.attrib_count = int_data[0]
        self.attrib_data = []
        for i in range(self.attrib_count):
            self.attrib_data.append(SB6M_VERTEX_ATTRIB_DECL(data, offset+12+i*84))

class SB6M_DATA_CHUNK(SB6M_CHUNK_HEADER):
    def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+20], dtype=np.byte), dtype=np.uint32)
        self.encoding, self.data_offset, self.data_length = int_data

class SB6M_SUB_OBJECT_DECL:
    def __init__(self, data, offset):
        int_data = np.frombuffer(np.array(data[offset:offset+8], dtype=np.byte), dtype=np.uint32)
        self.first, self.count = int_data

class SB6M_CHUNK_SUB_OBJECT_LIST(SB6M_CHUNK_HEADER):
    def __init__(self, data, offset):
        super().__init__(data, offset)
        int_data = np.frombuffer(np.array(data[offset+8:offset+12], dtype=np.byte), dtype=np.uint32)
        self.count = int_data[0]
        self.sub_object = []
        for i in range(self.count):
            self.sub_object.append(SB6M_SUB_OBJECT_DECL(data, offset+12+i*8))

class SB6M_CHUNK_HEADER_:
    chunk_type = 0
    chunk_name = ''
    size = 0

class SB6M_DATA_ENCODING:
    SB6M_DATA_ENCODING_RAW  = 0


class SB6M_CHUNK_COMMENT:
    header = SB6M_CHUNK_HEADER_()
    comment = []
    comment.append('')
    comment.append('')


# data_buffer = GLuint(0)
# vao = GLuint(0)
# index_type = GLuint(0)
index_offset = GLuint(0)



def get_sub_object_info(index, first, count):
    if (index >= num_sub_objects):
        first = 0
        count = 0
    else:
        first = sub_object[index].first;
        count = sub_object[index].count;

def render(instance_count = 1, base_instance = 0):
    render_sub_object(0, instance_count, base_instance)


class SBMObject:

    def __init__(self):
        self.vao = GLuint(0)

    def load(self, filename):

        vertex_attrib_chunk = None
        vertex_data_chunk = None
        index_data_chunk = None
        sub_object_chunk = None
        data_chunk = None

        #try:
        data = numpy.fromfile(filename, dtype=np.byte)
        filesize = data.size

        header = SB6M_HEADER(data)
        offset = header.size

        for i in range(header.num_chunks):

            chunk = SB6M_CHUNK_HEADER(data, offset)
            if chunk.type == SB6M_CHUNK_TYPE_VERTEX_ATTRIBS:
                vertex_attrib_chunk = SB6M_VERTEX_ATTRIB_CHUNK(data, offset) 
            elif chunk.type == SB6M_CHUNK_TYPE_VERTEX_DATA:
                vertex_data_chunk = SB6M_CHUNK_VERTEX_DATA(data, offset)
            elif chunk.type == SB6M_CHUNK_TYPE_INDEX_DATA:
                index_data_chunk = SB6M_CHUNK_INDEX_DATA(data, offset) 
            elif chunk.type == SB6M_CHUNK_TYPE_SUB_OBJECT_LIST:
                sub_object_chunk = SB6M_CHUNK_SUB_OBJECT_LIST(data, offset)
            elif chunk.type == SB6M_CHUNK_TYPE_DATA:
                data_chunk = SB6M_DATA_CHUNK(data, offset) 
            else:
                raise

            offset += chunk.size

        #except:
        #    print("error reading file {}".format(filename))

        print("finished reading")

        if vertex_data_chunk and vertex_attrib_chunk:
            start = vertex_data_chunk.data_offset
            end = start + vertex_data_chunk.data_size
            vertex_data = np.frombuffer(np.array(data[start:end], dtype=np.byte), dtype=np.float)

            data_buffer = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, data_buffer)
            glBufferData(GL_ARRAY_BUFFER, vertex_data, GL_STATIC_DRAW)

            self.vertexcount = vertex_data_chunk.total_vertices
            self.vao = glGenVertexArrays(1)
            glBindVertexArray(self.vao)

            for attrib_i, attrib in enumerate(vertex_attrib_chunk.attrib_data):
                if attrib.name=='position' or attrib.name=='map1': 
                    glVertexAttribPointer(attrib_i,
                        attrib.size, attrib.type,
                        GL_TRUE if (attrib.flags & SB6M_VERTEX_ATTRIB_FLAG_NORMALIZED) != 0 else GL_FALSE,
                        attrib.stride, ctypes.c_void_p(int(attrib.data_offset)))
                    glEnableVertexAttribArray(attrib_i)

    def render(self):

        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.vertexcount)

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

M3D_PI = 3.14159265358979323846
M3D_PI_DIV_180 = M3D_PI / 180.0
M3D_INV_PI_DIV_180 = 57.2957795130823229

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


        # way # 1 - works
        # T = translate(0.0, 0.0, -4.0).reshape(4,4)
        # RX = np.array(rotation_matrix( [1.0, 0.0, 0.0], currentTime * m3dDegToRad(17.0)))
        # RY = np.array(rotation_matrix( [0.0, 1.0, 0.0], currentTime * m3dDegToRad(13.0)))
        # mv_matrix = np.matmul(np.matmul(RY, RX), T)


        # way # 2 - works !!
        m3dTranslateMatrix44(T, 0, 0, -4)
        m3dRotationMatrix44(RX, currentTime * m3dDegToRad(17.0), 1.0, 0.0, 0.0)
        m3dRotationMatrix44(RY, currentTime * m3dDegToRad(13.0), 0.0, 1.0, 0.0)

        # way # 2 - option A   works!
        # Matrix multiplication is not commutative, order matters when multiplying matrices
        R = m3dMultiply(RY, RX) 
        mv_matrix = m3dMultiply(T, R)

        # way # 2 - option B    works!
        # T = np.matrix(T).reshape(4,4)
        # mv_matrix = np.matmul(np.matmul(np.matrix(RY).reshape(4,4), np.matrix(RX).reshape(4,4)).reshape(4,4), T)


        # way # 3 - works also
        # T  = np.matrix(translate(0.0, 0.0, -4.0)).reshape(4,4)
        # RX = np.matrix(rotation_matrix( [1.0, 0.0, 0.0], currentTime * m3dDegToRad(17.0)))
        # RY = np.matrix(rotation_matrix( [0.0, 1.0, 0.0], currentTime * m3dDegToRad(13.0)))
        # mv_matrix = RX * RY * T


        proj_matrix = (GLfloat * 16)(*identityMatrix)
        proj_matrix = m3dPerspective(m3dDegToRad(60.0), float(self.width) / float(self.height), 0.1, 100.0);    

        glUniformMatrix4fv(uniforms_mv_matrix, 1, GL_FALSE, mv_matrix);
        glUniformMatrix4fv(uniforms_proj_matrix, 1, GL_FALSE, proj_matrix);

        myobject.render()
        #gltDrawTorus(0.35, 0.15, 40, 20)

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