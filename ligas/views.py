from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .fixture import (
    FixtureAlreadyExists,
    FixtureGenerationError,
    crear_fixture_para_torneo,
    obtener_clubes_para_fixture,
)
from .models import FixturePartido, Torneo


def home(request):
    return render(request, "ligas/home.html")


def torneo_fixture(request, pk):
    torneo = get_object_or_404(Torneo.objects.select_related("liga"), pk=pk)
    partidos = list(
        FixturePartido.objects.filter(torneo=torneo)
        .select_related("local", "visitante")
        .order_by("ronda", "fecha_nro", "id")
    )

    rondas = [
        (FixturePartido.RONDA_IDA, "Ronda 1 (Ida)"),
        (FixturePartido.RONDA_VUELTA, "Ronda 2 (Vuelta)"),
    ]

    partidos_por_ronda: dict[int, OrderedDict[int, list[FixturePartido]]] = {
        ronda: OrderedDict() for ronda, _ in rondas
    }
    for partido in partidos:
        fechas = partidos_por_ronda[partido.ronda]
        fechas.setdefault(partido.fecha_nro, []).append(partido)

    clubes = obtener_clubes_para_fixture(torneo)
    clubes_por_id = {club.pk: club for club in clubes}
    club_ids = set(clubes_por_id.keys())

    fixture = []
    for ronda, label in rondas:
        fechas_info = []
        for fecha, lista_partidos in partidos_por_ronda[ronda].items():
            jugados_ids = {p.local_id for p in lista_partidos} | {
                p.visitante_id for p in lista_partidos
            }
            libres = [
                clubes_por_id[cid]
                for cid in sorted(club_ids - jugados_ids)
                if cid in clubes_por_id
            ]
            fechas_info.append(
                {
                    "numero": fecha,
                    "partidos": lista_partidos,
                    "libres": libres,
                }
            )
        fixture.append(
            {
                "ronda": ronda,
                "label": label,
                "fechas": fechas_info,
            }
        )

    context = {
        "torneo": torneo,
        "fixture": fixture,
        "clubes": clubes,
        "fixture_exists": bool(partidos),
        "can_create_fixture": request.user.has_perm("ligas.add_fixturepartido"),
        "create_url": reverse("ligas:torneo_fixture_create", args=[torneo.pk]),
    }
    return render(request, "ligas/torneo_fixture.html", context)


@login_required
@permission_required("ligas.add_fixturepartido", raise_exception=True)
@require_POST
def torneo_fixture_create(request, pk):
    torneo = get_object_or_404(Torneo.objects.select_related("liga"), pk=pk)
    try:
        crear_fixture_para_torneo(torneo)
    except FixtureAlreadyExists:
        messages.info(request, "El fixture ya había sido generado previamente.")
    except FixtureGenerationError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Fixture generado correctamente.")
    return redirect("ligas:torneo_fixture", pk=torneo.pk)
