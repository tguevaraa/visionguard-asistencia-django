"""Pruebas del módulo de visión (sin base de datos ni cámara)."""
from unittest import TestCase

import numpy as np

from asistencia.vision.camara import ConfirmadorIdentidad, ServicioVideo
from asistencia.vision.procesador import (
    Deteccion, DetectorRostros, ReconocedorLBPH, anotar, cuadro_sin_senal, normalizar_rostro,
)

from .utilidades import rostro_sintetico


class ReconocedorLBPHTests(TestCase):
    def setUp(self):
        self.rec = ReconocedorLBPH(umbral=70, tamano=200)
        rostros = [rostro_sintetico(s, ruido=i) for s in (1, 2) for i in range(1, 6)]
        etiquetas = [1001] * 5 + [1002] * 5
        self.rec.entrenar(rostros, etiquetas)

    def test_sin_entrenar_no_reconoce(self):
        vacio = ReconocedorLBPH(umbral=70, tamano=200)
        self.assertFalse(vacio.entrenado)
        self.assertEqual(vacio.predecir(rostro_sintetico(1))[0], None)

    def test_reconoce_a_cada_persona(self):
        self.assertEqual(self.rec.predecir(rostro_sintetico(1, ruido=9))[0], 1001)
        self.assertEqual(self.rec.predecir(rostro_sintetico(2, ruido=9))[0], 1002)

    def test_rechaza_desconocido_por_umbral(self):
        etiqueta, distancia = self.rec.predecir(rostro_sintetico(77))
        self.assertIsNone(etiqueta)
        self.assertGreater(distancia, 70)

    def test_entrenar_sin_muestras_falla(self):
        with self.assertRaises(ValueError):
            ReconocedorLBPH(70, 200).entrenar([], [])


class ConfirmadorTests(TestCase):
    def test_confirma_solo_al_llegar_a_n_cuadros_seguidos(self):
        c = ConfirmadorIdentidad(3)
        self.assertEqual(c.observar({7}), [])
        self.assertEqual(c.observar({7}), [])
        self.assertEqual(c.observar({7}), [7])
        self.assertEqual(c.observar({7}), [])  # no repite mientras siga presente

    def test_interrupcion_reinicia_el_conteo(self):
        c = ConfirmadorIdentidad(2)
        c.observar({7})
        c.observar(set())
        self.assertEqual(c.observar({7}), [])
        self.assertEqual(c.observar({7}), [7])


class ProcesadorTests(TestCase):
    def test_detector_carga_cascada_y_no_ve_rostros_en_imagen_plana(self):
        d = DetectorRostros()
        self.assertEqual(d.detectar(np.full((240, 320), 128, np.uint8)), [])

    def test_normalizar_rostro_devuelve_tamano_fijo(self):
        gris = np.zeros((480, 640), np.uint8)
        self.assertEqual(normalizar_rostro(gris, (10, 10, 90, 120), 200).shape, (200, 200))

    def test_anotar_conserva_dimensiones(self):
        cuadro = cuadro_sin_senal()
        salida = anotar(cuadro, [Deteccion(10, 10, 100, 100, 5, 40.0, "Ana")], "estado")
        self.assertEqual(salida.shape, (480, 640, 3))


class ServicioVideoTests(TestCase):
    """Procesa cuadros sintéticos con un detector simulado y verifica el flujo completo."""

    def test_reconocimiento_confirmado_dispara_registro(self):
        rec = ReconocedorLBPH(umbral=70, tamano=200)
        rec.entrenar([rostro_sintetico(1, ruido=i) for i in range(1, 6)], [1001] * 5)
        llamadas = []
        servicio = ServicioVideo("no-existe.mp4", rec, 200, cuadros_confirmacion=3,
                                 al_confirmar=lambda e, d: llamadas.append(e) or "ok",
                                 nombres=lambda: {1001: "Ana Pérez"})
        servicio.detector.detectar = lambda gris: [(100, 50, 200, 200)]

        cuadro = np.zeros((480, 640, 3), np.uint8)
        cuadro[50:250, 100:300] = rostro_sintetico(1, ruido=8)[..., None]
        for _ in range(4):
            servicio.procesar(cuadro.copy())

        self.assertEqual(llamadas, [1001])
        self.assertEqual(servicio.detecciones[0].nombre, "Ana Pérez")
        self.assertTrue(servicio.jpeg.startswith(b"\xff\xd8"))  # JPEG válido
        self.assertEqual(servicio.eventos[0]["mensaje"], "ok")
