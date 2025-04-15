# Importa la biblioteca PyMeshLab
import pymeshlab

import numpy as np
import multiprocessing
import os
import psutil
import os
from mesh_functions import *

#nombre de la carpeta de archivos temporales como variabe global
folder_name  = "generated files/"

def repair_mesh(ms, hole_size, file_name):
    """
    Realiza un proceso de reparación en la malla usando los métodos de PyMeshLab.
    
    Argumentos:
    ms: PyMeshLab.MeshSet
        Conjunto de mallas cargado con PyMeshLab.
    """
    # Verificar si la malla tiene caras
    if ms.current_mesh().face_number() == 0:
        print("Error: current mesh has not faces")
        return None
    holes=None

    check_mesh_repaired = False
    
    while not check_mesh_repaired:
        # Suponemos que la malla está reparada hasta encontrar un problema
        check_mesh_repaired = True
        
        # Seleccionar caras pequeñas desconectadas y eliminarlas
        ms.compute_selection_by_small_disconnected_components_per_face()
        if ms.current_mesh().selected_face_number() > 0:
            ms.meshing_remove_selected_faces()
            check_mesh_repaired = False

        # Seleccionar caras problemáticas, dilatar selección y eliminarlas
        ms.compute_selection_bad_faces()
        ms.apply_selection_dilatation()
        if ms.current_mesh().selected_face_number() > 0:
            ms.meshing_remove_selected_faces()
            check_mesh_repaired = False

        # Seleccionar caras con bordes no manifold, dilatar selección y eliminarlas
        ms.compute_selection_by_non_manifold_edges_per_face()
        ms.apply_selection_dilatation()
        if ms.current_mesh().selected_face_number() > 0:
            ms.meshing_remove_selected_faces()
            check_mesh_repaired = False

        # Seleccionar caras con autointersecciones, dilatar selección y eliminarlas
        ms.compute_selection_by_self_intersections_per_face()
        ms.apply_selection_dilatation()
        if ms.current_mesh().selected_face_number() > 0:
            ms.meshing_remove_selected_faces()
            check_mesh_repaired = False

        # Seleccionar vértices no manifold y eliminarlos
        ms.compute_selection_by_non_manifold_per_vertex()
        #print("Número de non mainfold per vertex: " + str(ms.current_mesh().selected_face_number()))
        if ms.current_mesh().selected_vertex_number() > 0:
            ms.meshing_remove_selected_vertices()
            check_mesh_repaired = False
        
        previous_holes = holes
        # Cerrar agujeros pequeños
        holes = ms.meshing_close_holes(maxholesize=hole_size)
        print(f"Number of closed holes: {holes}")

        
        closed_holes = holes["closed_holes"]
        new_faces = holes["new_faces"]

        if closed_holes>0 and new_faces==0:
            delete_border_if_necessary(ms, hole_size)
            hole_size=hole_size*2
            check_mesh_repaired=False

        #esto es necesario porque a veces crea agujeros con problemas
        #pero no hay ninguna forma de arreglar esos problemas
        #entonces no para de crear agujeros con problemas
        #continuamente de manera infinita. Con esto cortamos el bucle
        #porque volvemos a eliminar el borde
        if previous_holes == holes:
            delete_border_if_necessary(ms, hole_size)
            hole_size=hole_size*2
            check_mesh_repaired=False
    
    
    output_file =file_name
    output_file = save_mesh(ms, output_file)
    
    #devolverlo con la coma lo mantiene como un argumento separado y así no 
    #cuenta cada caracter como un argumentos
    return output_file
#comprueba si la malla está reparada antes de usar el filtro de voronoia atlas
def check_mesh_repaired(ms):
    ms.compute_selection_by_small_disconnected_components_per_face()
    if ms.current_mesh().selected_face_number() > 0:
        return False
    ms.compute_selection_bad_faces()
    if ms.current_mesh().selected_face_number() > 0:
        return False
    ms.compute_selection_by_non_manifold_edges_per_face()
    if ms.current_mesh().selected_face_number() > 0:
        return False
    ms.compute_selection_by_self_intersections_per_face()
    if ms.current_mesh().selected_face_number() > 0:
        return False
    ms.compute_selection_by_non_manifold_per_vertex()
    if ms.current_mesh().selected_face_number() > 0:
        return False
    return True
