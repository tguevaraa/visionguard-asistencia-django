from django.db import models


class Empleado(models.Model):
    """Persona que el sistema debe reconocer. ``codigo`` es la etiqueta LBPH."""

    codigo = models.PositiveIntegerField("código", unique=True)
    nombre = models.CharField(max_length=120)
    cargo = models.CharField(max_length=80, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    @property
    def total_muestras(self):
        return self.muestras.count()


class MuestraRostro(models.Model):
    """Recorte de rostro en escala de grises usado para entrenar el modelo."""

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="muestras")
    imagen = models.ImageField(upload_to="rostros/")
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creada"]


class Asistencia(models.Model):
    """Registro de entrada producido por un reconocimiento confirmado."""

    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name="asistencias")
    fecha_hora = models.DateTimeField(db_index=True)
    distancia = models.FloatField(help_text="Distancia LBPH: menor es más parecido.")

    class Meta:
        ordering = ["-fecha_hora"]

    def __str__(self):
        return f"{self.empleado.nombre} · {self.fecha_hora:%Y-%m-%d %H:%M:%S}"

    @property
    def confianza(self):
        """Distancia LBPH expresada como porcentaje aproximado de confianza (0–100)."""
        return max(0, min(100, round(100 - self.distancia)))
