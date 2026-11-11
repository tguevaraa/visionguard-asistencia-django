# VisionGuard AI · Control de asistencia por reconocimiento facial

Aplicativo web en **Django** que captura video en tiempo real, lo procesa con **OpenCV**
(detección Haar Cascade + reconocimiento **LBPH**), registra la asistencia de los empleados
reconocidos en **PostgreSQL** y muestra los resultados en una interfaz web interactiva.

> Práctica 3 · Construcción de Software · UNEMI — Enfoque elegido:
> **detección de rostros para control de asistencia**.

## Funcionalidades

| Módulo | Qué hace |
|---|---|
| Inicio de sesión | Acceso con usuarios de Django. Administrador (`is_staff`) gestiona; operador solo consulta. |
| Panel en vivo | Video MJPEG procesado: cajas verdes (reconocido), rojas (desconocido), azules (modelo sin entrenar), con nombre y distancia LBPH dibujados sobre el video. Indicadores de cámara, FPS, presentes y registros del día, actualizados cada segundo. |
| Empleados | Alta y edición de empleados (código, nombre, cargo, activo). Captura de 20 muestras de rostro desde la cámara y galería de muestras. |
| Entrenamiento | Entrena el modelo LBPH con las muestras guardadas y lo pone en uso sin reiniciar el servidor. |
| Registro automático | Una asistencia se registra cuando la misma persona es reconocida en **5 cuadros seguidos**, y no se repite dentro de **60 s** (configurable). |
| Asistencias | Listado con filtros por fecha y empleado, porcentaje de confianza y **exportación a Excel**. |

## Arquitectura

```
Cámara ─► Hilo ServicioVideo (asistencia/vision/camara.py)
            captura → DetectorRostros (Haar) → ReconocedorLBPH → ConfirmadorIdentidad
                 │                                                 │
                 ▼                                                 ▼
           último JPEG anotado                       servicios.registrar_asistencia()
                 │                                                 │
   /video/ (multipart MJPEG)  /api/estado/ (JSON)          ORM Django ─► PostgreSQL
                 └────────────── Navegador (plantillas + panel.js) ◄─┘
```

- `asistencia/vision/` — OpenCV puro, sin Django: se prueba y reutiliza de forma aislada.
- `asistencia/servicios.py` — reglas de negocio (espera entre registros, captura, entrenamiento).
- `asistencia/views.py` — vistas delgadas que delegan en los servicios.
- `legacy/` — versión de escritorio original (Tkinter), conservada como referencia.

## Requisitos

- Python 3.11 o 3.12
- PostgreSQL 14+ (o Docker para levantarlo con `docker compose`)
- Una cámara web (o un archivo de video, ver `VG_FUENTE_VIDEO`)

## Instalación

```bash
git clone https://github.com/tommylguevara/VisionGuard-Asistencia-AI.git
cd VisionGuard-Asistencia-AI
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Linux/macOS: cp .env.example .env
```

Base de datos (elija una opción):

```bash
# a) con Docker
docker compose up -d

# b) con PostgreSQL instalado: crear usuario y base
psql -U postgres -c "CREATE USER visionguard WITH PASSWORD 'visionguard' CREATEDB;"
psql -U postgres -c "CREATE DATABASE visionguard OWNER visionguard;"
```

Migrar, crear el administrador y ejecutar:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abrir <http://127.0.0.1:8000/> e ingresar con el usuario creado.

## Uso

1. **Empleados → Registrar empleado** (código numérico único, nombre, cargo).
2. En la ficha del empleado, con **solo esa persona** frente a la cámara, pulsar **Capturar muestras**.
3. Repetir para cada persona y pulsar **Entrenar modelo**.
4. Abrir el **Panel en vivo**: al reconocer a alguien 5 cuadros seguidos se registra su entrada.
5. **Asistencias**: filtrar y **Exportar a Excel**.

## Configuración (`.env`)

| Variable | Defecto | Descripción |
|---|---|---|
| `POSTGRES_*` | `visionguard` / `localhost:5432` | Conexión a PostgreSQL |
| `VG_FUENTE_VIDEO` | `0` | Índice de cámara o ruta a un video |
| `VG_UMBRAL_LBPH` | `70` | Distancia máxima aceptada (menor = más estricto) |
| `VG_CUADROS_CONFIRMACION` | `5` | Cuadros seguidos para confirmar identidad |
| `VG_ESPERA_SEGUNDOS` | `60` | Tiempo mínimo entre dos registros de la misma persona |
| `VG_MUESTRAS_POR_CAPTURA` | `20` | Muestras por captura |
| `VG_USAR_SQLITE` | — | `1` para una prueba rápida sin PostgreSQL |

## Pruebas

```bash
python manage.py test asistencia
```

Cubren el reconocedor LBPH (personas conocidas y desconocidas), la confirmación por cuadros
consecutivos, el flujo completo del hilo de video con cuadros sintéticos, la regla de espera
entre registros, el entrenamiento desde la base de datos, los permisos por rol, la validación
de formularios y la exportación a Excel.

## Equipo

| Integrante | Rol |
|---|---|
| Tommy Guevara | Líder del proyecto y desarrollador de visión artificial (OpenCV) |
| Ezequiel Rosales | Desarrollador backend (Django + PostgreSQL) |
| Emily Hidalgo | Diseñadora UI y desarrolladora frontend |
| Holger Ferruzola | Responsable de pruebas (QA) y del video demostrativo |
| Kattia Arreaga | Responsable de documentación y gestión de riesgos |

## Tecnologías

Python · Django 5.2 · OpenCV (opencv-contrib-python: Haar Cascade + LBPH) · PostgreSQL ·
psycopg 3 · openpyxl · HTML/CSS/JavaScript.