def load_ply(ms, file_name):
    if not os.path.exists(file_name):
        print(f"File not founded: {file_name}")
    ms.load_new_mesh(file_name)
    #mscount = ms.mesh_number() 
    #print(mscount)
    #print("Nube de puntos cargada con éxito.")

def surface_reconstruction(ms, octree_depth=8):

    if ms.current_mesh().face_number()> 0:
            print("Error: Current mesh has no faces")
            return None

    try:
        ms.apply_filter(
            'generate_surface_reconstruction_screened_poisson',
            visiblelayer=False,    # Usar todas las capas visibles
            depth=octree_depth,               # Profundidad máxima del octree
            fulldepth=5,           # Profundidad adaptativa del octree
            cgdepth=0,             # Profundidad para el solver de gradientes conjugados
            scale=1.1,             # Factor de escala
            samplespernode=1.5,    # Muestras mínimas por nodo
            pointweight=4,         # Peso de interpolación
            iters=8,               # Iteraciones de relajación de Gauss-Seidel
            confidence=False,      # No usar la calidad como confianza
            preclean=False,        # No limpiar previamente
            threads=16             # Número de hilos a usar
        )
    except Exception as e:
        print(f"Error on the surface reconstruction: {e}")
    output_file ='screened_poisson.ply'
    output_file = save_mesh(ms, output_file)
    
    #devolverlo con la coma lo mantiene como un argumento separado y así no 
    #cuenta cada caracter como un argumentos
    return output_file

def remove_huge_unused_faces(ms):
    """
    Elimina caras demasiado grandes generadas en la reconstrucción de la superficie.
    Se pueden eliminar sábanas
    """
    try:
        # Verificar si la malla tiene caras
        if ms.current_mesh().face_number() == 0:
            print("Error: current mesh has no faces.")
            return None

        # Calcular una longitud promedio de los lados de la malla
        average_edge_length = ms.current_mesh().bounding_box().diagonal() / 100
        print(f"Average edge length (estimated): {average_edge_length}")

        # Seleccionar caras con lados grandes y eliminarlas
        ms.compute_selection_by_edge_length(threshold=average_edge_length)
        ms.meshing_remove_selected_faces()

        # Guardar la malla procesada
        output_file = "huge_faces_removed.ply"
        output_file = save_mesh(ms, output_file)

        # Devolver como tupla (para evitar que Python lo trate como caracteres separados)
        return output_file

    except AttributeError as e:
        print(f"Error: could not be possible to access the current mesh. {e}")
        return None

def delete_border_if_necessary(ms, hole_size=100):
    #elimina los bordes de los agujeros que no se pueden cerrar para eliminar posibles
    #errores topoógicos no detectados
    output_file="tmp.ply"
    folder_path = os.path.join(os.getcwd(), folder_name)  # Ruta absoluta
    os.makedirs(folder_path, exist_ok=True)
  
    # Unir la carpeta con el nombre del archivo
    # Obtener un nombre único si el archivo ya existe
    
    output_file = os.path.join(folder_path, os.path.basename(output_file))
    ms.save_current_mesh(
        file_name=output_file,
        binary=False,  # Guarda en formato binario (más compacto y compatible)
        save_vertex_quality = False,
        save_vertex_color = True,
        save_vertex_normal  = True,
        save_wedge_texcoord=False    # Guardar coordenadas UV

    )
    try:
        delete_border(output_file, output_file, hole_size)
        load_ply(ms, output_file)
        #remover el archivo temporal 
        os.remove(output_file)
    except Exception as e:
            print(f" An unexpected error occurred: {e}")

