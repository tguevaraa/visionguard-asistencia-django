from django import forms

from .models import Empleado


class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ["codigo", "nombre", "cargo", "activo"]
        widgets = {
            "codigo": forms.NumberInput(attrs={"min": 1, "placeholder": "Ej. 1001"}),
            "nombre": forms.TextInput(attrs={"placeholder": "Nombres y apellidos"}),
            "cargo": forms.TextInput(attrs={"placeholder": "Ej. Analista"}),
        }

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if len(nombre) < 3:
            raise forms.ValidationError("Escriba el nombre completo.")
        return nombre


class FiltroAsistenciaForm(forms.Form):
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    empleado = forms.ModelChoiceField(queryset=Empleado.objects.all(), required=False, empty_label="Todos")

    def clean(self):
        datos = super().clean()
        if datos.get("desde") and datos.get("hasta") and datos["desde"] > datos["hasta"]:
            raise forms.ValidationError("La fecha 'desde' no puede ser posterior a 'hasta'.")
        return datos
