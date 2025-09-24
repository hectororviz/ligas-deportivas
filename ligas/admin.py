from django.contrib import admin
from .models import (
    Club, Liga, Torneo, Ronda, Categoria, Equipo,
    Jugador, Arbitro, Fecha, Partido, PartidoFixture,
    EventoPartido, ReglaPuntos, TablaPosicion
)

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)

@admin.register(Liga)
class LigaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "temporada")
    list_filter = ("temporada",)
    search_fields = ("nombre", "temporada")

@admin.register(Torneo)
class TorneoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "liga")
    list_filter = ("liga__temporada", "liga__nombre")
    search_fields = ("nombre",)

@admin.register(Ronda)
class RondaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "torneo")
    list_filter = ("torneo__liga__temporada", "torneo__nombre")
    search_fields = ("nombre",)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "liga", "activa", "suma_puntos_general", "horario")
    list_filter = ("liga__temporada", "liga__nombre", "activa", "suma_puntos_general")
    search_fields = ("nombre",)

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ("club", "categoria", "alias")
    list_filter = ("categoria__liga__temporada", "categoria__nombre", "club__nombre")
    search_fields = ("club__nombre", "alias")

@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    list_display = ("apellido", "nombre", "equipo", "dni")
    list_filter = ("equipo__categoria__nombre",)
    search_fields = ("apellido", "nombre", "dni")

@admin.register(Arbitro)
class ArbitroAdmin(admin.ModelAdmin):
    list_display = ("apellido", "nombre")
    search_fields = ("apellido", "nombre")

@admin.register(Fecha)
class FechaAdmin(admin.ModelAdmin):
    list_display = ("numero", "ronda", "fecha")
    list_filter = ("ronda__torneo__liga__temporada", "ronda__torneo__nombre")
    search_fields = ("ronda__nombre",)

@admin.register(Partido)
class PartidoAdmin(admin.ModelAdmin):
    list_display = ("fecha_ref", "categoria", "local", "visitante", "goles_local", "goles_visitante", "jugado")
    list_filter = ("categoria__liga__temporada", "categoria__nombre", "jugado")
    search_fields = ("local__club__nombre", "visitante__club__nombre")
    autocomplete_fields = ("arbitro", "local", "visitante", "categoria")


@admin.register(PartidoFixture)
class PartidoFixtureAdmin(admin.ModelAdmin):
    list_display = ("torneo", "ronda", "fecha_nro", "club_local", "club_visitante", "jugado")
    list_filter = ("torneo__liga__temporada", "torneo__nombre", "ronda", "jugado")
    search_fields = ("club_local__nombre", "club_visitante__nombre", "torneo__nombre")
    autocomplete_fields = ("torneo", "club_local", "club_visitante")

@admin.register(EventoPartido)
class EventoPartidoAdmin(admin.ModelAdmin):
    list_display = ("partido", "tipo", "minuto", "equipo", "jugador")
    list_filter = ("tipo",)
    search_fields = ("detalle",)

@admin.register(ReglaPuntos)
class ReglaPuntosAdmin(admin.ModelAdmin):
    list_display = ("categoria", "puntos_victoria", "puntos_empate", "puntos_derrota")

@admin.register(TablaPosicion)
class TablaPosicionAdmin(admin.ModelAdmin):
    list_display = ("categoria", "equipo", "puntos", "pj", "pg", "pe", "pp", "gf", "gc")
    list_filter = ("categoria__liga__temporada", "categoria__nombre")
    search_fields = ("equipo__club__nombre",)
