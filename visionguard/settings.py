"""Configuración de VisionGuard AI.

Los valores sensibles y de entorno se leen de variables de entorno (o de un
archivo ``.env`` en la raíz del proyecto; ver ``.env.example``).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(nombre, defecto=False):
    return os.environ.get(nombre, str(defecto)).strip().lower() in {"1", "true", "si", "sí", "yes"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "solo-para-desarrollo-cambiar-en-produccion")
DEBUG = _bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "asistencia",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "visionguard.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "visionguard.wsgi.application"

# --- Base de datos: PostgreSQL (requisito de la práctica) ---------------------
# VG_USAR_SQLITE=1 permite una prueba rápida sin servidor PostgreSQL.
if _bool("VG_USAR_SQLITE"):
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "visionguard"),
            "USER": os.environ.get("POSTGRES_USER", "visionguard"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "visionguard"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "panel"
LOGOUT_REDIRECT_URL = "login"

# --- Visión artificial ---------------------------------------------------------
# Fuente de video: índice de cámara ("0") o ruta a un archivo de video.
VG_FUENTE_VIDEO = os.environ.get("VG_FUENTE_VIDEO", "0")
# Distancia LBPH máxima para aceptar un reconocimiento (menor = más estricto).
VG_UMBRAL_LBPH = float(os.environ.get("VG_UMBRAL_LBPH", "70"))
# Cuadros consecutivos con la misma identidad antes de registrar la asistencia.
VG_CUADROS_CONFIRMACION = int(os.environ.get("VG_CUADROS_CONFIRMACION", "5"))
# Tiempo mínimo entre dos registros de la misma persona.
VG_ESPERA_SEGUNDOS = int(os.environ.get("VG_ESPERA_SEGUNDOS", "60"))
# Muestras de rostro que se toman al registrar a un empleado.
VG_MUESTRAS_POR_CAPTURA = int(os.environ.get("VG_MUESTRAS_POR_CAPTURA", "20"))
# Tamaño (px) al que se normaliza cada rostro antes de entrenar/predecir.
VG_TAMANO_ROSTRO = 200
VG_RUTA_MODELO = MEDIA_ROOT / "modelo" / "lbph.yml"
VG_RUTA_ROSTROS = MEDIA_ROOT / "rostros"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "loggers": {"asistencia": {"handlers": ["consola"], "level": "INFO"}},
}
