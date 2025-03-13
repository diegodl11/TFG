from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer
from OpenGL.GL import *
import numpy as np
import ctypes
from plyfile import PlyData
from PIL import Image
import os



class PlyViewer(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.texture_path = None
        self.texture= None
        self.window = None
        self.width = 800
        self.height = 600
        self.vertices = None
        self.normals = None
        self.faces = None
        self.colors = None
        self.texcoords = None
        self.VAO = None
        self.VBO = None
        self.VBO_N = None
        self.VBO_C = None
        self.VBO_T = None
        self.EBO = None
        self.shader_program = None
        self.vertexShader = None
        self.fragmentShader = None
        self.texture = None
        self.VERTEX_SHADER = None
        self.FRAGMENT_SHADER = None

        # Variables de la cámara
        self.yaw, self.pitch, self.roll = 0, 0, 0
        self.last_x, self.last_y = None, None
        self.sensitivity = 0.008
        self.radius = 3.0
        self.cam_x, self.cam_y, self.cam_z = 0.0, 0.0, self.radius
        self.mouse_pressed = False
        self.fov = 30.0
        self.aspect = 800 / 600
        self.near = 2.0
        self.far = 50.0

        self.zoom_sensitivity = 2.0
        self.first_click = True
        self.view = None
        self.model = np.eye(4, dtype=np.float32)
        self.lightPos = np.array([0.0, 1.0, 3.0], dtype=np.float32)  # Antes estaba en (1.2, 1.0, 2.0)
        self.lightColor = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.objectColor = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        #rotaciones de la camara. Definimos la de z por si quiero implementar esa funcionalidad
        self.rotacion_y = None
        self.rotacion_x = None
        self.rotacion_z = None
        
        # Configurar un temporizador para refrescar la pantalla (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)  # `update()` llama automáticamente a `paintGL()`
        self.timer.start(1)  # Aproximadamente 60 FPS

    def perspective_matrix(self, fov, aspect, near, far):
        f = 1.0 / np.tan(np.radians(fov) / 2.0)
        return np.array([
            [f/aspect, 0,  0,                              0],
            [0,        f,  0,                              0],
            [0,        0, (far+near)/(near-far), (2*far*near)/(near-far)],
            [0,        0, -1,                              0]
        ], dtype=np.float32)
    def look_at(self, eye, target, up):
        f = target - eye
        f /= np.linalg.norm(f)
        u = up / np.linalg.norm(up)
        s = np.cross(f, u)
        s /= np.linalg.norm(s)
        u = np.cross(s, f)

        view = np.eye(4, dtype=np.float32)
        view[:3, 0] = s
        view[:3, 1] = u
        view[:3, 2] = -f
        view[:3, 3] = -eye @ np.array([s, u, -f])  # Traslación

        return view.astype(np.float32)
    def initializeGL(self):
        
        glEnable(GL_DEPTH_TEST)  # Habilita el buffer de profundidad
        glClearColor(0.1, 0.1, 0.1, 1.0)  # Fondo gris oscuro
        glViewport(0, 0, self.width, self.height)
       
        glDisable(GL_CULL_FACE)  # Desactiva eliminación de caras por si afecta a la visibilidad
        #tamaño de los puntos
        glEnable(GL_PROGRAM_POINT_SIZE)

        glPointSize(3.0)  # Ajustar a un tamaño visible
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)  # Renderizar solo en líneas (wireframe)
        
        
        
        

    def resizeGL(self, width, height):
        """Se ejecuta cuando la ventana cambia de tamaño"""
        glViewport(0, 0, width, height)

    def wheelEvent(self, event):
        """Hace zoom cuando el usuario usa la rueda del ratón."""
        delta = event.angleDelta().y() / 120  # Normalizar el desplazamiento de la rueda
        self.fov -= delta * self.zoom_sensitivity
        self.fov = np.clip(self.fov, 10.0, 90.0)  # Limitar el zoom
        self.update()  # ⚡ Refrescar la escena

    def mousePressEvent(self, event):
        """Detecta cuándo el usuario presiona un botón del ratón."""
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = True
            self.first_click = True  # Indica que es el primer clic para evitar saltos
            self.last_x = event.x()
            self.last_y = event.y()

    def mouseReleaseEvent(self, event):
        """Detecta cuándo el usuario suelta el botón del ratón."""
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = False

    def mouseMoveEvent(self, event):
        """Mueve la cámara cuando el usuario arrastra el ratón."""
        if not self.mouse_pressed:
            return  # No hacer nada si el botón del ratón no está presionado

        if self.first_click:
            self.last_x, self.last_y = event.x(), event.y()
            self.first_click = False
            return

        dx = event.x() - self.last_x
        dy = event.y() - self.last_y

        self.yaw += dx * self.sensitivity
        self.pitch += dy * self.sensitivity * abs(np.cos(np.radians(self.yaw)))
        self.pitch = np.clip(self.pitch, -89.0, 89.0)  # Limitar la inclinación

        self.last_x, self.last_y = event.x(), event.y()
        self.update()  #  Refrescar la escena con la nueva rotación   

    #para limpiar el fondo en caso de usar el boton hacia atras hasta el final
    def clear_background(self):
        #con poner los vértices a None es suficiente porque así no entra en el bucle de dibujado
        self.vertices = None
        self.update()       # Fuerza el redibujado de la ventana
    
    #cargar atributos de malals de la pila
    def load_attributes(self, vertex, normals, colors, faces, texcoords, texture_path):
        self.texture = None
        self.vertices = vertex
        self.normals = normals
        self.colors = colors
        self.faces = faces
        self.texcoords = texcoords
        self.texture_path = texture_path
        #en caso de que esa malla tenga textura inicailizarla
        if self.texture_path:
            self.load_texture()
        self.init_opengl() 
        self.load_shaders()
        
        self.update()
    def load_shaders(self):
        
        if self.texcoords is not None:
            
            self.VERTEX_SHADER="""
            #version 330 core
            layout (location = 0) in vec3 position;
            
            layout (location = 2) in vec3 color;
            layout (location = 3) in vec2 texCoord;

            out vec3 vertexColor;
            out vec2 TexCoord;

            uniform mat4 transform;

            void main() {
                vertexColor = color;
                TexCoord = texCoord;
                gl_Position = transform * vec4(position, 1.0);
            }
            """
            #En caso de que haya una imagen asociada a la malla parametrizada
            if self.texture is not None and getattr(self.colors, "size", 0) == 0:
                
                self.FRAGMENT_SHADER="""
                #version 330 core
                in vec3 vertexColor;
                in vec2 TexCoord;
                out vec4 FragOutput;

                uniform sampler2D texture1;

                void main() {
                    //FragOutput = vec4(TexCoord, 0.0, 1.0);  //Devuelve rojo y verde según las UV
                    
                    FragOutput = texture(texture1, TexCoord); 
                }
                """

            #En caso de que no haya una imagen asociada a la malla parametrizada
            else:
                
                self.FRAGMENT_SHADER="""
                #version 330 core

                in vec3 vertexColor;
                out vec4 FragColor;

                void main() {
                    FragColor = vec4(vertexColor, 1.0);
                }
                """
                
                
        else:
            if getattr(self.colors, "size", 0) == 0 and getattr(self.normals, "size", 0) == 0:
                # Caso 1: Sin normales ni colores (blanco por defecto)
                self.VERTEX_SHADER = """
                #version 330 core
                layout (location = 0) in vec3 position;

                uniform mat4 transform;

                void main() {
                    gl_Position = transform * vec4(position, 1.0);
                }
                """

                self.FRAGMENT_SHADER = """
                #version 330 core
                out vec4 FragColor;

                void main() {
                    FragColor = vec4(1.0, 1.0, 1.0, 1.0); // Blanco
                }
                """

            elif getattr(self.colors, "size", 0) > 0 and getattr(self.normals, "size", 0) == 0:
                # Caso 2: Con colores, sin normales

                self.VERTEX_SHADER = """
                #version 330 core
                layout (location = 0) in vec3 position;
                //importante que coincida con  glEnableVertexAttribArray(2)
                layout (location = 2) in vec3 color;

                out vec3 FragColor;

                uniform mat4 transform;

                void main() {
                    FragColor = color;
                    gl_Position = transform * vec4(position, 1.0);
                }
                """

                self.FRAGMENT_SHADER = """
                #version 330 core
                in vec3 FragColor;
                out vec4 OutColor;

                void main() {
                    OutColor = vec4(FragColor, 1.0); // Color del punto
                }
                """

            elif getattr(self.colors, "size", 0) == 0 and getattr(self.normals, "size", 0) > 0:
                # Caso 3: Con normales, sin colores (iluminación básica)
                self.VERTEX_SHADER = """
                #version 330 core
                layout (location = 0) in vec3 position;
                layout (location = 1) in vec3 normal;

                out vec3 FragNormal;
                out vec3 FragPos;

                uniform mat4 transform;
                uniform mat4 model;

                void main() {
                    FragPos = vec3(transform * vec4(position, 1.0));  // Ahora en espacio de cámara
                    FragNormal = normalize(normal);
                    gl_Position = transform * vec4(position, 1.0);
                }
                """

                self.FRAGMENT_SHADER = """
                #version 330 core
                in vec3 FragNormal;
                in vec3 FragPos;

                out vec4 FragColor;

                uniform vec3 lightPos;
                uniform vec3 lightColor;
                uniform vec3 objectColor;
                uniform vec3 viewPos; // Posición de la cámara

                void main() {
                    vec3 norm = normalize(FragNormal);
                    vec3 lightDir = normalize(lightPos - FragPos);

                    // Componente difusa (modelo Lambert)
                    float diff = max(dot(norm, lightDir), 0.2); // Luz mínima para evitar negro total

                    // Componente especular (modelo Phong)
                    vec3 viewDir = normalize(viewPos - FragPos);
                    vec3 reflectDir = reflect(-lightDir, norm);
                    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32); // Brillo especular

                    // Componente ambiental (iluminación mínima en todas partes)
                    vec3 ambient = 0.3 * objectColor;

                    // Color final combinando iluminación ambiental, difusa y especular
                    vec3 result = (ambient + diff * objectColor + spec * lightColor);
                    FragColor = vec4(result, 1.0);
                }
                """
            else:
                # Caso 4: Con normales y colores
                self.VERTEX_SHADER = """
                #version 330 core
                layout (location = 0) in vec3 position;
                layout (location = 1) in vec3 normal;
                layout (location = 2) in vec3 color;

                out vec3 FragNormal;
                out vec3 FragPos;
                out vec3 FragColor;

                uniform mat4 transform;
                uniform mat4 model;

                void main() {
                    FragPos = vec3(transform * vec4(position, 1.0));
                    FragNormal = normalize(normal);
                    FragColor = color;
                    gl_Position = transform * vec4(position, 1.0);
                }
                """

                self.FRAGMENT_SHADER = """
                #version 330 core
                in vec3 FragNormal;
                in vec3 FragPos;
                in vec3 FragColor;

                out vec4 FragOutput;

                uniform vec3 lightPos;
                uniform vec3 lightColor;
                uniform vec3 viewPos;

                void main() {
                    vec3 norm = normalize(FragNormal);
                    vec3 lightDir = normalize(lightPos - FragPos);
                    float diff = max(dot(norm, lightDir), 0.2);
                    vec3 ambient = 0.3 * FragColor;
                    vec3 result = (ambient + diff * FragColor);
                    FragOutput = vec4(result, 1.0);
                }
                """
            
        
        #eliminar shaders antiguos para dar paso a unos nuevos
       
        if self.shader_program is not None:
            glDeleteProgram(self.shader_program)
        if self.vertexShader is not None:
            glDeleteShader(self.vertexShader)
        if self.fragmentShader is not None:
            glDeleteShader(self.fragmentShader)
            
        #  Compilar Shaders
        
        self.shader_program = glCreateProgram()
       
        self.vertexShader = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(self.vertexShader, self.VERTEX_SHADER)
        glCompileShader(self.vertexShader)
        if glGetShaderiv(self.vertexShader, GL_COMPILE_STATUS) != GL_TRUE:
            print(" Vertex Shader Compilation Failed ")
            print(glGetShaderInfoLog(self.vertexShader).decode())

        self.fragmentShader = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(self.fragmentShader, self.FRAGMENT_SHADER)
        glCompileShader(self.fragmentShader)
        # Verificar compilación del Fragment Shader
        if glGetShaderiv(self.fragmentShader, GL_COMPILE_STATUS) != GL_TRUE:
            print(" Fragment Shader Compilation Failed ")
            print(glGetShaderInfoLog(self.fragmentShader).decode())

        glAttachShader(self.shader_program, self.vertexShader)
        glAttachShader(self.shader_program, self.fragmentShader)
        glLinkProgram(self.shader_program)
        if glGetProgramiv(self.shader_program, GL_LINK_STATUS) != GL_TRUE:
            print("Shader Linking Error:")
            print(glGetProgramInfoLog(self.shader_program).decode())

        
        glBindVertexArray(0)

    #para limpiar los buffers si están vacíos
    def clear_buffer_if_not_empty(self, buffer):
        
        # Borrar buffers antiguos antes de asignar nuevos datos
        #también comprobar que los buffer_vertex_objects no están vacíos
        #si están vacíos pueden dar problemas
        glBindVertexArray(self.VAO)
        if buffer == self.VBO:
       
            if self.VBO is not None:
                glDeleteBuffers(1, [self.VBO])
            self.VBO = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.VBO)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
            glEnableVertexAttribArray(0)

        if buffer == self.VBO_N and self.normals is not None:
          
            if self.VBO_N is not None:
                glDeleteBuffers(1, [self.VBO_N])
            self.VBO_N = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.VBO_N)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
            glEnableVertexAttribArray(1)

        if buffer == self.VBO_C and self.colors is not None:
          
            if self.VBO_C is not None:
                glDeleteBuffers(1, [self.VBO_C])
            self.VBO_C = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.VBO_C)
            glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
            glEnableVertexAttribArray(2)

        if buffer == self.VBO_T and self.texcoords is not None:
           
            if self.VBO_T is not None:
                glDeleteBuffers(1, [self.VBO_T])
            self.VBO_T = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.VBO_T)
            glVertexAttribPointer(3, 2, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
            glEnableVertexAttribArray(3)

        if buffer == self.EBO and self.faces is not None:
           
            if self.EBO is not None:
                glDeleteBuffers(1, [self.EBO])
            self.EBO = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.EBO)
        glBindVertexArray(0)

    #para ver si la malla tiene normales    
    def has_normals(self):
        if self.normals is not None:
            return True
        else:
            return False 
    #para ver si la malla tiene caras
    def has_faces(self):
        if self.faces is not None:
            return True
        else:
            return False
    #para añadir el nombre de la textura
    def set_texture(self, texture_path):
        self.texture_path = texture_path

    def load_ply(self, filename):
        #aseguramos que todos los atributos de la malla estén inicializados a None
        #esto es porque si cambia la malla que estamos usando y pasamos de que esa malla
        #tiene caras a no tener caras pues la visualización va a usar las caras de la anterior
        self.vertices = None
        self.normals = None
        self.colors = None
        self.faces = None
        self.texcoords = None
        self.texture = None
        ply = PlyData.read(filename)
        
        #hay ocasiones en las que introducimos archivos con textura 
        for comment in ply.comments:
            
            if comment.startswith("TextureFile"):
                folder = os.path.dirname(filename)  # Obtiene la carpeta donde está el PLY
                texture_name= comment.split(" ", 1)[1]  # Extrae el nombre después de "TextureFile"
                self.texture_path = os.path.join(folder, texture_name)  # Une carpeta + nombre de textura
                
        
        self.vertices = np.array([(v['x'], v['y'], v['z']) for v in ply['vertex']], dtype=np.float32)
        
        self.normals = np.array([(v['nx'], v['ny'], v['nz']) for v in ply['vertex']], dtype=np.float32) \
            if 'nx' in ply['vertex'][0].dtype.names else None
        
        # Cargar colores si existen
        if {'red', 'green', 'blue'}.issubset(ply['vertex'][0].dtype.names):
            self.colors = np.array([(v['red'], v['green'], v['blue']) for v in ply['vertex']], dtype=np.float32) / 255.0
        else:
            self.colors = None


        if 'face' in ply and len(ply['face'].data) > 0:
            self.faces = np.array([f[0] for f in ply['face'].data], dtype=object)  # Guardamos las listas de vértices
            self.faces = np.concatenate(self.faces).astype(np.uint32)  # Aplanamos la lista

            # Cargar coordenadas de textura si existen
            if 'texcoord' in ply['face'][0].dtype.names:
                self.texcoords = np.array([tuple(f['texcoord']) for f in ply['face']], dtype=np.float32).flatten()

        #invertir las coordenadas de textura para que se vea bien 
        if self.texcoords is not None:
            self.texcoords = self.texcoords.reshape(-1, 2)  # Convierte en (N, 2)
            self.texcoords[:, 1] = 1.0 - self.texcoords[:, 1]  # Invierte V

        #normalizar normales
        if self.normals is not None:
            norms = np.linalg.norm(self.normals, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Evita la división por cero
            self.normals /= norms
            
        # Normalizar los vértices
        self.normalize_vertices()
        #Como un mismo vértice podía tener diferentes coordenadas de textura en distintas caras, duplicamos los vértices para que cada cara tuviera sus propios datos independientes
        #getattr(colors, "size", 0) == 0 porque la malla parametrizada con textura no tiene colores de vértices. Mucho más secillo discriminar de esta forma
        if self.texcoords is not None and getattr(self.colors, "size", 0) == 0:
            self.faces = self.faces.reshape(-1, 3)


            # Crear nuevos arrays para vértices y texcoords expandiendo por caras
            new_vertices = []
            new_texcoords = []
            new_faces = []

            for i, face in enumerate(self.faces):
                new_face = []
                for j in range(3):  # Para cada vértice en la cara
                    vertex_index = face[j]  # Índice del vértice original

                    new_vertices.append(self.vertices[vertex_index])
                    new_texcoords.append(self.texcoords[i * 3 + j])  # Obtener la texcoord correcta de la cara

                    new_face.append(len(new_vertices) - 1)  # Índice del nuevo vértice en la lista expandida

                new_faces.append(new_face)  # Agregar la cara con los nuevos índices

            self.vertices = np.array(new_vertices, dtype=np.float32)
            self.texcoords = np.array(new_texcoords, dtype=np.float32)
            self.faces = np.array(new_faces, dtype=np.uint32)
        #en caso de que esa malla tenga textura inicailizarla
       
        if self.texture_path:
            if os.path.exists(self.texture_path):
                self.load_texture()
            else:
                print("No se ha encontrado el archivo de textura de esta malla")
            
        self.init_opengl() 
        self.load_shaders()
        
        self.update()
        


    
    def normalize_vertices(self):
        
        min_vals = np.min(self.vertices, axis=0)
        max_vals = np.max(self.vertices, axis=0)
        center = (min_vals + max_vals) / 2
        scale = np.max(max_vals - min_vals)
        self.vertices = (self.vertices - center) / scale

    def load_texture(self):
        
        img = Image.open(self.texture_path)
        img_data = np.array(img, dtype=np.uint8)

        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glGenerateMipmap(GL_TEXTURE_2D)
        

    def init_opengl(self):
        #asegura que el entorno de openGL está activo antes de iniciar las operaciones de buffer. Es decir
        #en paintGL por ejemplo, el entorno está activo, pero con makecurrent se puede activar en otras funciones
        
        
        self.makeCurrent()  
        
        #  Creo el VAO aquí porque cada vez que se carga una malla nueva no se compilan bien los shaders
        #  creando un nuevo VAO fuerzo a que se actualicen lo shaders
        #  elimino el VAO anterior para que no se acumulen los VAOs
        if self.VAO is not None:
            glDeleteVertexArrays(1, [self.VAO])
        self.VAO = glGenVertexArrays(1) #creamos el VAO aquí porque no se va a modificar durante todo el programa

        self.clear_buffer_if_not_empty(self.VBO)
        
         
        self.clear_buffer_if_not_empty(self.VBO_N)
        self.clear_buffer_if_not_empty(self.VBO_C)
        self.clear_buffer_if_not_empty(self.VBO_T)
        self.clear_buffer_if_not_empty(self.EBO)
        glBindVertexArray(self.VAO)
        # Actualizar VBO de vértices
        glBindBuffer(GL_ARRAY_BUFFER, self.VBO)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)

        # Actualizar VBO de normales si existen
        if self.normals is not None:
            glBindBuffer(GL_ARRAY_BUFFER, self.VBO_N)
            glBufferData(GL_ARRAY_BUFFER, self.normals.nbytes, self.normals, GL_STATIC_DRAW)

        # Actualizar VBO de colores si existen
        if self.colors is not None:
            glBindBuffer(GL_ARRAY_BUFFER, self.VBO_C)
            glBufferData(GL_ARRAY_BUFFER, self.colors.nbytes, self.colors, GL_STATIC_DRAW)

        # Actualizar VBO de coordenadas de textura si existen
        if self.texcoords is not None:
            glBindBuffer(GL_ARRAY_BUFFER, self.VBO_T)
            glBufferData(GL_ARRAY_BUFFER, self.texcoords.nbytes, self.texcoords, GL_STATIC_DRAW)

        # Actualizar 
        if self.faces is not None:
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.EBO)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.faces.nbytes, self.faces, GL_STATIC_DRAW)
       

       
        glBindVertexArray(0)
       

    def paintGL(self):
        
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        rotation_y = np.array([
            [np.cos(self.yaw), 0, np.sin(self.yaw), 0],
            [0, 1, 0, 0],
            [-np.sin(self.yaw), 0, np.cos(self.yaw), 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        rotation_x = np.array([
            [1, 0, 0, 0],
            [0, np.cos(self.pitch), -np.sin(self.pitch), 0],
            [0, np.sin(self.pitch), np.cos(self.pitch), 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)


        #ya implementaré bien el roll luego
        rotation_z = np.array([
            [np.cos(self.roll), -np.sin(self.roll), 0, 0],
            [np.sin(self.roll), np.cos(self.roll), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        

        # Aplicamos las rotaciones en orden (Y luego X luego Z)
        self.model = rotation_y @ rotation_x @ rotation_z
        self.view = self.look_at(
                np.array([self.cam_x, self.cam_y, self.cam_z], dtype=np.float32), # Posición de la cámara (X, Y, Z)
                np.array([0, 0, 0], dtype=np.float32), # Punto al que mira
                np.array([0, 1, 0], dtype=np.float32)   # Vector "arriba"
            )
        #añadimos aquí el projection el fov se va modificando
        projection = self.perspective_matrix(self.fov, self.aspect, self.near, self.far)
        transform = projection @ self.view @ self.model
       

        if self.vertices is not None:
        
            glUseProgram(self.shader_program)

            if self.texture is not None:
                
                glUniform1i(glGetUniformLocation(self.shader_program, "texture1"), 0) 
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, self.texture)
          
            transformLoc = glGetUniformLocation(self.shader_program, "transform")
            glUniformMatrix4fv(transformLoc, 1, GL_TRUE, transform.flatten())
            lightPos_cam = (self.view @ np.append(self.lightPos, 1.0))[:3]
            glUniform3fv(glGetUniformLocation(self.shader_program, "lightPos"), 1, lightPos_cam)

            glUniform3fv(glGetUniformLocation(self.shader_program, "lightColor"), 1, self.lightColor)
            glUniform3fv(glGetUniformLocation(self.shader_program, "objectColor"), 1, self.objectColor)
            
            glBindVertexArray(self.VAO)


            #glBindBuffer(GL_ARRAY_BUFFER, self.VBO)

            
            # getattr(colors, "size", 0) == 0 porque la malla parametrizada con textura no tiene colores, mucho más sencillo discriminar de esta forma
            if self.texcoords is not None and getattr(self.colors, "size", 0) == 0:
           
                #glDrawElements a glDrawArrays. Como habíamos expandido los datos correctamente (cada vértice tenía sus propias coordenadas de textura), ya no era necesario usar índices (faces) para dibujar.
                glDrawArrays(GL_TRIANGLES, 0, len(self.vertices))
            else:
                if self.faces is not None and len(self.faces) > 0:
                    

                    glDrawElements(GL_TRIANGLES, len(self.faces), GL_UNSIGNED_INT, None)
                   
                else:
                   
                    glDrawArrays(GL_POINTS, 0, len(self.vertices))

            glBindVertexArray(0)
        
        
       
      
"""
#comprobación de VB para ver si funcionan correctamente
vao_binding = glGetInteger(GL_VERTEX_ARRAY_BINDING)
        vbo_binding = glGetInteger(GL_ARRAY_BUFFER_BINDING)
        ebo_binding = glGetInteger(GL_ELEMENT_ARRAY_BUFFER_BINDING)

        print("🔹 VAO activo:", vao_binding)
        print("🔹 VBO activo:", vbo_binding)
        print("🔹 EBO activo:", ebo_binding)

        print("VAO:", self.VAO)
        print("VBO:", self.VBO)
        print("VBO_N (normales):", self.VBO_N)
        print("VBO_C (colores):", self.VBO_C)
        print("VBO_T (texcoords):", self.VBO_T)
        print("EBO:", self.EBO)
        glBindBuffer(GL_ARRAY_BUFFER, self.VBO)
        buffer_data = glGetBufferSubData(GL_ARRAY_BUFFER, 0, self.vertices.nbytes)
        print("Datos en el buffer:", buffer_data[:10])  # Muestra los primeros valores

        size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE)
        print(f"🟢 Tamaño de VBO: {size} bytes (debería ser {self.vertices.nbytes})")
        

        for i in range(4):  # Suponiendo que tienes hasta 4 atributos
            enabled = glGetVertexAttribiv(i, GL_VERTEX_ATTRIB_ARRAY_ENABLED)
            print(f"🔹 Atributo {i}: {enabled}")  # Imprime directamente el array

""" 



