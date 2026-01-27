# VisionGuard AI - Sistema de Asistencia Biométrico 👁️📊

**VisionGuard AI** es una aplicación de escritorio robusta desarrollada en Python que moderniza el control de asistencia empresarial. Utiliza visión artificial y algoritmos de aprendizaje automático (LBPH) para identificar empleados en tiempo real, registrando sus horas de entrada automáticamente y permitiendo la exportación de reportes a Excel.

## 🚀 Características Principales

* **Reconocimiento Facial en Tiempo Real:** Implementación del algoritmo **LBPH (Local Binary Patterns Histograms)** mediante OpenCV para una identificación precisa y ligera.
* **Gestión de Empleados (CRUD):** Registro de personal con ID, Nombre y Cargo, con persistencia de datos en formato **JSON**.
* **Entrenamiento de Modelo Integrado:** Módulo capaz de capturar dataset de rostros, procesar imágenes en escala de grises y entrenar la IA directamente desde la interfaz.
* **Sistema Anti-Spam de Logs:** Lógica inteligente que evita registros duplicados inmediatos (Cooldown de 1 minuto entre detecciones).
* **Exportación de Reportes:** Generación automática de archivos `.xlsx` (Excel) con nombres dinámicos basados en la fecha y hora para evitar conflictos de escritura.
* **Compatibilidad con Ejecutables:** El código incluye manejo de rutas relativas y absolutas (`sys.frozen`) para funcionar perfectamente al ser compilado con **PyInstaller**.

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3.x
* **Interfaz Gráfica (GUI):** Tkinter (ttk) con manejo de imágenes mediante Pillow.
* **Visión Artificial:** `opencv-contrib-python` (Haar Cascades + LBPHFaceRecognizer).
* **Manejo de Datos:** `pandas` y `openpyxl` para reportes; `json` para base de datos local.
* **Estructura:** Arquitectura modular separando lógica de negocio (`modelo.py`) de la interfaz (`interfaz.py`).

## 📋 Pre-requisitos e Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/TU_USUARIO/VisionGuard-Asistencia-AI.git](https://github.com/TU_USUARIO/VisionGuard-Asistencia-AI.git)
    cd VisionGuard-Asistencia-AI
    ```

2.  **Instalar dependencias:**
    El proyecto incluye un archivo `requirements.txt` con las librerías necesarias.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Ejecutar la aplicación:**
    ```bash
    python interfaz.py
    ```

## 📂 Estructura del Proyecto

* `interfaz.py`: **Frontend**. Controla la ventana, la cámara, el ciclo de video y la interacción con el usuario. Incluye la lógica para exportar a Excel.
* `modelo.py`: **Backend**. Define las clases `Empleado
