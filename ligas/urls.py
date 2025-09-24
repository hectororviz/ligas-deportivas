from django.urls import path

from . import views
from .abm_views import (
    AdminHomeView,
    LigaListView, LigaCreateView, LigaUpdateView, LigaDeleteView,
    ClubListView, ClubCreateView, ClubUpdateView, ClubDeleteView,
    TorneoListView, TorneoCreateView, TorneoUpdateView, TorneoDeleteView, TorneoFixtureView,
    PartidoFixtureResultadoView,
    RondaListView, RondaCreateView, RondaUpdateView, RondaDeleteView,
    CategoriaListView, CategoriaCreateView, CategoriaUpdateView, CategoriaDeleteView,
    EquipoListView, EquipoCreateView, EquipoGenerateView, EquipoUpdateView, EquipoDeleteView,
    EquipoDetailView,
    JugadorListView, JugadorCreateView, JugadorUpdateView, JugadorDeleteView,
    ArbitroListView, ArbitroCreateView, ArbitroUpdateView, ArbitroDeleteView,
    IdentidadView,
)

app_name = "ligas"

urlpatterns = [
    # público/home
    path("", views.home, name="home"),

    # administración (non-admin)
    path("administracion/", AdminHomeView.as_view(), name="admin_home"),

    path("administracion/ligas/", LigaListView.as_view(), name="liga_list"),
    path("administracion/ligas/nueva/", LigaCreateView.as_view(), name="liga_create"),
    path("administracion/ligas/<int:pk>/editar/", LigaUpdateView.as_view(), name="liga_update"),
    path("administracion/ligas/<int:pk>/eliminar/", LigaDeleteView.as_view(), name="liga_delete"),

    path("administracion/clubes/", ClubListView.as_view(), name="club_list"),
    path("administracion/clubes/nuevo/", ClubCreateView.as_view(), name="club_create"),
    path("administracion/clubes/<int:pk>/editar/", ClubUpdateView.as_view(), name="club_update"),
    path("administracion/clubes/<int:pk>/eliminar/", ClubDeleteView.as_view(), name="club_delete"),

    path("administracion/torneos/", TorneoListView.as_view(), name="torneo_list"),
    path("administracion/torneos/nuevo/", TorneoCreateView.as_view(), name="torneo_create"),
    path("administracion/torneos/<int:pk>/editar/", TorneoUpdateView.as_view(), name="torneo_update"),
    path("administracion/torneos/<int:pk>/eliminar/", TorneoDeleteView.as_view(), name="torneo_delete"),
    path("administracion/torneos/<int:pk>/fixture/", TorneoFixtureView.as_view(), name="torneo_fixture"),
    path(
        "administracion/torneos/<int:pk>/fixture/<int:partido_id>/resultados/",
        PartidoFixtureResultadoView.as_view(),
        name="partido_fixture_resultados",
    ),

    path("administracion/rondas/", RondaListView.as_view(), name="ronda_list"),
    path("administracion/rondas/nuevo/", RondaCreateView.as_view(), name="ronda_create"),
    path("administracion/rondas/<int:pk>/editar/", RondaUpdateView.as_view(), name="ronda_update"),
    path("administracion/rondas/<int:pk>/eliminar/", RondaDeleteView.as_view(), name="ronda_delete"),

    path("administracion/categorias/", CategoriaListView.as_view(), name="categoria_list"),
    path("administracion/categorias/nuevo/", CategoriaCreateView.as_view(), name="categoria_create"),
    path("administracion/categorias/<int:pk>/editar/", CategoriaUpdateView.as_view(), name="categoria_update"),
    path("administracion/categorias/<int:pk>/eliminar/", CategoriaDeleteView.as_view(), name="categoria_delete"),

    path("administracion/equipos/", EquipoListView.as_view(), name="equipo_list"),
    path("administracion/equipos/generar/", EquipoGenerateView.as_view(), name="equipo_generate"),
    path("administracion/equipos/<int:pk>/", EquipoDetailView.as_view(), name="equipo_detail"),
    path("administracion/equipos/nuevo/", EquipoCreateView.as_view(), name="equipo_create"),
    path("administracion/equipos/<int:pk>/editar/", EquipoUpdateView.as_view(), name="equipo_update"),
    path("administracion/equipos/<int:pk>/eliminar/", EquipoDeleteView.as_view(), name="equipo_delete"),

    path("administracion/jugadores/", JugadorListView.as_view(), name="jugador_list"),
    path("administracion/jugadores/nuevo/", JugadorCreateView.as_view(), name="jugador_create"),
    path("administracion/jugadores/<int:pk>/editar/", JugadorUpdateView.as_view(), name="jugador_update"),
    path("administracion/jugadores/<int:pk>/eliminar/", JugadorDeleteView.as_view(), name="jugador_delete"),

    path("administracion/arbitros/", ArbitroListView.as_view(), name="arbitro_list"),
    path("administracion/arbitros/nuevo/", ArbitroCreateView.as_view(), name="arbitro_create"),
    path("administracion/arbitros/<int:pk>/editar/", ArbitroUpdateView.as_view(), name="arbitro_update"),
    path("administracion/arbitros/<int:pk>/eliminar/", ArbitroDeleteView.as_view(), name="arbitro_delete"),

    # configuración
    path("configuracion/identidad/", IdentidadView.as_view(), name="identidad"),
]
