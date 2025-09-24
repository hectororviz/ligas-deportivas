"""Utilidades para generar y consultar fixture de torneos."""

from __future__ import annotations

from collections.abc import Iterable
from typing import List, Optional

from django.db import transaction

from .models import Club, FixturePartido, Torneo


class FixtureGenerationError(Exception):
    """Errores genéricos al generar el fixture."""


class FixtureAlreadyExists(FixtureGenerationError):
    """Se lanza cuando el torneo ya tiene partidos generados."""


def obtener_clubes_para_fixture(torneo: Torneo) -> List[Club]:
    """Obtiene los clubes participantes ordenados de forma estable."""

    return list(
        Club.objects.filter(equipos__categoria__liga=torneo.liga)
        .distinct()
        .order_by("nombre", "pk")
    )


def _emparejar(
    arreglo: List[Optional[Club]],
) -> Iterable[tuple[Optional[Club], Optional[Club]]]:
    n = len(arreglo)
    for i in range(n // 2):
        yield arreglo[i], arreglo[n - 1 - i]


def _rotar(arreglo: List[Optional[Club]]) -> List[Optional[Club]]:
    if len(arreglo) <= 2:
        return arreglo[:]
    fijo = arreglo[0]
    resto = arreglo[1:]
    if not resto:
        return arreglo[:]
    resto = [resto[-1], *resto[:-1]]
    return [fijo, *resto]


def crear_fixture_para_torneo(torneo: Torneo) -> List[FixturePartido]:
    """Genera el fixture ida y vuelta para el torneo indicado."""

    clubes = obtener_clubes_para_fixture(torneo)
    if len(clubes) < 2:
        raise FixtureGenerationError("Se requieren al menos 2 clubes para generar el fixture.")

    if FixturePartido.objects.filter(torneo=torneo).exists():
        raise FixtureAlreadyExists("El fixture ya fue generado previamente.")

    usar_bye = len(clubes) % 2 == 1
    arreglo: List[Optional[Club]] = clubes[:]
    if usar_bye:
        arreglo.append(None)

    fechas_por_ronda = len(arreglo) - 1
    ronda1_datos: List[dict[str, object]] = []

    ultima_localia: dict[int, str] = {}

    for fecha in range(1, fechas_por_ronda + 1):
        for equipo1, equipo2 in _emparejar(arreglo):
            if equipo1 is None or equipo2 is None:
                continue
            prefer_local, prefer_visitante = (
                (equipo1, equipo2)
                if fecha % 2 == 1
                else (equipo2, equipo1)
            )

            local, visitante = prefer_local, prefer_visitante
            local_prev = ultima_localia.get(prefer_local.pk)
            visitante_prev = ultima_localia.get(prefer_visitante.pk)
            if local_prev == "L" or visitante_prev == "V":
                alternativa_local = prefer_visitante
                alternativa_visitante = prefer_local
                alt_local_prev = ultima_localia.get(alternativa_local.pk)
                alt_visit_prev = ultima_localia.get(alternativa_visitante.pk)
                if alt_local_prev != "L" and alt_visit_prev != "V":
                    local, visitante = alternativa_local, alternativa_visitante

            ultima_localia[local.pk] = "L"
            ultima_localia[visitante.pk] = "V"
            ronda1_datos.append(
                {
                    "fecha_nro": fecha,
                    "local": local,
                    "visitante": visitante,
                }
            )
        arreglo = _rotar(arreglo)

    with transaction.atomic():
        ronda1_objs = [
            FixturePartido(
                torneo=torneo,
                ronda=FixturePartido.RONDA_IDA,
                fecha_nro=data["fecha_nro"],
                local=data["local"],
                visitante=data["visitante"],
            )
            for data in ronda1_datos
        ]
        FixturePartido.objects.bulk_create(ronda1_objs)

        ronda2_objs = [
            FixturePartido(
                torneo=torneo,
                ronda=FixturePartido.RONDA_VUELTA,
                fecha_nro=data["fecha_nro"],
                local=data["visitante"],
                visitante=data["local"],
            )
            for data in ronda1_datos
        ]
        FixturePartido.objects.bulk_create(ronda2_objs)

    return ronda1_objs + ronda2_objs
