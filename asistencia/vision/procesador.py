"""Detección (Haar Cascade) y reconocimiento (LBPH) de rostros con OpenCV.

Este módulo no depende de Django: recibe y devuelve arreglos de NumPy, lo que
permite probarlo de forma aislada y reutilizarlo fuera de la web.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

VERDE = (60, 200, 60)
ROJO = (40, 40, 230)
AZUL = (230, 140, 40)


@dataclass
class Deteccion:
    x: int
    y: int
    w: int
    h: int
    etiqueta: int | None = None  # código del empleado, None si es desconocido
    distancia: float | None = None
    nombre: str = "Desconocido"

    @property
    def reconocido(self) -> bool:
        return self.etiqueta is not None


class DetectorRostros:
    def __init__(self, ruta_cascada: str | None = None):
        ruta = ruta_cascada or cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.cascada = cv2.CascadeClassifier(ruta)
        if self.cascada.empty():
            raise RuntimeError(f"No se pudo cargar el clasificador Haar: {ruta}")

    def detectar(self, gris: np.ndarray) -> list[tuple[int, int, int, int]]:
        gris = cv2.equalizeHist(gris)
        caras = self.cascada.detectMultiScale(gris, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
        return [tuple(int(v) for v in c) for c in caras]


def normalizar_rostro(gris: np.ndarray, caja: tuple[int, int, int, int], tamano: int) -> np.ndarray:
    x, y, w, h = caja
    recorte = gris[y : y + h, x : x + w]
    recorte = cv2.resize(recorte, (tamano, tamano))
    return cv2.equalizeHist(recorte)


class ReconocedorLBPH:
    """Envoltura con bloqueo para poder reentrenar mientras el video corre."""

    def __init__(self, umbral: float, tamano: int):
        self.umbral = umbral
        self.tamano = tamano
        self._modelo = None
        self._lock = threading.Lock()

    @property
    def entrenado(self) -> bool:
        return self._modelo is not None

    def cargar(self, ruta: Path) -> bool:
        if not Path(ruta).exists():
            return False
        modelo = cv2.face.LBPHFaceRecognizer_create()
        modelo.read(str(ruta))
        with self._lock:
            self._modelo = modelo
        return True

    def entrenar(self, rostros: list[np.ndarray], etiquetas: list[int], ruta: Path | None = None) -> None:
        if not rostros:
            raise ValueError("No hay muestras para entrenar.")
        if len(set(etiquetas)) < 1:
            raise ValueError("Se necesita al menos una persona con muestras.")
        modelo = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)
        modelo.train(rostros, np.array(etiquetas, dtype=np.int32))
        if ruta is not None:
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            modelo.write(str(ruta))
        with self._lock:
            self._modelo = modelo

    def predecir(self, rostro: np.ndarray) -> tuple[int | None, float]:
        with self._lock:
            if self._modelo is None:
                return None, float("inf")
            etiqueta, distancia = self._modelo.predict(rostro)
        if distancia <= self.umbral:
            return int(etiqueta), float(distancia)
        return None, float(distancia)


def anotar(cuadro: np.ndarray, detecciones: list[Deteccion], texto_estado: str) -> np.ndarray:
    """Dibuja cajas, nombres y una barra de estado directamente sobre el video."""
    for d in detecciones:
        color = VERDE if d.reconocido else (ROJO if d.distancia is not None else AZUL)
        cv2.rectangle(cuadro, (d.x, d.y), (d.x + d.w, d.y + d.h), color, 2)
        rotulo = d.nombre
        if d.distancia is not None and d.distancia != float("inf"):
            rotulo += f" ({d.distancia:.0f})"
        (tw, th), _ = cv2.getTextSize(rotulo, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        y_txt = max(d.y - 8, th + 6)
        cv2.rectangle(cuadro, (d.x, y_txt - th - 6), (d.x + tw + 8, y_txt + 4), color, -1)
        cv2.putText(cuadro, rotulo, (d.x + 4, y_txt), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    alto = cuadro.shape[0]
    cv2.rectangle(cuadro, (0, alto - 28), (cuadro.shape[1], alto), (20, 20, 20), -1)
    cv2.putText(cuadro, texto_estado, (10, alto - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (235, 235, 235), 1)
    return cuadro


def cuadro_sin_senal(ancho: int = 640, alto: int = 480, mensaje: str = "Sin senal de camara") -> np.ndarray:
    cuadro = np.full((alto, ancho, 3), 30, dtype=np.uint8)
    (tw, _), _ = cv2.getTextSize(mensaje, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    cv2.putText(cuadro, mensaje, ((ancho - tw) // 2, alto // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)
    return cuadro
