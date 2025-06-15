# Configuración del entorno en Windows + WSL

Este documento describe los pasos necesarios para configurar correctamente el entorno en **WSL (Windows Subsystem for Linux)** para ejecutar el programa con interfaz gráfica basada en PyQt5 y renderizado en OpenGL.

## Requisitos previos

En WSL no se dispone de un servidor gráfico nativo. Para que las aplicaciones gráficas basadas en Qt, GTK u OpenGL funcionen correctamente, es necesario instalar un **servidor X** en Windows que permita mostrar las ventanas renderizadas desde Linux.

### 1. Instalar VcXsrv

Se debe instalar el servidor X [**VcXsrv Windows X Server**](https://sourceforge.net/projects/vcxsrv/).

### 2. Configuración de VcXsrv

Al iniciar VcXsrv, se deben seguir estos pasos en su asistente:

1. **Multiple Windows**
2. **Start No Client**
3. **Disable Access Control**

Esto permitirá abrir ventanas gráficas desde WSL sin problemas de permisos o compatibilidad.

## Configuración en WSL

### 3. Variables de entorno (añadir en `.bashrc`)

Editar el archivo `~/.bashrc` y añadir al final las siguientes líneas:

```bash
export DISPLAY=localhost:0
export QT_X11_NO_MITSHM=1
export XDG_RUNTIME_DIR=/tmp/runtime-root
mkdir -p $XDG_RUNTIME_DIR
chmod 700 $XDG_RUNTIME_DIR
``` 

### 4. Rutas de PyQt5 y librerías Qt

También es necesario asegurarse de que se está utilizando la versión correcta de Qt para PyQt5 y pymeshlab:

```bash
export PYQT_PATH=$(python3 -c "import sys; print(sys.prefix)")/local/lib/python3.10/dist-packages/PyQt5
export LD_LIBRARY_PATH="$PYQT_PATH/Qt5/lib:$LD_LIBRARY_PATH"
```

> La variable `PYQT_PATH` se generaliza automáticamente usando Python para que funcione independientemente del entorno WSL del usuario.

---
Importante: hacer source ~/.bashrc para que se actualicen los cambios
##  Requisitos del proyecto (`requirements.txt`)

```txt
PyQt5>=5.15
PyOpenGL>=3.1.6
pymeshlab>=2022.2
matplotlib>=3.5
numpy>=1.21
plyfile>=0.7.4
psutil
```

---

## Figura: Pasos para abrir el servidor gráfico VcXsrv  
![image](https://github.com/user-attachments/assets/e382f752-a15e-4d46-bf7c-ec12fa7ff8bb)


---

## Notas finales

- Verifica que tu distribución WSL tenga habilitado el acceso a Internet y permisos para abrir sockets locales.
- Puedes automatizar la configuración usando un script de instalación.
