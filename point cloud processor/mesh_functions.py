import subprocess

def voronoi_atlas_parametrization(input_file, output_file, sample_num=None):
    """
    Ejecuta el programa `voronoi_atlas` con los argumentos proporcionados.

    Args:
        input_file (str): Archivo de entrada en formato PLY.
        output_file (str): Archivo de salida en formato PLY.
        sample_num (int, optional): Número de muestras adicionales. Por defecto, None.

    Raises:
        RuntimeError: Si el ejecutable retorna un error.
        FileNotFoundError: Si el ejecutable no se encuentra.
    """
    executable = "./voronoi_atlas"
    # Construye el comando con los argumentos obligatorios y opcionales
    command = [executable, input_file, output_file]
    if sample_num is not None:
        command.append(str(sample_num))
    
    try:
        # Ejecuta el comando
        result = subprocess.run(
            command,
            check=True,          # Lanza una excepción si el comando falla
            capture_output=False, # Captura stdout y stderr
            text=False           # Decodifica la salida como texto
        )
        #print("Ejecución exitosa:")
        #print(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Runtime Error {executable}: {e.stderr}") from e
    except FileNotFoundError:
        raise FileNotFoundError(f"It wasn't possible to find the file: {executable}")
    


def normal_filter(input_file, output_file, fitting_adj_num=None, smoothing_iter_num=None,
                   use_view_point=None, view_point_x=None, view_point_y=None, view_point_z=None):
    """
    Ejecuta el programa `normal_filter` con los argumentos proporcionados.

    Args:
        input_file (str): Archivo de entrada en formato PLY.
        output_file (str): Archivo de salida en formato PLY.
        fitting_adj_num (int, optional): Número de vecinos para el ajuste de normales.
        smoothing_iter_num (int, optional): Número de iteraciones de suavizado.
        use_view_point (bool, optional): Activar el uso del punto de vista.
        view_point_x (float, optional): Coordenada X del punto de vista.
        view_point_y (float, optional): Coordenada Y del punto de vista.
        view_point_z (float, optional): Coordenada Z del punto de vista.

    Raises:
        RuntimeError: Si el ejecutable retorna un error.
        FileNotFoundError: Si el ejecutable no se encuentra.
    """
    executable = "./normal_filter"
    
    # Construcción del comando con los argumentos obligatorios
    command = [executable, input_file, output_file]

    # Agrega los argumentos opcionales si se proporcionan
    if fitting_adj_num is not None:
        command.append(str(fitting_adj_num))
    if smoothing_iter_num is not None:
        command.append(str(smoothing_iter_num))
    if use_view_point is not None:
        command.append(str(int(use_view_point)))  # Convierte bool a 1 o 0
    if view_point_x is not None and view_point_y is not None and view_point_z is not None:
        command.extend([str(view_point_x), str(view_point_y), str(view_point_z)])

    try:
        # Ejecuta el comando
        result = subprocess.run(
            command,
            check=True,          # Lanza una excepción si el comando falla
            capture_output=False, # Captura stdout y stderr
            text=True            # Decodifica la salida como texto
        )
        #print("Ejecución exitosa:")
        #print(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Runtime Error {executable}: {e.stderr}") from e
    except FileNotFoundError:
        raise FileNotFoundError(f"It wasn't possible to find the file: {executable}")
    
def delete_border(input_file, output_file, hole_size=100):
    """
    Ejecuta el programa `delete_border` con los argumentos proporcionados.

    Args:
        input_file (str): Archivo de entrada en formato PLY.
        output_file (str): Archivo de salida en formato PLY.
        hole_size (int, optional): Tamaño del agujero a eliminar. Por defecto, None.

    Raises:
        RuntimeError: Si el ejecutable retorna un error.
        FileNotFoundError: Si el ejecutable no se encuentra.
    """
    executable = "./delete_border"
    
    # Construcción del comando con los argumentos obligatorios
    command = [executable, input_file, output_file]

    # Agrega el argumento opcional si se proporciona
    if hole_size is not None:
        command.append(str(hole_size))

    try:
        # Ejecuta el comando
        result = subprocess.run(
            command,
            check=True,          # Lanza una excepción si el comando falla
            capture_output=False, # No captura stdout ni stderr
            text=True            # Decodifica la salida como texto
        )
        #print("Ejecución exitosa:")
        #print(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Runtime Error {executable}: {e.stderr}") from e
    except FileNotFoundError:
        raise FileNotFoundError(f"It wasn't possible to find the file: {executable}")