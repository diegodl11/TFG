# Importa la biblioteca PyMeshLab
import pymeshlab
import numpy as np
import os

file_name : str = 'C:/Users/diego/OneDrive/Escritorio/TFG/material/Modelos/prueba python/BustOfNefertitti.ply'
if not os.path.exists(file_name):
    print(f"Archivo no encontrado: {file_name}")

# Crea un nuevo objeto MeshSet, que representa el estado actual de MeshLab
# Este objeto contiene un conjunto de mallas y permite aplicar filtros sobre ellas
ms = pymeshlab.MeshSet()

# Cargar una nueva malla desde un archivo
# Cambia 'airplane.obj' por la ruta de tu archivo de malla


ms.load_new_mesh(file_name)
print("Nube de puntos cargada con éxito.")


"""
# Generar el casco convexo (convex hull) de la malla cargada
# Esto crea una aproximación de la malla como un volumen convexo
ms.generate_convex_hull()
print("Casco convexo generado.")


# Guardar la malla procesada en un nuevo archivo
# Cambia 'convex_hull.ply' por la ruta y el nombre de salida deseado
ms.save_current_mesh('convex_hull.ply')
print("Malla guardada con éxito.")

# Listar todos los filtros disponibles en PyMeshLab
# Esto imprime una lista de los filtros que puedes aplicar con sus nombres y descripciones
print("Lista de filtros disponibles:")
pymeshlab.print_filter_list()
"""
k_neighbors = 10  # Número de vecinos
smooth_iterations = 0  # Sin iteraciones de suavizado
flip_normals = False  # No voltear las normales
viewpoint_position = np.array([0, 0, 0])  # Posición de la cámara (puedes ajustarlo)

# Aplica el filtro

#ms.apply_filter('compute_normal_for_point_clouds', k=k_neighbors, smoothiter=smooth_iterations, flipflag=flip_normals, viewpos=viewpoint_position)
ms.compute_normal_for_point_clouds(k=k_neighbors, smoothiter=smooth_iterations, 
                flipflag=flip_normals, viewpos=viewpoint_position)

#Returns the number of meshes contained in the MeshSet.
#assert ms.mesh_number() == 2

# Guarda el resultado con las normales calculadas
ms.save_current_mesh('point_cloud_with_normals.ply')



ms.apply_filter(
    'generate_surface_reconstruction_screened_poisson',
    visiblelayer=False,    # Usar todas las capas visibles
    depth=8,               # Profundidad máxima del octree
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

# Guardar la malla reconstruida
output_file = 'reconstructed_mesh.ply'
ms.save_current_mesh(output_file)
print(f"Malla creada en {output_file}")


# Aplicar el filtro 'Simplification: Quadric Edge Collapse Decimation'
# Configura los parámetros según tus necesidades
ms.apply_filter(
    'meshing_decimation_quadric_edge_collapse',
    targetfacenum=10000,         # Número deseado de caras finales
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

# Guardar la malla simplificada
output_file = 'simplified_mesh.ply'
ms.save_current_mesh(output_file)

print(f"Malla simplificada guardada en {output_file}")


ms.load_new_mesh('C:/Users/diego/OneDrive/Escritorio/TFG/material/Modelos/prueba python/prueba.ply')


# Aplicar el filtro 'Parametrization: Voronoi Atlas'
# Configura los parámetros según tus necesidades
ms.apply_filter(
    'generate_voronoi_atlas_parametrization',
    regionnum=10,          # Número aproximado de regiones
    overlapflag=False      # Generar regiones superpuestas (útil para mipmaps)
)

# Guardar la malla parametrizada
output_file = 'voronoi_atlas_mesh.ply'
ms.save_current_mesh(output_file)
print(f"Malla textura guardada en {output_file}")



#mscount = ms.mesh_number() 
#print(f"Número de mallas presentes en el MeshSet: {mscount}")

uv_check = ms.current_mesh().has_wedge_tex_coord()
print(f"La malla objetivo tiene coordenadas UV: {uv_check}")

ms.apply_filter(
    'transfer_attributes_to_texture_per_vertex',
    sourcemesh=0,               # Índice de la malla fuente
    targetmesh=3,               # Índice de la malla objetivo
    attributeenum='Vertex Color',  # Atributo a transferir (e.g., Vertex Color, Vertex Normal)
    upperbound= pymeshlab.PercentageValue(2),            # Distancia máxima para buscar puntos de muestra
    textname='transferred_texture.png',  # Nombre del archivo de textura a generar
    textw=1024,                 # Ancho de la textura
    texth=1024,                 # Altura de la textura
    overwrite=True,             # Sobrescribir la textura existente en la malla objetivo
    pullpush=True               # Llenar los espacios vacíos con el algoritmo pull-push
)

# Guardar la malla objetivo con la textura aplicada
output_mesh_file = 'target_mesh_with_texture.ply'
ms.save_current_mesh(output_mesh_file)

print(f"Malla objetivo con la textura transferida guardada en {output_mesh_file}")


"""
# Listar los parámetros de un filtro específico
# Cambia el nombre del filtro para explorar otros
print("\nParámetros del filtro 'generate_surface_reconstruction_screened_poisson':")
pymeshlab.print_filter_parameter_list('generate_surface_reconstruction_screened_poisson')

# Aplicar un filtro con parámetros específicos
# En este caso, se genera una isosuperficie ruidosa con resolución personalizada
ms.create_noisy_isosurface(resolution=128)
print("Isosuperficie ruidosa generada.")

# Buscar filtros relacionados con una palabra clave, por ejemplo 'poisson'
# Esto ayuda a localizar filtros relevantes en la biblioteca
print("\nFiltros relacionados con 'poisson':")
pymeshlab.search('poisson')

# Aplicar un filtro que devuelve valores
# Por ejemplo, obtener medidas geométricas de la malla actual
out_dict = ms.get_geometric_measures()
print("\nMedidas geométricas de la malla:")
print(f"Área de superficie: {out_dict['surface_area']}")

# Fin del script
print("Proceso completo.")
"""