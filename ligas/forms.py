from django import forms

from typing import Iterable

from django.core.exceptions import ValidationError

from .models import Categoria, Club, Liga


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


class ResultadoPartidoFixtureForm(forms.Form):
    """Formulario dinámico para capturar resultados por categoría."""

    error_message = "Ingrese un entero ≥ 0"

    def __init__(self, categorias: Iterable[Categoria], *args, **kwargs):
        self.categorias = list(categorias)
        super().__init__(*args, **kwargs)

        for categoria in self.categorias:
            self.fields[self._field_name(categoria, "local")] = forms.IntegerField(
                min_value=0,
                required=False,
                label="",
                error_messages={"min_value": self.error_message, "invalid": self.error_message},
            )
            self.fields[self._field_name(categoria, "visitante")] = forms.IntegerField(
                min_value=0,
                required=False,
                label="",
                error_messages={"min_value": self.error_message, "invalid": self.error_message},
            )

    @staticmethod
    def _field_name(categoria: Categoria, rol: str) -> str:
        return f"categoria_{categoria.pk}_{rol}"

    def clean(self):
        cleaned_data = super().clean()
        for categoria in self.categorias:
            local_key = self._field_name(categoria, "local")
            visitante_key = self._field_name(categoria, "visitante")
            local = cleaned_data.get(local_key)
            visitante = cleaned_data.get(visitante_key)

            if (local is None) ^ (visitante is None):
                # Forzamos que ambos estén informados o ninguno
                if local is None:
                    self.add_error(local_key, self.error_message)
                if visitante is None:
                    self.add_error(visitante_key, self.error_message)
        return cleaned_data

    def iter_resultados(self):
        """Yield ``(categoria, goles_local, goles_visitante)`` for categorías cargadas."""

        if not self.is_valid():
            raise ValidationError("El formulario contiene errores.")

        for categoria in self.categorias:
            local = self.cleaned_data.get(self._field_name(categoria, "local"))
            visitante = self.cleaned_data.get(self._field_name(categoria, "visitante"))
            if local is None or visitante is None:
                yield categoria, None, None
            else:
                yield categoria, local, visitante
