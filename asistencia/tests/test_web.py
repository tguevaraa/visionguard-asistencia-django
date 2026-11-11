"""Pruebas de servicios y vistas (requieren base de datos; usan un MEDIA_ROOT temporal)."""
import shutil
import tempfile
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from asistencia import servicios
from asistencia.models import Asistencia, Empleado
from asistencia.vision.procesador import ReconocedorLBPH

from .utilidades import rostro_sintetico

TMP = Path(tempfile.mkdtemp(prefix="vg-test-"))


@override_settings(MEDIA_ROOT=TMP, VG_RUTA_MODELO=TMP / "modelo" / "lbph.yml", VG_ESPERA_SEGUNDOS=60)
class ServiciosTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        self.ana = Empleado.objects.create(codigo=1001, nombre="Ana Pérez", cargo="Analista")

    def test_registra_y_respeta_tiempo_de_espera(self):
        t0 = timezone.now()
        self.assertIsNotNone(servicios.registrar_asistencia(1001, 35.2, ahora=t0))
        self.assertIsNone(servicios.registrar_asistencia(1001, 30.0, ahora=t0 + timedelta(seconds=30)))
        self.assertIsNotNone(servicios.registrar_asistencia(1001, 30.0, ahora=t0 + timedelta(seconds=61)))
        self.assertEqual(Asistencia.objects.count(), 2)

    def test_no_registra_empleado_inactivo_o_inexistente(self):
        self.ana.activo = False
        self.ana.save()
        self.assertIsNone(servicios.registrar_asistencia(1001, 20))
        self.assertIsNone(servicios.registrar_asistencia(9999, 20))

    def test_guardar_muestras_y_entrenar(self):
        luis = Empleado.objects.create(codigo=1002, nombre="Luis Mora")
        servicios.guardar_muestras(self.ana, [rostro_sintetico(1, ruido=i) for i in range(1, 6)])
        servicios.guardar_muestras(luis, [rostro_sintetico(2, ruido=i) for i in range(1, 6)])
        rec = ReconocedorLBPH(70, 200)

        r = servicios.entrenar_modelo(rec)

        self.assertEqual(r, {"muestras": 10, "personas": 2})
        self.assertTrue((TMP / "modelo" / "lbph.yml").exists())
        self.assertEqual(rec.predecir(rostro_sintetico(2, ruido=9))[0], 1002)

    def test_eliminar_empleado_borra_sus_datos_y_reentrena(self):
        luis = Empleado.objects.create(codigo=1002, nombre="Luis Mora")
        servicios.guardar_muestras(self.ana, [rostro_sintetico(1, ruido=i) for i in range(1, 6)])
        servicios.guardar_muestras(luis, [rostro_sintetico(2, ruido=i) for i in range(1, 6)])
        servicios.registrar_asistencia(1001, 30)
        rec = ReconocedorLBPH(70, 200)
        servicios.entrenar_modelo(rec)

        r = servicios.eliminar_empleado(self.ana, rec)

        self.assertEqual(r, {"asistencias": 1, "modelo": "reentrenado"})
        self.assertFalse(Empleado.objects.filter(codigo=1001).exists())
        self.assertEqual(Asistencia.objects.count(), 0)
        self.assertFalse(any((TMP / "rostros" / "1001").glob("*.png")))
        self.assertNotEqual(rec.predecir(rostro_sintetico(1, ruido=9))[0], 1001)  # ya no existe en el modelo
        self.assertEqual(rec.predecir(rostro_sintetico(2, ruido=9))[0], 1002)

    def test_eliminar_al_ultimo_empleado_descarta_el_modelo(self):
        servicios.guardar_muestras(self.ana, [rostro_sintetico(1, ruido=i) for i in range(1, 6)])
        rec = ReconocedorLBPH(70, 200)
        servicios.entrenar_modelo(rec)

        r = servicios.eliminar_empleado(self.ana, rec)

        self.assertEqual(r["modelo"], "sin muestras")
        self.assertFalse(rec.entrenado)
        self.assertFalse((TMP / "modelo" / "lbph.yml").exists())

    def test_entrenar_sin_muestras_avisa(self):
        with self.assertRaises(ValueError):
            servicios.entrenar_modelo(ReconocedorLBPH(70, 200))


class VistasTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="clave-prueba-123", is_staff=True)
        self.operador = User.objects.create_user("operador", password="clave-prueba-123")
        self.ana = Empleado.objects.create(codigo=1001, nombre="Ana Pérez", cargo="Analista")
        Asistencia.objects.create(empleado=self.ana, fecha_hora=timezone.now(), distancia=32.4)

    def test_paginas_exigen_inicio_de_sesion(self):
        for nombre in ("panel", "empleados", "asistencias", "exportar_excel", "estado"):
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 302, nombre)
            self.assertIn(reverse("login"), r.url)

    def test_login_y_listados(self):
        self.client.login(username="operador", password="clave-prueba-123")
        self.assertContains(self.client.get(reverse("empleados")), "Ana Pérez")
        self.assertContains(self.client.get(reverse("asistencias")), "1 registro")

    def test_admin_registra_empleado(self):
        self.client.login(username="admin", password="clave-prueba-123")
        r = self.client.post(reverse("empleados"), {"codigo": 1002, "nombre": "  Luis   Mora ", "activo": "on"})
        luis = Empleado.objects.get(codigo=1002)
        self.assertRedirects(r, reverse("empleado_detalle", args=[luis.pk]))
        self.assertEqual(luis.nombre, "Luis Mora")

    def test_codigo_duplicado_es_rechazado(self):
        self.client.login(username="admin", password="clave-prueba-123")
        r = self.client.post(reverse("empleados"), {"codigo": 1001, "nombre": "Otra Persona"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Empleado.objects.count(), 1)

    def test_operador_no_puede_registrar_ni_entrenar(self):
        self.client.login(username="operador", password="clave-prueba-123")
        self.client.post(reverse("empleados"), {"codigo": 1003, "nombre": "Intruso"})
        self.assertFalse(Empleado.objects.filter(codigo=1003).exists())
        self.assertEqual(self.client.post(reverse("entrenar")).status_code, 302)
        self.client.post(reverse("eliminar_empleado", args=[self.ana.pk]))
        self.assertTrue(Empleado.objects.filter(pk=self.ana.pk).exists())

    def test_exportar_excel(self):
        self.client.login(username="operador", password="clave-prueba-123")
        r = self.client.get(reverse("exportar_excel"))
        self.assertEqual(r["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        hoja = load_workbook(BytesIO(r.content)).active
        self.assertEqual(hoja["D2"].value, "Ana Pérez")
        self.assertEqual(hoja["F2"].value, 68)

    def test_filtro_por_fechas_invalido(self):
        self.client.login(username="operador", password="clave-prueba-123")
        r = self.client.get(reverse("asistencias"), {"desde": "2026-12-31", "hasta": "2026-01-01"})
        self.assertContains(r, "no puede ser posterior")
