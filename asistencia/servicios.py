"""Reglas de negocio de VisionGuard. Las vistas delegan aquí; aquí no hay HTTP."""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import timedelta

import cv2
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import close_old_connections
from django.utils import timezone

from .models import Asistencia, Empleado, MuestraRostro
from .vision.camara import ServicioVideo
from .vision.procesador import ReconocedorLBPH

log = logging.getLogger("asistencia")

_servicio: ServicioVideo | None = None
_lock = threading.Lock()


# ---------------------------------------------------------------- asistencias
def registrar_asistencia(codigo: int, distancia: float, ahora=None) -> Asistencia | None:
    """Registra la entrada si la persona no tiene otra dentro de la ventana de espera."""
    ahora = ahora or timezone.now()
    empleado = Empleado.objects.filter(codigo=codigo, activo=True).first()
    if empleado is None:
        return None
    desde = ahora - timedelta(seconds=settings.VG_ESPERA_SEGUNDOS)
    if empleado.asistencias.filter(fecha_hora__gt=desde).exists():
        return None
    return Asistencia.objects.create(empleado=empleado, fecha_hora=ahora, distancia=round(distancia, 2))


def _al_confirmar(codigo: int, distancia: float) -> str | None:
    """Callback del hilo de video: corre fuera de una petición, maneja su conexión."""
    close_old_connections()
    try:
        a = registrar_asistencia(codigo, distancia)
        if a:
            log.info("Asistencia registrada: %s", a)
            return f"Asistencia registrada: {a.empleado.nombre}"
        return None
    finally:
        close_old_connections()


def _nombres_activos() -> dict[int, str]:
    close_old_connections()
    try:
        return dict(Empleado.objects.filter(activo=True).values_list("codigo", "nombre"))
    finally:
        close_old_connections()


# --------------------------------------------------------------- video/modelo
def obtener_servicio() -> ServicioVideo:
    global _servicio
    with _lock:
        if _servicio is None:
            reconocedor = ReconocedorLBPH(settings.VG_UMBRAL_LBPH, settings.VG_TAMANO_ROSTRO)
            if reconocedor.cargar(settings.VG_RUTA_MODELO):
                log.info("Modelo LBPH cargado desde %s", settings.VG_RUTA_MODELO)
            _servicio = ServicioVideo(
                fuente=settings.VG_FUENTE_VIDEO,
                reconocedor=reconocedor,
                tamano_rostro=settings.VG_TAMANO_ROSTRO,
                cuadros_confirmacion=settings.VG_CUADROS_CONFIRMACION,
                al_confirmar=_al_confirmar,
                nombres=_nombres_activos,
            )
        return _servicio


def guardar_muestras(empleado: Empleado, rostros) -> int:
    """Guarda recortes de rostro (arreglos en gris) como muestras del empleado."""
    guardadas = 0
    for rostro in rostros:
        ok, buf = cv2.imencode(".png", rostro)
        if not ok:
            continue
        nombre = f"{empleado.codigo}/{uuid.uuid4().hex[:12]}.png"
        muestra = MuestraRostro(empleado=empleado)
        muestra.imagen.save(nombre, ContentFile(buf.tobytes()), save=True)
        guardadas += 1
    return guardadas


def capturar_muestras(empleado: Empleado) -> int:
    rostros = obtener_servicio().tomar_rostros(settings.VG_MUESTRAS_POR_CAPTURA)
    return guardar_muestras(empleado, rostros)


def entrenar_modelo(reconocedor: ReconocedorLBPH | None = None) -> dict:
    """Entrena LBPH con las muestras de empleados activos y lo pone en uso."""
    rostros, etiquetas = [], []
    muestras = MuestraRostro.objects.filter(empleado__activo=True).select_related("empleado")
    for m in muestras:
        img = cv2.imread(m.imagen.path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        if img.shape != (settings.VG_TAMANO_ROSTRO, settings.VG_TAMANO_ROSTRO):
            img = cv2.resize(img, (settings.VG_TAMANO_ROSTRO, settings.VG_TAMANO_ROSTRO))
        rostros.append(img)
        etiquetas.append(m.empleado.codigo)
    if not rostros:
        raise ValueError("No hay muestras de rostro. Capture fotos de al menos un empleado.")

    reconocedor = reconocedor or obtener_servicio().reconocedor
    reconocedor.entrenar(rostros, etiquetas, settings.VG_RUTA_MODELO)
    if _servicio is not None:
        _servicio.invalidar_nombres()
    return {"muestras": len(rostros), "personas": len(set(etiquetas))}
