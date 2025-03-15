import sys
from mesh_processing import *
from PyQt5.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QApplication, QFileDialog, QLineEdit, QMainWindow, QAction, QVBoxLayout, QWidget, QDialog, QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor
from ply_viewer_class import PlyViewer
#pilsa que usaremos para ir hacia atrás y hacia alante
from stack import Stack
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np
import faulthandler
#para depurar
faulthandler.enable()


class TransparentGraph(QWidget):
    """Ventana flotante y transparente con la gráfica de coordenadas de textura."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")  # Qt transparente
        
        # Posición inicial en 0, 0 porque la posición la va a controlar
        #el resizeEvent
        self.setGeometry(0, 0, 400, 400)  

        # Layout para el gráfico
        layout = QVBoxLayout()
        self.figure, self.ax = plt.subplots()
        self.figure.patch.set_alpha(0)  # Fondo de la figura transparente
        self.ax.patch.set_alpha(0)  # Fondo de los ejes transparente

        # Crear el lienzo de Matplotlib integrado en Qt
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background:transparent;")  # Matplotlib sin fondo
        
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.setVisible(False)  # Inicialmente oculta

        # Variables para arrastrar la ventana
        self.dragging = False
        self.last_pos = None

    def plot_texcoords(self, texcoords):
        """Dibuja las coordenadas de textura en la gráfica."""
        if texcoords is not None and len(texcoords) > 0:
            texcoords = np.array(texcoords)
            #lo invierto porque lo he invertido para que se vea bien la textura
            texcoords[:, 1] = 1.0 - texcoords[:, 1]  # Invierte V
            self.ax.clear()
            self.ax.set_facecolor('none')  # Asegurar que el fondo es transparente
            self.ax.scatter(texcoords[:, 0], texcoords[:, 1], c='white', marker='o', s=0.5)

            
            # Configurar ejes blancos
            self.ax.spines['bottom'].set_color('white')
            self.ax.spines['top'].set_color('white') 
            self.ax.spines['left'].set_color('white')
            self.ax.spines['right'].set_color('white')

            self.ax.xaxis.label.set_color('white')  # Etiqueta del eje X en blanco
            self.ax.yaxis.label.set_color('white')  # Etiqueta del eje Y en blanco
            self.ax.tick_params(axis='x', colors='white')  # Color de los ticks del eje X
            self.ax.tick_params(axis='y', colors='white')  # Color de los ticks del eje Y

            # Ajustar límites
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(0, 1)
            self.canvas.draw()

            self.setVisible(True)  # Mostrar la ventana cuando se actualiza

    def mousePressEvent(self, event):
        """Detecta cuando se empieza a arrastrar la ventana."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_pos = event.globalPos()

