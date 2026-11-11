from django.urls import path

from . import views

urlpatterns = [
    path("", views.panel, name="panel"),
    path("video/", views.video, name="video"),
    path("api/estado/", views.estado, name="estado"),
    path("empleados/", views.empleados, name="empleados"),
    path("empleados/<int:pk>/", views.empleado_detalle, name="empleado_detalle"),
    path("empleados/<int:pk>/capturar/", views.capturar, name="capturar"),
    path("empleados/<int:pk>/borrar-muestras/", views.borrar_muestras, name="borrar_muestras"),
    path("empleados/<int:pk>/eliminar/", views.eliminar_empleado, name="eliminar_empleado"),
    path("modelo/entrenar/", views.entrenar, name="entrenar"),
    path("asistencias/", views.asistencias, name="asistencias"),
    path("asistencias/excel/", views.exportar_excel, name="exportar_excel"),
]
