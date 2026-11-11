from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from . import servicios
from .forms import EmpleadoForm, FiltroAsistenciaForm
from .models import Asistencia, Empleado, MuestraRostro

solo_administrador = user_passes_test(lambda u: u.is_active and u.is_staff, login_url="login")


def _asistencias_hoy():
    inicio = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return Asistencia.objects.filter(fecha_hora__gte=inicio).select_related("empleado")


# --------------------------------------------------------------------- panel
@login_required
def panel(request):
    hoy = _asistencias_hoy()
    contexto = {
        "total_empleados": Empleado.objects.filter(activo=True).count(),
        "presentes_hoy": hoy.values("empleado").distinct().count(),
        "registros_hoy": hoy.count(),
        "modelo_entrenado": servicios.obtener_servicio().reconocedor.entrenado,
        "ultimas": hoy[:8],
        "cuadros_confirmacion": settings.VG_CUADROS_CONFIRMACION,
    }
    return render(request, "asistencia/panel.html", contexto)


@login_required
def video(request):
    servicio = servicios.obtener_servicio()
    respuesta = StreamingHttpResponse(
        servicio.flujo_mjpeg(), content_type="multipart/x-mixed-replace; boundary=frame"
    )
    respuesta["Cache-Control"] = "no-store"
    return respuesta


@login_required
def estado(request):
    s = servicios.obtener_servicio()
    s.iniciar()
    hoy = _asistencias_hoy()
    return JsonResponse(
        {
            "camara_conectada": s.conectada,
            "fps": round(s.fps, 1),
            "modelo_entrenado": s.reconocedor.entrenado,
            "detecciones": [
                {"nombre": d.nombre, "reconocido": d.reconocido,
                 "distancia": None if d.distancia in (None, float("inf")) else round(d.distancia, 1)}
                for d in s.detecciones
            ],
            "eventos": list(s.eventos)[:6],
            "presentes_hoy": hoy.values("empleado").distinct().count(),
            "registros_hoy": hoy.count(),
            "ultimas": [
                {"nombre": a.empleado.nombre, "cargo": a.empleado.cargo,
                 "hora": timezone.localtime(a.fecha_hora).strftime("%H:%M:%S"), "confianza": a.confianza}
                for a in hoy[:8]
            ],
        }
    )


# ----------------------------------------------------------------- empleados
@login_required
def empleados(request):
    form = EmpleadoForm()
    if request.method == "POST":
        if not request.user.is_staff:
            messages.error(request, "Solo un administrador puede registrar empleados.")
            return redirect("empleados")
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            emp = form.save()
            messages.success(request, f"{emp.nombre} registrado. Ahora capture sus muestras de rostro.")
            return redirect("empleado_detalle", pk=emp.pk)
    lista = Empleado.objects.all()
    return render(request, "asistencia/empleados.html", {"form": form, "empleados": lista})


@login_required
def empleado_detalle(request, pk):
    emp = get_object_or_404(Empleado, pk=pk)
    form = EmpleadoForm(instance=emp)
    if request.method == "POST" and request.user.is_staff:
        form = EmpleadoForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos actualizados.")
            return redirect("empleado_detalle", pk=pk)
    return render(
        request,
        "asistencia/empleado_detalle.html",
        {"empleado": emp, "form": form, "muestras": emp.muestras.all()[:40],
         "muestras_objetivo": settings.VG_MUESTRAS_POR_CAPTURA},
    )


@solo_administrador
@require_POST
def capturar(request, pk):
    emp = get_object_or_404(Empleado, pk=pk)
    n = servicios.capturar_muestras(emp)
    if n == 0:
        messages.error(request, "No se detectó un único rostro frente a la cámara. Intente de nuevo.")
    else:
        messages.success(request, f"Se guardaron {n} muestras. Recuerde entrenar el modelo.")
    return redirect("empleado_detalle", pk=pk)


@solo_administrador
@require_POST
def borrar_muestras(request, pk):
    emp = get_object_or_404(Empleado, pk=pk)
    for m in emp.muestras.all():
        m.imagen.delete(save=False)
        m.delete()
    messages.info(request, "Muestras eliminadas. Entrene el modelo para aplicar el cambio.")
    return redirect("empleado_detalle", pk=pk)


@solo_administrador
@require_POST
def eliminar_empleado(request, pk):
    emp = get_object_or_404(Empleado, pk=pk)
    nombre = emp.nombre
    r = servicios.eliminar_empleado(emp)
    messages.success(request, f"{nombre} fue eliminado junto con sus muestras y {r['asistencias']} asistencia(s).")
    return redirect("empleados")


@solo_administrador
@require_POST
def entrenar(request):
    try:
        r = servicios.entrenar_modelo()
        messages.success(request, f"Modelo entrenado con {r['muestras']} muestras de {r['personas']} persona(s).")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect(request.POST.get("siguiente") or "empleados")


# --------------------------------------------------------------- asistencias
def _filtrar(request):
    form = FiltroAsistenciaForm(request.GET or None)
    qs = Asistencia.objects.select_related("empleado")
    if form.is_valid():
        d = form.cleaned_data
        if d.get("desde"):
            qs = qs.filter(fecha_hora__date__gte=d["desde"])
        if d.get("hasta"):
            qs = qs.filter(fecha_hora__date__lte=d["hasta"])
        if d.get("empleado"):
            qs = qs.filter(empleado=d["empleado"])
    return form, qs


@login_required
def asistencias(request):
    form, qs = _filtrar(request)
    return render(request, "asistencia/asistencias.html",
                  {"form": form, "asistencias": qs[:500], "total": qs.count(), "query": request.GET.urlencode()})


@login_required
def exportar_excel(request):
    _, qs = _filtrar(request)
    wb = Workbook()
    ws = wb.active
    ws.title = "Asistencias"
    encabezado = ["Fecha", "Hora", "Código", "Empleado", "Cargo", "Confianza (%)"]
    ws.append(encabezado)
    for celda in ws[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F3A5F")
    for a in qs:
        local = timezone.localtime(a.fecha_hora)
        ws.append([local.date(), local.strftime("%H:%M:%S"), a.empleado.codigo,
                   a.empleado.nombre, a.empleado.cargo, a.confianza])
    for col, ancho in zip("ABCDEF", (12, 10, 10, 32, 22, 14)):
        ws.column_dimensions[col].width = ancho

    buf = BytesIO()
    wb.save(buf)
    nombre = f"asistencias_{timezone.localtime():%Y-%m-%d_%H-%M}.xlsx"
    resp = HttpResponse(buf.getvalue(),
                        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return resp
