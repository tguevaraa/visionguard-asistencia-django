"""Captura de video en un hilo de fondo y transmisión MJPEG al navegador.

Un único hilo lee la cámara, detecta y reconoce rostros, dibuja los resultados
sobre el cuadro y deja disponible el último JPEG. Las vistas solo leen ese
estado, así varios navegadores pueden ver el video sin abrir la cámara dos veces.
"""
from __future__ import annotations

import logging
import sys
import threading
import time
from collections import deque
from typing import Callable

import cv2

from .procesador import Deteccion, DetectorRostros, ReconocedorLBPH, anotar, cuadro_sin_senal, normalizar_rostro

log = logging.getLogger("asistencia.vision")


class ConfirmadorIdentidad:
    """Exige N cuadros consecutivos con la misma identidad antes de confirmar.

    Evita registrar asistencias por un reconocimiento aislado (falso positivo).
    """

    def __init__(self, cuadros_requeridos: int):
        self.requeridos = max(1, cuadros_requeridos)
        self._conteos: dict[int, int] = {}

    def observar(self, etiquetas: set[int]) -> list[int]:
        confirmadas = []
        self._conteos = {e: self._conteos.get(e, 0) + 1 for e in etiquetas}
        for etiqueta, conteo in self._conteos.items():
            if conteo == self.requeridos:
                confirmadas.append(etiqueta)
        return confirmadas


class ServicioVideo:
    def __init__(
        self,
        fuente: str,
        reconocedor: ReconocedorLBPH,
        tamano_rostro: int,
        cuadros_confirmacion: int,
        al_confirmar: Callable[[int, float], str | None] | None = None,
        nombres: Callable[[], dict[int, str]] | None = None,
    ):
        self.fuente = int(fuente) if str(fuente).isdigit() else fuente
        self.reconocedor = reconocedor
        self.detector = DetectorRostros()
        self.tamano = tamano_rostro
        self.confirmador = ConfirmadorIdentidad(cuadros_confirmacion)
        self.al_confirmar = al_confirmar
        self._proveedor_nombres = nombres or (lambda: {})
        self._nombres: dict[int, str] = {}
        self._nombres_t = 0.0

        self._hilo: threading.Thread | None = None
        self._detener = threading.Event()
        self._cond = threading.Condition()
        self.jpeg: bytes | None = None
        self.numero_cuadro = 0
        self.gris = None
        self.cajas: list[tuple[int, int, int, int]] = []
        self.detecciones: list[Deteccion] = []
        self.conectada = False
        self.fps = 0.0
        self.eventos = deque(maxlen=20)  # mensajes recientes para el panel

    # ------------------------------------------------------------------ ciclo
    def iniciar(self):
        if self._hilo and self._hilo.is_alive():
            return
        self._detener.clear()
        self._hilo = threading.Thread(target=self._bucle, name="VisionGuard-video", daemon=True)
        self._hilo.start()

    def detener(self):
        self._detener.set()
        if self._hilo:
            self._hilo.join(timeout=3)

    def invalidar_nombres(self):
        self._nombres_t = 0.0

    def _abrir(self):
        if isinstance(self.fuente, int) and sys.platform == "win32":
            cap = cv2.VideoCapture(self.fuente, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(self.fuente)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return cap

    def _bucle(self):
        cap = self._abrir()
        t_prev = time.perf_counter()
        while not self._detener.is_set():
            ok, cuadro = cap.read() if cap.isOpened() else (False, None)
            if not ok and isinstance(self.fuente, str) and cap.isOpened():
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # archivo de video: repetir
                ok, cuadro = cap.read()
            if not ok:
                self.conectada = False
                self._publicar(cuadro_sin_senal(), None, [], [])
                cap.release()
                time.sleep(2)
                cap = self._abrir()
                continue

            self.conectada = True
            try:
                self.procesar(cuadro)
            except Exception:  # el video nunca debe caerse por un error puntual
                log.exception("Error procesando un cuadro")
            ahora = time.perf_counter()
            self.fps = 0.9 * self.fps + 0.1 * (1.0 / max(ahora - t_prev, 1e-3))
            t_prev = ahora
            if isinstance(self.fuente, str):
                time.sleep(1 / 25)  # archivo: respetar velocidad aproximada
        cap.release()

    # ----------------------------------------------------------- procesamiento
    def _nombre(self, etiqueta: int) -> str:
        if time.monotonic() - self._nombres_t > 10:
            try:
                self._nombres = self._proveedor_nombres()
            except Exception:
                log.exception("No se pudieron leer los nombres de empleados")
            self._nombres_t = time.monotonic()
        return self._nombres.get(etiqueta, f"ID {etiqueta}")

    def procesar(self, cuadro):
        gris = cv2.cvtColor(cuadro, cv2.COLOR_BGR2GRAY)
        cajas = self.detector.detectar(gris)
        detecciones = []
        for caja in cajas:
            d = Deteccion(*caja)
            if self.reconocedor.entrenado:
                etiqueta, distancia = self.reconocedor.predecir(normalizar_rostro(gris, caja, self.tamano))
                d.distancia = distancia
                if etiqueta is not None:
                    d.etiqueta, d.nombre = etiqueta, self._nombre(etiqueta)
            else:
                d.nombre = "Rostro"
            detecciones.append(d)

        for etiqueta in self.confirmador.observar({d.etiqueta for d in detecciones if d.reconocido}):
            if self.al_confirmar:
                distancia = min(d.distancia for d in detecciones if d.etiqueta == etiqueta)
                mensaje = self.al_confirmar(etiqueta, distancia)
                if mensaje:
                    self.eventos.appendleft({"hora": time.strftime("%H:%M:%S"), "mensaje": mensaje})

        modelo = "modelo entrenado" if self.reconocedor.entrenado else "modelo SIN entrenar"
        estado = f"Rostros: {len(cajas)}  |  {self.fps:4.1f} fps  |  {modelo}"
        self._publicar(anotar(cuadro, detecciones, estado), gris, cajas, detecciones)

    def _publicar(self, cuadro, gris, cajas, detecciones):
        ok, buf = cv2.imencode(".jpg", cuadro, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with self._cond:
            if ok:
                self.jpeg = buf.tobytes()
            self.gris, self.cajas, self.detecciones = gris, cajas, detecciones
            self.numero_cuadro += 1
            self._cond.notify_all()

    # ------------------------------------------------------------- consumidores
    def esperar_cuadro(self, ultimo: int, timeout: float = 2.0) -> int:
        with self._cond:
            self._cond.wait_for(lambda: self.numero_cuadro != ultimo, timeout=timeout)
            return self.numero_cuadro

    def flujo_mjpeg(self):
        self.iniciar()
        ultimo = -1
        while not self._detener.is_set():
            ultimo = self.esperar_cuadro(ultimo)
            jpeg = self.jpeg
            if jpeg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"

    def tomar_rostros(self, cantidad: int, timeout: float = 15.0):
        """Devuelve hasta ``cantidad`` recortes normalizados de cuadros con UN solo rostro."""
        self.iniciar()
        rostros, ultimo, limite = [], -1, time.monotonic() + timeout
        while len(rostros) < cantidad and time.monotonic() < limite:
            ultimo = self.esperar_cuadro(ultimo, timeout=1.0)
            with self._cond:
                gris, cajas = self.gris, list(self.cajas)
            if gris is not None and len(cajas) == 1:
                rostros.append(normalizar_rostro(gris, cajas[0], self.tamano))
                time.sleep(0.1)  # espaciar muestras para variar pose/expresión
        return rostros