class OutputStream:
    """ Clase para redirigir stdout a QTextEdit """
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):
        self.text_widget.append(text.strip())  # Agrega texto a la terminal
        self.text_widget.ensureCursorVisible()  # Asegura que el scroll baje

    def flush(self):
        pass  # No es necesario en este caso

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):

        self.setWindowTitle("PLY viewer and processor")
        self.setGeometry(100, 0, 1100, 800)  # Tamaño inicial de la ventana

        #stack para ir hacia detrás
        self.back = Stack()
        #stack para ir hacia delante
        self.forward = Stack()

      
        
        #botón de ir hacia atrás
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(lambda: self.back_button_function())

        #botón de ir hacia alante
        self.forward_button = QPushButton("Forward")
        self.forward_button.clicked.connect(lambda: self.forward_button_function())

        #crear meshset
        self.ms = pymeshlab.MeshSet()
        #nombre de la textura
        self.texture_name = 'transferred_texture.png'
        #archivo inicial del meshset
        self.file_path = None
        #comprobar si una malla o nube de putnos tiene normales
        self.has_normals = None
        #para la nube de puntos que utilizaremos para crear la textura
        self.point_cloud_name = None
        #id de la malla voronoi atlas
        self.voronoi_atlas_name = None
        #octree_depth when surface reconstruction
        self.octree_depth= 8
        #Tamaño de los agujeros
        self.hole_size = 50
        #Número e caras objetivo cuando simplifico
        self.target_faces = 40000

        # Crear barra de menú
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        self.processing_menu = menubar.addMenu("Mesh processing")
        
        #procesos de reparación de la malla
        self.normals_created = QLabel("Normals Created") #0

        self.screened_poisson_done = QLabel("Screened posisson filter") #1
       
        self.huge_faces_removed = QLabel("Huge faces removed") #2
   
        self.mesh_repaired_done = QLabel("Mesh repaired after" + "\n"+"screened poisson") #3

        #esto lo añado para que cuando vaya a reparar la malla por segunda vez, se llame al metodo correcto
        self.simplified_mesh_done_check=False
        self.simplified_mesh_done = QLabel("Mesh simplified") #4
   
        self.mesh_repaired2_done = QLabel("Mesh repaired after" + "\n" + "mesh simplification") #5

        self.voronoi_done = QLabel("Voronoi atlas filter aplied") #6

        self.added_texture_done = QLabel("Texture mesh generated") #7
      

        """
        Añadimos todo los necesario para poder introducir el hole_size y el
        octree_depth
        """
        # ** Cuadro de texto para "Hole Size" **
        self.hole_size_label = QLabel("Hole Size :")
        self.hole_size_input = QLineEdit("50")

        # ** Cuadro de texto para "Octree Depth" **
        self.octree_label = QLabel("Octree Depth:")
        self.octree_input = QLineEdit("8")

        # ** Cuadro de texto para "Target num of faces" **
        self.target_faces_label = QLabel("Target number of faces:")
        self.target_faces_input = QLineEdit("10000")

        # ** Botón de aplicar **
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(lambda: self.label_values(self.hole_size_input, self.octree_input, self.target_faces_input))

        # ** Botón para hacer el proceso automáticamente **
        self.process_mesh_button = QPushButton("Process point cloud")
        self.process_mesh_button.clicked.connect(lambda: self.set_processing_button())
        # ** Layout derecho (inputs y botón) **
        self.right_panel = QVBoxLayout()
        self.right_panel.addWidget(self.hole_size_label)
        self.right_panel.addWidget(self.hole_size_input)
        self.right_panel.addWidget(self.octree_label)
        self.right_panel.addWidget(self.octree_input)
        self.right_panel.addWidget(self.target_faces_label)
        self.right_panel.addWidget(self.target_faces_input)
        self.right_panel.addWidget(self.apply_button)
        self.right_panel.addWidget(self.back_button)
        self.right_panel.addWidget(self.forward_button)
        self.right_panel.addWidget(self.process_mesh_button)
        self.right_panel.addWidget(self.normals_created)
        self.right_panel.addWidget(self.screened_poisson_done)
        self.right_panel.addWidget(self.huge_faces_removed)
        self.right_panel.addWidget(self.mesh_repaired_done)
        self.right_panel.addWidget(self.simplified_mesh_done)
        self.right_panel.addWidget(self.mesh_repaired2_done)
        self.right_panel.addWidget(self.voronoi_done)
        self.right_panel.addWidget(self.added_texture_done)
        self.right_panel.addStretch()  # Empuja todo hacia arriba

        # ** Widget contenedor derecho (le ponemos un ancho fijo) **
        self.right_widget = QWidget()
        self.right_widget.setLayout(self.right_panel)
        self.right_widget.setFixedWidth(200)  # Limita el ancho del panel derecho


        # Opción de "Cargar PLY"
        load_action = QAction("Load PLY", self)
        load_action.triggered.connect(self.load_ply)
        file_menu.addAction(load_action)

         # Opción de "Mostrar Coordenadas de Textura"
        texcoord_action = QAction("See TexCoords", self)
        texcoord_action.triggered.connect(self.toggle_texcoords)
        file_menu.addAction(texcoord_action)

        #opción para guardar un ply
        saveply_action = QAction("Save file", self)
        saveply_action.triggered.connect(self.save_ply)
        file_menu.addAction(saveply_action)

        #archivo de salida de cada modificación en el meshset
        self.output_file = None
        
        # ** Layout viewer con visor ply y panel derecho **
        self.viewer = QHBoxLayout()
        # Crear el visor PLY y añadirlo debajo del gráfico
        self.ply_viewer_class = PlyViewer()  # Se llama a initializeGL  
        self.viewer.addWidget(self.ply_viewer_class) 
        self.viewer.addWidget(self.right_widget)  # Panel derecho
       
        # ** Terminal (QTextEdit para capturar `print`) **
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        #terminal con fondo negro
        self.terminal.setStyleSheet("""
            background-color: black;
            color: white;
            font-family: Consolas, Courier, monospace;
            font-size: 12px;
            border: none;
        """)
        self.terminal.setPlaceholderText("Terminal output...")
        self.terminal.setFixedHeight(150)  # Fijar altura

        # ** Widget contenedor de la terminal con layout **
        self.down_widget = QWidget()
        down_layout = QVBoxLayout(self.down_widget)
        down_layout.addWidget(self.terminal)
        down_layout.setContentsMargins(0, 0, 0, 0)  # Eliminar márgenes

        # ** Configurar política de tamaño **
        # se usa la del panel derecho porque ya está bien configurada
        self.terminal.setSizePolicy(self.right_widget.sizePolicy())  

        # ** Crear Layout principal en vertical (Visor arriba, Terminal abajo) **
        self.main_layout = QVBoxLayout()
         # ** Añadir el visor y la terminal al layout principal **
        self.main_layout.addLayout(self.viewer)  # Arriba
        self.main_layout.addWidget(self.down_widget)  # Abajo

        # Widget principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setLayout(self.main_layout)
        # **Redirigir stdout a la terminal**
        sys.stdout = OutputStream(self.terminal)

        #crear el menú de procesamiento
        self.create_processing_menu()
        
        
        # Crear la ventana flotante del gráfico (pero no mostrarla aún)
        self.graph_window = TransparentGraph(self)
    #con este evento podemos cambiar el tamaño de la ventana sin miedo a que las coordenadas 
    #de textura  no cambien de posición para las mallas con coordenadas de textura
    def resizeEvent(self, event):
        """
        Se ejecuta cuando se redimensiona la ventana.
        Mueve el widget de coordenadas de textura a la nueva posición correcta.
        """
        super().resizeEvent(event)
        self.graph_window.move(self.width()-600, 10)  # Mueve el widget a la derecha
    def save_ply(self):
        
        if not self.back.is_empty() :
            #nombre por defecto del archivo
            default_name="Untitled.ply"
            #seleccionar archivo actual
            file = self.back.peek()[0]
            # Abrir diálogo para seleccionar dónde guardar el archivo
            save_path, _ = QFileDialog.getSaveFileName(None, "Save file", default_name, "PLY Files (*.ply)")

            if save_path:  # Si el usuario eligió una ruta
                with open(file, "rb") as f_src, open(save_path, "wb") as f_dest:
                    f_dest.write(f_src.read())  # Copiar contenido al nuevo destino
                    if self.back.peek()[7]==7:
                        texture_dir = os.path.dirname(file)  # Obtiene la carpeta donde está el archivo
                        texture_path = os.path.join(texture_dir, self.texture_name)  # Une carpeta + nombre de textura
                        
                        # Nueva ruta donde guardar la textura
                        save_texture_path = os.path.join(os.path.dirname(save_path), self.texture_name)

                        # Verifica si el archivo de textura existe
                        if os.path.exists(texture_path):
                            with open(texture_path, "rb") as tex_file, open(save_texture_path, "wb") as tex_dest:
                                tex_dest.write(tex_file.read())  # Copiar la textura a la carpeta de destino

                print(f"File saved in: {save_path}")
            else:
                print("Saving canceled")
        else:
            print("There is not files to save")


    def load_ply(self):
        self.file_path, _ = QFileDialog.getOpenFileName(self, "Opne PLY file", "", "PLY Files (*.ply)")
        if self.file_path:
            self.ply_viewer_class.load_ply(self.file_path)
            #mirar si la nube de puntos tiene normales
            self.has_normals = self.ply_viewer_class.has_normals()
            #mirar si la nube de puntos tiene caras, es decir, si no es una nube de puntos
            self.has_faces = self.ply_viewer_class.has_faces()

            #reiniciar textos
            self.normals_created.setText("Normals created ")
            self.screened_poisson_done.setText("Screened posisson filter ")
            self.huge_faces_removed.setText("Huge faces removed ")
            self.mesh_repaired_done.setText("Mesh repaired after" + "\n"+"screened poisson " )
            #poner esto a false cada vez que craguemos un ply
            self.simplified_mesh_done_check=False
            self.simplified_mesh_done.setText("Mesh simplified ")
            self.mesh_repaired2_done.setText("Mesh repaired after" + "\n" + "mesh simplification ")   
            self.voronoi_done.setText("Voronoi atlas filter aplied")
            self.added_texture_done.setText("Texture mesh generated")

            #archivo inicial si la primera nube de puntos tiene normales
            if self.has_faces == 0 and self.has_normals >0:
                self.point_cloud_name = self.file_path
                self.normals_created.setText("Normals created \u2714")  # Añadir el tick
                number = 0
            else:
                number = -1
           
            #cargar ply en pymeshlab
            self.ms.clear() #cada nueva malla a cargar y procesar es un nuevo meshset
            #limpiar la carpeta de archivos tenporales cada vez que cargamos un nuevo ply
            self.clear_generated_files()
            load_ply(self.ms, self.file_path)
            #vaciamos las pilas en caso de que tengan archivos
            while not self.back.is_empty():
                self.back.pop()
            while not self.forward.is_empty():
                self.forward.pop()

            #añado este file_path al stack de back
            file_path_for_stack = self.file_path
            self.back.push([
                file_path_for_stack, 
                self.ply_viewer_class.vertices,
                self.ply_viewer_class.normals,
                self.ply_viewer_class.colors,
                self.ply_viewer_class.faces,
                self.ply_viewer_class.texcoords,
                self.ply_viewer_class.texture_path,
                number
              ])
            
            #cada vez que cargo un ply quito el gráfico de las coordenadas de textura
            if self.graph_window.isVisible():
                self.graph_window.setVisible(False)
    #esta función carga archivos ply del meshset de pymeshlab para la visualización
    def load_processed_ply(self, file_name):
        if file_name:
            self.ply_viewer_class.load_ply(file_name)
            #cada vez que cargo un ply quito el gráfico de las coordenadas de textura
            if self.graph_window.isVisible():
                self.graph_window.setVisible(False)
    def toggle_texcoords(self):
        """Muestra u oculta la ventana del gráfico con las coordenadas de textura."""
        if self.graph_window.isVisible():
            self.graph_window.setVisible(False)
        else:
            texcoords = self.ply_viewer_class.texcoords
            if texcoords is not None and len(texcoords) > 0:
                self.graph_window.plot_texcoords(texcoords)
            else:
                print("No texture coordinates available.")
    #botón para el procesamiento de la malla
    def set_processing_button(self):
        if self.file_path is not None:
            #se hace la comprobación de si la malla actual del meshset es una nube de puntos
            if self.ply_viewer_class.has_faces() == False:
          
                if self.has_normals == False:
                    self.set_output_file_normals(*compute_normals_if_necessary(self.ms, self.has_normals, self.has_faces, self.file_path))
                    QApplication.processEvents()  # Permite actualizar la UI
                self.apply_surface_reconstruction()
                QApplication.processEvents()
                self.apply_remove_huge_faces()
                QApplication.processEvents()
                self.apply_repair_mesh()
                QApplication.processEvents()
                self.apply_simplify_mesh()
                QApplication.processEvents()
                self.apply_repair_mesh()
                QApplication.processEvents()
                check_voronoi = self.apply_voronoi()
                QApplication.processEvents()
                number_of_faces = 15000
                # en caso de que voronoi falle, cambiamos algunos parámetros
                while not check_voronoi:
                    print("Voronoi atlas failed, trying again with more faces for the mesh simplification")
                    self.back_button_function()
                    QApplication.processEvents()
                    self.back_button_function()
                    QApplication.processEvents()
                    number_of_faces_aux = str(number_of_faces)
                    self.target_faces_input.setText(number_of_faces_aux)
                    self.target_faces = number_of_faces
                    number_of_faces+=5000
                    QApplication.processEvents()
                    self.apply_simplify_mesh()
                    QApplication.processEvents()
                    self.apply_repair_mesh()
                    QApplication.processEvents()
                    check_voronoi = self.apply_voronoi()
                    QApplication.processEvents()
                self.safe_transfer_texture() 
                
            else:
                print("To use this botton, cuurent mesh should be a point cloud")
        else:
            print("There is not any file loaded")
    def create_processing_menu(self):

        #lambda nos permite llamar a la función solo cuando el botón sea pulsado
        compute_normals = QAction("Compute normals for points sets", self)
        compute_normals.triggered.connect(lambda: (
            self.set_output_file_normals(*compute_normals_if_necessary(self.ms, self.has_normals, self.has_faces, self.file_path))))
        self.processing_menu.addAction(compute_normals)

        surface_resconstruction = QAction("Generate surface reconstruction screened poisson", self)
        surface_resconstruction.triggered.connect(lambda: (
           self.apply_surface_reconstruction() ))
        self.processing_menu.addAction(surface_resconstruction)

        remove_huge_faces = QAction("Remove huge unused faces", self)      
        remove_huge_faces.triggered.connect(lambda:(
            self.apply_remove_huge_faces()))
        self.processing_menu.addAction(remove_huge_faces)
        

        repair_mesh_action = QAction("Repair mesh", self)
        repair_mesh_action.triggered.connect(lambda:(
        self.apply_repair_mesh()))
        self.processing_menu.addAction(repair_mesh_action)

        simplify_mesh_action = QAction("Simplify mesh", self)
        simplify_mesh_action.triggered.connect(lambda:(
        self.apply_simplify_mesh()))
        self.processing_menu.addAction(simplify_mesh_action)

        
        voronoi_atlas_action = QAction("Voronoi atlas filer", self)
        voronoi_atlas_action.triggered.connect(lambda:(
            self.apply_voronoi()
        ))
        self.processing_menu.addAction(voronoi_atlas_action)

        mesh_with_texture_action = QAction("Create texture filer", self)
        mesh_with_texture_action.triggered.connect(lambda:(
        self.safe_transfer_texture()))
        self.processing_menu.addAction(mesh_with_texture_action)

    #función para la recnstucción de la superficie
    def apply_surface_reconstruction(self):
        output_file = surface_reconstruction(self.ms, self.octree_depth)
        self.set_output_file(output_file, 1)
    #remove huge faces funcion
    def apply_remove_huge_faces(self):
        output_file = remove_huge_unused_faces(self.ms)
        self.set_output_file(output_file, 2)
    def apply_repair_mesh(self):
        output_file = repair_mesh(self.ms, self.hole_size, "repaired_mesh.ply")
        if self.simplified_mesh_done_check ==False:
            self.set_output_file(output_file, 3)
        else:
            self.set_output_file(output_file, 5)
    def apply_simplify_mesh(self):
        output_file = mesh_simplification(self.ms, self.target_faces)
        self.set_output_file(output_file, 4)
        self.simplified_mesh_done_check = True
    
    #creamos una función para el botón de voronoi atlas
    def apply_voronoi(self):
        
        last_file = self.back.peek()[0]
        output_file, check_voronoi = voronoi_atlas(self.ms, last_file)      
        self.set_output_file_voronoi(output_file)
        return check_voronoi

    def safe_transfer_texture(self):
        self.ms.clear()
        load_ply(self.ms, self.point_cloud_name)
        point_cloud_id= self.ms.current_mesh_id()

        load_ply(self.ms, self.voronoi_atlas_name)
        voronoi_atlas_id = self.ms.current_mesh_id()
        if self.ms is None:
            print("Error: self.ms is None, avoiding crash")
            return

        print(f"MeshSet contains {self.ms.mesh_number()} meshes:")
        meshes = []
        for i in range(20):
            if self.ms.mesh_id_exists(i):
                meshes.append(i)  # Agrega el ID de la malla a la lista
                
        for i in meshes:  # Itera sobre los IDs válidos
            try:
                mesh = self.ms.mesh(i)
                print(f"  Mesh {i}: {mesh}, vertex: {mesh.vertex_number()}, faces: {mesh.face_number()}")
            except Exception as e:
                print(f"  Mesh access error {i}: {e}")
        print(f"point_cloud_id: {point_cloud_id}")
        print(f"voronoi_atlas_id: {voronoi_atlas_id}")
        print(f"texture_name: {self.texture_name}")

        if self.ms is None:
            print("Error: one of the values is None, avoiding crash")
            return

        output_file = transfer_attributes_to_texture_per_vertex(self.ms, point_cloud_id, voronoi_atlas_id, self.texture_name)
        self.set_output_file(output_file,7)
    def set_output_file_normals(self, output_file):
        if output_file is not None:
            self.output_file = output_file
            #siempre que haya un outputfile habrá una id
            self.point_cloud_name = self.output_file
            self.load_processed_ply(output_file)
            #añadimos el archivo al stack
            file_path_for_stack = self.output_file
            self.normals_created.setText("Normals created \u2714") 
            
            number = 0
            self.back.push([
                file_path_for_stack, 
                self.ply_viewer_class.vertices,
                self.ply_viewer_class.normals,
                self.ply_viewer_class.colors,
                self.ply_viewer_class.faces,
                self.ply_viewer_class.texcoords,
                self.ply_viewer_class.texture_path,
                number
              ])
            #eliminamos lo anterior de forward
            while not self.forward.is_empty():
                self.forward.pop()
            #vaciamos el meshset para tener solo una malla
            self.ms.clear()
            # Recargar la malla en el MeshSet para que los cambios se reflejen
            load_ply(self.ms, file_path_for_stack)
            print(f"File with normals generated: {output_file}")
        else:
            print("A new file was not generated because the point cloud already has normals.")   

    def set_output_file_voronoi(self, output_file):
        if output_file is not None:
            self.output_file = output_file
            #siempre que haya un outputfile habrá una id
            
            self.voronoi_atlas_name = self.output_file
            self.load_processed_ply(output_file)
            #añadimos el archivo al stack
            file_path_for_stack = self.output_file
            self.voronoi_done.setText("Voronoi atlas filter aplied \u2714")
            number = 6
            self.back.push([
                file_path_for_stack, 
                self.ply_viewer_class.vertices,
                self.ply_viewer_class.normals,
                self.ply_viewer_class.colors,
                self.ply_viewer_class.faces,
                self.ply_viewer_class.texcoords,
                self.ply_viewer_class.texture_path,
                number
              ])
            #eliminamos lo anterior de forward
            while not self.forward.is_empty():
                self.forward.pop()
            #vaciamos el meshset para tener solo una malla
            self.ms.clear()
            # Recargar la malla en el MeshSet para que los cambios se reflejen
            load_ply(self.ms, file_path_for_stack)
           
            print(f"Voronoi atlas file generated: {output_file}")
        else:
            print("No file voronoi atlas was created.") 

        
    def set_output_file(self, output_file, number):
        if output_file:
            self.output_file = output_file
            #siempre que haya un outputfile habrá una id
        
            self.load_processed_ply(output_file)
            #añadimos el archivo al stack
            file_path_for_stack = self.output_file
            if number == 1:
                self.screened_poisson_done.setText("Screened posisson filter \u2714")
            elif number == 2:
                self.huge_faces_removed.setText("Huge faces removed \u2714")
            elif number == 3:
                self.mesh_repaired_done.setText("Mesh repaired after" + "\n"+"screened poisson " + "\u2714" )
            elif number == 4:
                self.simplified_mesh_done.setText("Mesh simplified \u2714")
            elif number == 5:
                self.mesh_repaired2_done.setText("Mesh repaired after" + "\n" + "mesh simplification \u2714")   
            elif number == 7:
                self.added_texture_done.setText("Texture mesh generated \u2714")
            self.back.push([
                file_path_for_stack, 
                self.ply_viewer_class.vertices,
                self.ply_viewer_class.normals,
                self.ply_viewer_class.colors,
                self.ply_viewer_class.faces,
                self.ply_viewer_class.texcoords,
                self.ply_viewer_class.texture_path,
                number
              ])
            #eliminamos lo anterior de forward
            while not self.forward.is_empty():
                self.forward.pop()
            #vaciamos el meshset para tener solo una malla
            self.ms.clear()
            # Recargar la malla en el MeshSet para que los cambios se reflejen
            load_ply(self.ms, file_path_for_stack)
           
            print(f"File created: {output_file}")
        else:
            print("No file was generated.")   
    #función para agregar valores a hole_size y a octree_depth con el fin de 
    def label_values(self, hole_input, octree_input, target_faces_input):
        try:
            self.hole_size = int(hole_input.text())  # Convertir el texto en número
            self.octree_depth = int(octree_input.text())
            self.target_faces = int(target_faces_input.text())
            print(f"Hole Size: {self.hole_size}, Octree Depth: {self.octree_depth}, Target number of faces: {self.target_faces}")
        except ValueError:
            print("Error: Introduce valid numeric values.")
    #para limpiar la carpeta de archivos que no utilizo cada vez que cargo un nuevo ply
    def clear_generated_files(self):
        #folder_name está definido como global en mesh processing
        if not os.path.exists(folder_name):  # Verificar si la carpeta existe
            print(f"Folder '{folder_name}' doesn't exists.")
            return

        for file in os.listdir(folder_name):  # Iterar sobre los archivos en la carpeta
            file_path = os.path.join(folder_name, file)
            try:
                if os.path.isfile(file_path):  # Eliminar solo archivos, no subdirectorios
                    os.remove(file_path)
                    print(f"Removing: {file_path}")
            except Exception as e:
                print(f"It was not possible to remove {file_path}: {e}")

        print(f"Folder '{folder_name}' emptied.")
    def back_button_function(self):
        if not self.back.is_empty():
            file = self.back.pop()
           
            self.forward.push(file)
            number=file[7]
            #cambiar los textos
            # a veces hago dos comprobaciones porque puede ser que por ejemplo, haya reparado la malla dos veces
            #con agujeros de diferente tamaño
            if number == 0:
                self.normals_created.setText("Normals created ")
            elif number == 1:
                self.screened_poisson_done.setText("Screened posisson filter ")
            elif number == 2:
                if self.back.peek()[7] != 2:
                    self.huge_faces_removed.setText("Huge faces removed ")
            elif number == 3:
                if self.back.peek()[7] != 3:
                    self.mesh_repaired_done.setText("Mesh repaired after" + "\n"+"screened poisson " )
            elif number == 4:
                if self.back.peek()[7] != 4:
                    self.simplified_mesh_done.setText("Mesh simplified ")
                    self.simplified_mesh_done_check = False
            elif number == 5:
                if self.back.peek()[7] != 5:
                    self.mesh_repaired2_done.setText("Mesh repaired after" + "\n" + "mesh simplification ")   
            elif number == 6:
                if self.back.peek()[7] != 6:
                    self.voronoi_done.setText("Voronoi atlas filter aplied")
            elif number == 7:
                self.added_texture_done.setText("Texture mesh generated")
            
            #borrar las mallas del mesh set
            self.ms.clear()
            if self.back.size() == 1:
                #archivo inicial si la primera nube de puntos tiene normales
                if self.has_faces == 0 and self.has_normals >0:
                    self.point_cloud_name = self.file_path
                #el archivo actual a cargar
                attributes = self.back.peek()
                self.ply_viewer_class.load_attributes(attributes[1], attributes[2], attributes[3], attributes[4], attributes[5], attributes[6])
                load_ply(self.ms, attributes[0])
                

            elif self.back.is_empty():
             
                self.ply_viewer_class.clear_background()
            else:
                #el archivo actual a cargar
                attributes = self.back.peek()
                load_ply(self.ms, attributes[0])
                self.ply_viewer_class.load_attributes(attributes[1], attributes[2], attributes[3], attributes[4], attributes[5], attributes[6])
            if self.graph_window.isVisible():
                    self.graph_window.setVisible(False)


    def forward_button_function(self):

        if not self.forward.is_empty():
            #limpiamos el meshset
            self.ms.clear()
            file = self.forward.pop()
            number=file[7]
            #cambiar los textos
            if number == 0:
                self.normals_created.setText("Normals created \u2714")
            elif number == 1:
                self.screened_poisson_done.setText("Screened posisson filter \u2714")
            elif number == 2:       
                    self.huge_faces_removed.setText("Huge faces removed \u2714")
            elif number == 3:   
                    self.mesh_repaired_done.setText("Mesh repaired after" + "\n"+"screened poisson \u2714" )
            elif number == 4:   
                    self.simplified_mesh_done.setText("Mesh simplified \u2714")
                    self.simplified_mesh_done_check = True
            elif number == 5:
                    self.mesh_repaired2_done.setText("Mesh repaired after" + "\n" + "mesh simplification \u2714")   
            elif number == 6:
                    self.voronoi_done.setText("Voronoi atlas filter aplied \u2714")
            elif number == 7:
                self.added_texture_done.setText("Texture mesh generated \u2714")
            self.back.push(file)
            #el archivo actual a cargar
            attributes = self.back.peek()
            #cargamos el archivo al meshset
            load_ply(self.ms, attributes[0])
            self.ply_viewer_class.load_attributes(attributes[1], attributes[2], attributes[3], attributes[4], attributes[5], attributes[6])
            if self.graph_window.isVisible():
                    self.graph_window.setVisible(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec())

