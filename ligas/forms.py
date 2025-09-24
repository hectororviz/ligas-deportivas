from django import forms

from .models import Club, Liga


class EquipoGenerateForm(forms.Form):
    club = forms.ModelChoiceField(
        queryset=Club.objects.all().order_by("nombre"),
        label="Club",
    )
    liga = forms.ModelChoiceField(
        queryset=Liga.objects.all().order_by("-temporada", "nombre"),
        label="Liga",
        help_text="Se crearán equipos para todas las categorías asociadas a la liga seleccionada.",
    )