def compute_normals_if_necessary(ms,has_normals, has_faces,file_name):
    #solo usar este método si la nube de puntos no tiene normales y es efectivamente una
    #nube de puntos
    if not has_normals and not has_faces:  
        filename_sin_ext, _ = os.path.splitext(file_name)
        output_file = filename_sin_ext + "_with_normals.ply"
        try:
            #filtro para crear las normales en una malla
            normal_filter(file_name, output_file) 
            load_ply(ms, output_file)
            #remover el archivo temporal de normales 
            os.remove(output_file)
            #cambiar la malla a binario y añadirla al meshset
            output_file = save_mesh(ms, output_file)
            
    
            #retornamos el mesh id para saber qué nube de puntos utilizar para la textura
            return (output_file, )
        except FileNotFoundError:
            print(f"Error: File {file_name} wasn't found.")
        except PermissionError:
            print(f"Error: You got no permissions to access {file_name}.")
        except Exception as e:
            print(f" An unexpected error occurred: {e}")
        return None
    else:
        print(" Either the point cloud already has normals or it is not a point cloud.")
        return None
# como va a haber casos en los que usemos un mismo método mas veces, vamos a crear una funcion
# #que nos genere un nombre de archivo unico cada vez que usemos ese método
def get_unique_filename(folder_path, filename):
    """Si el archivo ya existe en la carpeta, añade un número incremental al final."""
    name, ext = os.path.splitext(filename)  # Separar nombre y extensión
    counter = 1
    new_filename = filename  # Nombre inicial

    while os.path.exists(os.path.join(folder_path, new_filename)):
        new_filename = f"{name}_{counter}{ext}"  # Añadir número antes de la extensión
        counter += 1

    return new_filename

def save_mesh(ms, output_file, save_v_color = True, save_UV=False):
     
    
    # Crear la carpeta si no existe
    folder_path = os.path.join(os.getcwd(), folder_name)  # Ruta absoluta
    os.makedirs(folder_path, exist_ok=True)
  
    # Unir la carpeta con el nombre del archivo
    # Obtener un nombre único si el archivo ya existe
    unique_filename = get_unique_filename(folder_path, os.path.basename(output_file))
    output_file = os.path.join(folder_path, os.path.basename(unique_filename))
    ms.save_current_mesh(
        file_name=output_file,
        binary=False,  # Guarda en formato binario (más compacto y compatible)
        save_vertex_quality = False,
        save_vertex_color = save_v_color,
        save_vertex_normal  = True,
        save_wedge_texcoord=save_UV    # Guardar coordenadas UV

    )
    
    return output_file

def mesh_simplification(ms, target_num_of_faces):
    if ms.current_mesh().face_number() == 0:
        print("Error: Mesh has no faces.")
        return None
    try:
        ms.apply_filter(
            'meshing_decimation_quadric_edge_collapse',
            targetfacenum=target_num_of_faces,         # Número deseado de caras finales
            targetperc=0,             # Porcentaje de reducción (0.5 significa 50%)
            qualitythr=0.3,             # Umbral de calidad para penalizar caras mal formadas
            preserveboundary=True,      # Preservar los bordes de la malla
            boundaryweight=1,         # Peso adicional para preservar bordes
            preservenormal=True,        # Preservar la orientación de las normales
            preservetopology=True,      # Mantener la topología de la malla
            optimalplacement=True,      # Colocación óptima de vértices simplificados
            planarquadric=True,         # Mejora simplificación en áreas planas
            planarweight=0.001,         # Peso de simplificación en regiones planas
            qualityweight=False,        # No usar la calidad de los vértices como peso
            autoclean=True,             # Limpieza post-simplificación
            selected=False              # Aplicar simplificación a toda la malla
        )
    except Exception as e:
        print(f"Error in surface reconstruction: {e}")

    output_file ='simplified_mesh.ply'
    output_file = save_mesh(ms, output_file)
    
    #devolverlo con la coma lo mantiene como un argumento separado y así no 
    #cuenta cada caracter como un argumentos
    return output_file

