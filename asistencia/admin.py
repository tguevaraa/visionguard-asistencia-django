from django.contrib import admin

from .models import Asistencia, Empleado, MuestraRostro


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "cargo", "activo", "total_muestras")
    search_fields = ("nombre", "codigo")
    list_filter = ("activo",)


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ("empleado", "fecha_hora", "distancia")
    list_filter = ("fecha_hora",)
    date_hierarchy = "fecha_hora"


admin.site.register(MuestraRostro)
admin.site.site_header = "VisionGuard AI · Administración"
