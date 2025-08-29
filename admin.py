from django.contrib import admin
from .models import (
    Club, Liga, Torneo, Ronda, Categoria, Equipo, Jugador, Arbitro,
    Fecha, Partido, EventoPartido, ReglaPuntos, TablaPosicion
)
admin.site.register([Club, Liga, Torneo, Ronda, Categoria, Equipo, Jugador, Arbitro,
                     Fecha, Partido, EventoPartido, ReglaPuntos, TablaPosicion])