def kill_voronoi_processes():
    """Encuentra y mata todos los procesos voronoi_atlas en ejecución."""
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        try:
            if "voronoi_atlas" in proc.info["name"]:  # Filtra por nombre
                print(f"Killing voronoi_atlas process (PID: {proc.info['pid']})")
                proc.kill()  # Mata el proceso
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue  # Si ya murió o no se puede acceder, ignorar

def run_voronoi_with_timeout(input_file, output_file, timeout=15):
    """
    Ejecuta voronoi_atlas_parametrization con un límite de tiempo.
    Si se excede el tiempo, el proceso y todos sus subprocesos se terminan.
    """
    def target():
        try:
            voronoi_atlas_parametrization(input_file=input_file, output_file=output_file)
        except Exception as e:
            print(f"Error in voronoi_atlas_parametrization: {e}")

    # Crear proceso
    process = multiprocessing.Process(target=target)
    process.start()
    process.join(timeout)  # Esperar hasta 'timeout' segundos

    if process.is_alive():
        print("Voronoi Atlas stuck in infinite loop. Killing all related processes...")
        process.terminate()  # Matar el proceso principal
        process.join()  # Asegurar que finalizó

        # 🔥 Eliminar procesos zombis de voronoi_atlas
        kill_voronoi_processes()
        return False  # Indica que falló por timeout
    
    return True  # Indica que terminó correctamente
def voronoi_atlas(ms, file_name):

    #comprobar antes de aplicar este filtro que la malla esté reparada
    if check_mesh_repaired(ms) == False:
        print("Error: The mesh has not been repaired")
        return None, False
    if ms.current_mesh().face_number() == 0:
        print("Error: Mesh has no faces.")
        return None, False

  
    output_file=  "voronoi_atlas.ply"
    try:
        success = run_voronoi_with_timeout(input_file=file_name, output_file=output_file, timeout=15)
        
        if not success:
            print("Error: Voronoi Atlas did not finish in the expected time. You can try changing some variables in the right panel and redo the steps.")
            return None, False
        load_ply(ms, output_file)
        #remover el archivo temporal de normales 
        os.remove(output_file)
        #Guardar malla
        output_file = save_mesh(ms, output_file, True, True)
   

        #retornamos el mesh id para saber cuál es la malla voronoi atlas para la textura utilizar para la textura
        return (output_file, True)
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, False

def transfer_attributes_to_texture_per_vertex(ms, point_cloud_id, voronoi_id, texture_name):
   
    if ms.current_mesh().face_number() == 0:
        print("Error: Current mesh has not faces")
        return None
    uv_check = ms.current_mesh().has_wedge_tex_coord()
    if not uv_check:
        print("Error: current mesh has not texture coordinates")
        return None
    try:
        ms.apply_filter(
            'transfer_attributes_to_texture_per_vertex',
            sourcemesh=point_cloud_id,               # Índice de la malla fuente (nube de puntos)
            targetmesh=voronoi_id,               # Índice de la malla objetivo
            attributeenum='Vertex Color',  # Atributo a transferir (e.g., Vertex Color, Vertex Normal)
            upperbound= pymeshlab.PercentageValue(2),            # Distancia máxima para buscar puntos de muestra
            textname=texture_name,  # Nombre del archivo de textura a generar
            textw=1024,                 # Ancho de la textura
            texth=1024,                 # Altura de la textura
            overwrite=False,             # Sobrescribir la textura existente en la malla objetivo
            pullpush=True               # Llenar los espacios vacíos con el algoritmo pull-push
        )

        #guardamos la malal sin colores de vértices porque ya no los necesoitamos
        output_file ='target_mesh_with_texture.ply'
        output_file = save_mesh(ms, output_file, False, True)
        
        return output_file
    except Exception as e:
        print(f"An error ocurred: {e}")