from itertools import combinations

from django.contrib.auth.models import Permission, User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .fixture import FixtureAlreadyExists, FixtureGenerationError, crear_fixture_para_torneo
from .models import Categoria, Club, Equipo, Liga, Torneo, FixturePartido


class EquipoGenerateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            password="testpass123",
            is_staff=True,
        )
        permission = Permission.objects.get(codename="add_equipo")
        self.user.user_permissions.add(permission)
        self.client.login(username="tester", password="testpass123")

        self.club = Club.objects.create(nombre="Club Generador")
        self.liga = Liga.objects.create(nombre="Liga Test", temporada="2024")
        self.categoria_a = Categoria.objects.create(liga=self.liga, nombre="Sub 10")
        self.categoria_b = Categoria.objects.create(liga=self.liga, nombre="Sub 12")

    def test_generate_creates_equipo_for_all_categories(self):
        response = self.client.post(
            reverse("ligas:equipo_generate"),
            {"club": self.club.id, "liga": self.liga.id},
        )

        self.assertRedirects(
            response,
            reverse("ligas:equipo_list"),
            fetch_redirect_response=False,
        )

        equipos = Equipo.objects.filter(club=self.club, categoria__liga=self.liga)
        self.assertEqual(equipos.count(), 2)
        self.assertEqual(
            equipos.get(categoria=self.categoria_a).alias,
            f"{self.club.nombre} - {self.categoria_a.nombre}",
        )

    def test_generate_skips_existing_equipo(self):
        Equipo.objects.create(club=self.club, categoria=self.categoria_a, alias="Personalizado")

        response = self.client.post(
            reverse("ligas:equipo_generate"),
            {"club": self.club.id, "liga": self.liga.id},
        )

        self.assertRedirects(
            response,
            reverse("ligas:equipo_list"),
            fetch_redirect_response=False,
        )

        equipos = Equipo.objects.filter(club=self.club, categoria__liga=self.liga)
        self.assertEqual(equipos.count(), 2)
        self.assertEqual(
            equipos.get(categoria=self.categoria_a).alias,
            "Personalizado",
        )
        self.assertEqual(
            equipos.get(categoria=self.categoria_b).alias,
            f"{self.club.nombre} - {self.categoria_b.nombre}",
        )


class FixtureGenerationTests(TestCase):
    def setUp(self):
        self.liga = Liga.objects.create(nombre="Liga Fixture", temporada="2024")
        self.torneo = Torneo.objects.create(liga=self.liga, nombre="Apertura")
        self.categoria = Categoria.objects.create(liga=self.liga, nombre="Primera")

    def crear_club(self, nombre: str) -> Club:
        club = Club.objects.create(nombre=nombre)
        Equipo.objects.create(club=club, categoria=self.categoria)
        return club

    def test_even_number_of_teams_generates_double_round_robin(self):
        clubes = [self.crear_club(f"Club {i}") for i in range(4)]

        crear_fixture_para_torneo(self.torneo)

        partidos = FixturePartido.objects.filter(torneo=self.torneo)
        self.assertEqual(partidos.count(), 12)

        ronda1 = partidos.filter(ronda=FixturePartido.RONDA_IDA)
        ronda2 = partidos.filter(ronda=FixturePartido.RONDA_VUELTA)
        self.assertEqual(ronda1.count(), 6)
        self.assertEqual(ronda2.count(), 6)
        self.assertEqual(set(ronda1.values_list("fecha_nro", flat=True)), {1, 2, 3})

        for club_a, club_b in combinations(clubes, 2):
            partido_ida = ronda1.filter(local=club_a, visitante=club_b).first()
            if partido_ida is None:
                partido_ida = ronda1.get(local=club_b, visitante=club_a)
            self.assertIsNotNone(partido_ida)
            partido_vuelta = ronda2.filter(
                local=partido_ida.visitante, visitante=partido_ida.local
            ).first()
            self.assertIsNotNone(partido_vuelta)

        for club in clubes:
            secuencia = [
                "L" if p.local_id == club.id else "V"
                for p in ronda1.order_by("fecha_nro")
                if club.id in {p.local_id, p.visitante_id}
            ]
            self.assertEqual(len(secuencia), 3)
            if len(secuencia) >= 2:
                self.assertNotEqual(
                    secuencia[0],
                    secuencia[1],
                    "La localía debe alternarse al menos en los primeros encuentros",
                )

    def test_odd_number_of_teams_includes_bye_each_round(self):
        clubes = [self.crear_club(f"Club {i}") for i in range(5)]

        crear_fixture_para_torneo(self.torneo)

        ronda1 = FixturePartido.objects.filter(
            torneo=self.torneo, ronda=FixturePartido.RONDA_IDA
        )
        self.assertEqual(ronda1.count(), 10)
        self.assertEqual(
            set(ronda1.values_list("fecha_nro", flat=True)), {1, 2, 3, 4, 5}
        )

        fechas = {1, 2, 3, 4, 5}
        for club in clubes:
            jugadas = set(
                ronda1.filter(local=club).values_list("fecha_nro", flat=True)
            ) | set(ronda1.filter(visitante=club).values_list("fecha_nro", flat=True))
            self.assertEqual(len(jugadas), 4)
            self.assertEqual(len(fechas - jugadas), 1)

    def test_idempotent_generation(self):
        [self.crear_club(f"Club {i}") for i in range(4)]
        crear_fixture_para_torneo(self.torneo)

        with self.assertRaises(FixtureAlreadyExists):
            crear_fixture_para_torneo(self.torneo)

    def test_requires_at_least_two_teams(self):
        self.crear_club("Solo Club")

        with self.assertRaises(FixtureGenerationError):
            crear_fixture_para_torneo(self.torneo)

    def test_constraints_enforced(self):
        clubes = [self.crear_club(f"Club {i}") for i in range(4)]
        crear_fixture_para_torneo(self.torneo)

        partido = FixturePartido.objects.filter(torneo=self.torneo).first()
        self.assertIsNotNone(partido)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FixturePartido.objects.create(
                    torneo=self.torneo,
                    ronda=partido.ronda,
                    fecha_nro=partido.fecha_nro,
                    local=partido.local,
                    visitante=partido.visitante,
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FixturePartido.objects.create(
                    torneo=self.torneo,
                    ronda=FixturePartido.RONDA_IDA,
                    fecha_nro=1,
                    local=clubes[0],
                    visitante=clubes[0],
                )


class FixtureCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="fixture", password="secret123", is_staff=True
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename="add_fixturepartido")
        )
        self.client.login(username="fixture", password="secret123")

        self.liga = Liga.objects.create(nombre="Liga View", temporada="2024")
        self.torneo = Torneo.objects.create(liga=self.liga, nombre="Clausura")
        self.categoria = Categoria.objects.create(liga=self.liga, nombre="Reserva")
        for i in range(4):
            club = Club.objects.create(nombre=f"Club V{i}")
            Equipo.objects.create(club=club, categoria=self.categoria)

    def test_post_creates_fixture(self):
        response = self.client.post(
            reverse("ligas:torneo_fixture_create", args=[self.torneo.pk])
        )

        self.assertRedirects(
            response,
            reverse("ligas:torneo_fixture", args=[self.torneo.pk]),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            FixturePartido.objects.filter(torneo=self.torneo).exists()
        )

    def test_post_without_permission_denied(self):
        self.client.logout()
        other = User.objects.create_user(username="sinperm", password="abc123")
        self.client.login(username="sinperm", password="abc123")

        response = self.client.post(
            reverse("ligas:torneo_fixture_create", args=[self.torneo.pk])
        )
        self.assertEqual(response.status_code, 403)
