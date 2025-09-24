"""Utilities for generating tournament fixtures using the circle method."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from django.db import transaction

from .models import Club, PartidoFixture, Torneo


class FixtureAlreadyExists(Exception):
    """Raised when attempting to generate a fixture that already exists."""


class FixtureGenerationError(Exception):
    """Raised when the fixture cannot be generated due to invalid conditions."""


@dataclass(frozen=True)
class FixtureMatch:
    """Represents a match scheduled for a specific round and date."""

    ronda: int
    fecha: int
    local: Club
    visitante: Club


def _normalize_clubs(clubs: Sequence[Club]) -> List[Club]:
    """Return a list of unique clubs preserving the original order."""

    seen: set[int] = set()
    unique: List[Club] = []
    for club in clubs:
        if club is None:
            continue
        if club.pk is None:
            raise FixtureGenerationError("Todos los clubes deben estar guardados antes de generar el fixture.")
        if club.pk in seen:
            continue
        seen.add(club.pk)
        unique.append(club)
    return unique


def _build_rounds(clubs: Sequence[Club]) -> Tuple[List[List[Tuple[Club, Club]]], List[List[Tuple[Club, Club]]], List[Optional[Club]]]:
    """Apply the circle method to obtain matches for both rounds.

    Returns a tuple ``(round1, round2, byes_round1)`` where each round is a list
    of fechas and each fecha is a list of (local, visitante) tuples. ``byes``
    keeps track of which club rests on each fecha of round 1 (``None`` when all
    play).
    """

    clubs_list: List[Optional[Club]] = list(clubs)
    has_bye = len(clubs_list) % 2 == 1
    if has_bye:
        clubs_list.append(None)  # marker for BYE

    total_slots = len(clubs_list)
    if total_slots < 2:
        raise FixtureGenerationError("Se necesitan al menos dos clubes para generar un fixture.")

    fechas_por_ronda = total_slots - 1
    mitad = total_slots // 2
    arrangement = clubs_list[:]

    ronda_ida: List[List[Tuple[Club, Club]]] = []
    libres_ida: List[Optional[Club]] = []

    for fecha_idx in range(fechas_por_ronda):
        cruces: List[Tuple[Club, Club]] = []
        libre: Optional[Club] = None
        for offset in range(mitad):
            primero = arrangement[offset]
            ultimo = arrangement[-(offset + 1)]
            if primero is None or ultimo is None:
                libre = primero or ultimo
                continue
            if fecha_idx % 2 == 0:  # fechas impares (1-indexed)
                local, visitante = primero, ultimo
            else:
                local, visitante = ultimo, primero
            cruces.append((local, visitante))
        ronda_ida.append(cruces)
        libres_ida.append(libre)
        # Rotación circular manteniendo fijo el primer club
        arrangement = [arrangement[0]] + [arrangement[-1]] + arrangement[1:-1]

    ronda_vuelta: List[List[Tuple[Club, Club]]] = [
        [(visitante, local) for (local, visitante) in fecha]
        for fecha in ronda_ida
    ]

    return ronda_ida, ronda_vuelta, libres_ida


def generate_fixture(torneo: Torneo, clubs: Sequence[Club]) -> List[FixtureMatch]:
    """Generate and persist the fixture for ``torneo`` using the circle method.

    The function is idempotent: if the tournament already has fixture matches it
    raises :class:`FixtureAlreadyExists`. When successful it returns a list of
    :class:`FixtureMatch` instances with the created matches.
    """

    clubes = _normalize_clubs(clubs)
    if len(clubes) < 2:
        raise FixtureGenerationError("Se necesitan al menos dos clubes para generar un fixture.")

    ronda_ida, ronda_vuelta, _ = _build_rounds(clubes)
    created_matches: List[FixtureMatch] = []

    with transaction.atomic():
        if PartidoFixture.objects.filter(torneo=torneo).exists():
            raise FixtureAlreadyExists("El torneo ya tiene un fixture generado.")

        for fecha_idx, fecha in enumerate(ronda_ida, start=1):
            for local, visitante in fecha:
                match = PartidoFixture.objects.create(
                    torneo=torneo,
                    ronda=PartidoFixture.RONDA_IDA,
                    fecha_nro=fecha_idx,
                    club_local=local,
                    club_visitante=visitante,
                )
                created_matches.append(
                    FixtureMatch(
                        ronda=match.ronda,
                        fecha=match.fecha_nro,
                        local=local,
                        visitante=visitante,
                    )
                )

        for fecha_idx, fecha in enumerate(ronda_vuelta, start=1):
            for local, visitante in fecha:
                match = PartidoFixture.objects.create(
                    torneo=torneo,
                    ronda=PartidoFixture.RONDA_VUELTA,
                    fecha_nro=fecha_idx,
                    club_local=local,
                    club_visitante=visitante,
                )
                created_matches.append(
                    FixtureMatch(
                        ronda=match.ronda,
                        fecha=match.fecha_nro,
                        local=local,
                        visitante=visitante,
                    )
                )

    return created_matches


__all__ = [
    "FixtureAlreadyExists",
    "FixtureGenerationError",
    "FixtureMatch",
    "generate_fixture",
]
