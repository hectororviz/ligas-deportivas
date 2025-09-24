from unittest import mock

from django.contrib.auth.models import Permission, User
from django.db.utils import ProgrammingError
from django.test import TestCase
from django.urls import reverse

from .fixture import FixtureAlreadyExists, FixtureGenerationError, generate_fixture
from .forms import ResultadoPartidoFixtureForm
from .models import (
    Categoria,
    Club,
    Equipo,
    Liga,
    PartidoFixture,
    ResultadoCategoriaPartido,
    Torneo,
)


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


class FixtureGenerationServiceTests(TestCase):
    def setUp(self):
        self.liga = Liga.objects.create(nombre="Liga Test", temporada="2024")
        self.torneo_par = Torneo.objects.create(liga=self.liga, nombre="Apertura")
        self.torneo_impar = Torneo.objects.create(liga=self.liga, nombre="Clausura")

    def test_generate_fixture_even_clubs(self):
        clubes = [
            Club.objects.create(nombre="Club A"),
            Club.objects.create(nombre="Club B"),
            Club.objects.create(nombre="Club C"),
            Club.objects.create(nombre="Club D"),
        ]

        created = generate_fixture(self.torneo_par, clubes)
        self.assertEqual(len(created), len(clubes) * (len(clubes) - 1))

        partidos = PartidoFixture.objects.filter(torneo=self.torneo_par)
        self.assertEqual(partidos.count(), len(created))
        self.assertEqual(
            partidos.filter(ronda=PartidoFixture.RONDA_IDA).count(),
            (len(clubes) - 1) * (len(clubes) // 2),
        )
        self.assertEqual(
            partidos.filter(ronda=PartidoFixture.RONDA_VUELTA).count(),
            (len(clubes) - 1) * (len(clubes) // 2),
        )

        pairings = {}
        for partido in partidos:
            pair = tuple(sorted([partido.club_local_id, partido.club_visitante_id]))
            pairings.setdefault(pair, []).append(partido)

        for pair, matches in pairings.items():
            self.assertEqual(len(matches), 2)
            rondas = {match.ronda for match in matches}
            self.assertEqual(rondas, {PartidoFixture.RONDA_IDA, PartidoFixture.RONDA_VUELTA})
            locales = {match.club_local_id for match in matches}
            self.assertEqual(locales, set(pair))

        fechas_por_ronda = len(clubes) - 1
        for fecha in range(1, fechas_por_ronda + 1):
            ida = partidos.filter(ronda=PartidoFixture.RONDA_IDA, fecha_nro=fecha)
            vuelta = partidos.filter(ronda=PartidoFixture.RONDA_VUELTA, fecha_nro=fecha)
            self.assertEqual(ida.count(), vuelta.count())
            cruces_ida = {(m.club_local_id, m.club_visitante_id) for m in ida}
            for match in vuelta:
                self.assertIn((match.club_visitante_id, match.club_local_id), cruces_ida)

        totales_local = {club.id: 0 for club in clubes}
        totales_visita = {club.id: 0 for club in clubes}
        for partido in partidos:
            totales_local[partido.club_local_id] += 1
            totales_visita[partido.club_visitante_id] += 1
        for club in clubes:
            self.assertEqual(totales_local[club.id], totales_visita[club.id])

        with self.assertRaises(FixtureAlreadyExists):
            generate_fixture(self.torneo_par, clubes)

    def test_generate_fixture_odd_clubs(self):
        clubes = [
            Club.objects.create(nombre="Club 1"),
            Club.objects.create(nombre="Club 2"),
            Club.objects.create(nombre="Club 3"),
            Club.objects.create(nombre="Club 4"),
            Club.objects.create(nombre="Club 5"),
        ]

        generate_fixture(self.torneo_impar, clubes)

        partidos = PartidoFixture.objects.filter(torneo=self.torneo_impar)
        self.assertEqual(partidos.count(), len(clubes) * (len(clubes) - 1))

        ids = {club.id for club in clubes}
        libres = {club.id: 0 for club in clubes}
        fechas_por_ronda = len(clubes)
        for fecha in range(1, fechas_por_ronda + 1):
            fecha_partidos = partidos.filter(ronda=PartidoFixture.RONDA_IDA, fecha_nro=fecha)
            jugando = {p.club_local_id for p in fecha_partidos} | {p.club_visitante_id for p in fecha_partidos}
            libres_fecha = ids - jugando
            self.assertEqual(len(libres_fecha), 1)
            libres[libres_fecha.pop()] += 1
        for cuenta in libres.values():
            self.assertEqual(cuenta, 1)

        totales_local = {club.id: 0 for club in clubes}
        totales_visita = {club.id: 0 for club in clubes}
        for partido in partidos:
            totales_local[partido.club_local_id] += 1
            totales_visita[partido.club_visitante_id] += 1
        for club in clubes:
            self.assertEqual(totales_local[club.id], totales_visita[club.id])

        with self.assertRaises(FixtureAlreadyExists):
            generate_fixture(self.torneo_impar, clubes)

        with self.assertRaises(FixtureGenerationError):
            generate_fixture(Torneo.objects.create(liga=self.liga, nombre="Preliminar"), [clubes[0]])

    def test_generate_fixture_missing_table(self):
        clubes = [
            Club.objects.create(nombre="Club X"),
            Club.objects.create(nombre="Club Y"),
        ]

        with mock.patch.object(
            PartidoFixture.objects,
            "filter",
            side_effect=ProgrammingError("missing relation"),
        ):
            with self.assertRaises(FixtureGenerationError) as ctx:
                generate_fixture(self.torneo_par, clubes)

        self.assertIn("migraciones", str(ctx.exception))
        self.assertFalse(PartidoFixture.objects.filter(torneo=self.torneo_par).exists())


class TorneoFixtureViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="fixture-admin",
            password="testpass123",
            is_staff=True,
        )
        perms = Permission.objects.filter(
            codename__in=["view_torneo", "add_partidofixture", "change_partidofixture"]
        )
        self.user.user_permissions.add(*perms)
        self.client.login(username="fixture-admin", password="testpass123")

        self.liga = Liga.objects.create(nombre="Liga Vista", temporada="2025")
        self.torneo = Torneo.objects.create(liga=self.liga, nombre="Invierno")
        self.categoria = Categoria.objects.create(liga=self.liga, nombre="Sub 15")
        self.categoria_b = Categoria.objects.create(liga=self.liga, nombre="Sub 17")

        self.clubes = [
            Club.objects.create(nombre="Vista Club 1"),
            Club.objects.create(nombre="Vista Club 2"),
            Club.objects.create(nombre="Vista Club 3"),
            Club.objects.create(nombre="Vista Club 4"),
        ]
        for club in self.clubes:
            Equipo.objects.create(club=club, categoria=self.categoria, alias=f"{club.nombre} - Sub 15")

        self.url = reverse("ligas:torneo_fixture", args=[self.torneo.pk])

    def test_fixture_page_shows_clubs(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["club_count"], len(self.clubes))
        self.assertNotContains(response, "Clubes participantes")

    def test_post_generates_fixture(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, self.url)
        partidos = PartidoFixture.objects.filter(torneo=self.torneo)
        self.assertTrue(partidos.exists())

        count = partidos.count()
        response = self.client.post(self.url)
        self.assertRedirects(response, self.url)
        self.assertEqual(PartidoFixture.objects.filter(torneo=self.torneo).count(), count)

    def test_fixture_table_columns_and_order(self):
        generate_fixture(self.torneo, self.clubes)

        response = self.client.get(self.url)
        self.assertContains(response, "<th>Local</th>")
        self.assertContains(response, "<th>Visitante</th>")
        self.assertContains(response, "<th>Fecha</th>")
        self.assertContains(response, "<th>Estado</th>")
        self.assertContains(response, "<th>Acciones</th>")

        rounds_data = response.context["fixture_rounds_data"]
        rendered_partidos = []
        for ronda in rounds_data:
            for fecha in ronda["fechas"]:
                rendered_partidos.extend([row["partido"] for row in fecha["partidos"]])

        expected_partidos = list(
            PartidoFixture.objects.filter(torneo=self.torneo).order_by("ronda", "fecha_nro", "id")
        )
        self.assertEqual([p.id for p in rendered_partidos], [p.id for p in expected_partidos])

    def test_fixture_shows_bye_without_actions(self):
        club_extra = Club.objects.create(nombre="Vista Club 5")
        Equipo.objects.create(
            club=club_extra,
            categoria=self.categoria,
            alias=f"{club_extra.nombre} - Sub 15",
        )
        clubes = self.clubes + [club_extra]
        generate_fixture(self.torneo, clubes)

        response = self.client.get(self.url)
        self.assertContains(response, "Libre")
        html = response.content.decode()
        libre_index = html.find("Libre</td>")
        self.assertGreaterEqual(libre_index, 0)
        snippet = html[libre_index:libre_index + 150]
        self.assertIn("estado-pendiente", snippet)
        self.assertIn("<td>—</td>", snippet)
        self.assertNotIn("href", snippet)

    def test_fixture_page_handles_missing_table(self):
        with mock.patch.object(
            PartidoFixture.objects,
            "filter",
            side_effect=ProgrammingError("missing relation"),
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["fixture_table_missing"])
        self.assertContains(response, "No se detectó la tabla de partidos de fixture")

    def test_resultados_flow_updates_estado(self):
        generate_fixture(self.torneo, self.clubes)
        partido = (
            PartidoFixture.objects.filter(torneo=self.torneo)
            .order_by("ronda", "fecha_nro", "id")
            .first()
        )
        url = reverse("ligas:partido_fixture_resultados", args=[self.torneo.pk, partido.pk])

        data = {
            ResultadoPartidoFixtureForm._field_name(self.categoria, "local"): 2,
            ResultadoPartidoFixtureForm._field_name(self.categoria, "visitante"): 1,
            ResultadoPartidoFixtureForm._field_name(self.categoria_b, "local"): "",
            ResultadoPartidoFixtureForm._field_name(self.categoria_b, "visitante"): "",
        }

        response = self.client.post(url, data)
        self.assertRedirects(response, self.url)

        resultados = ResultadoCategoriaPartido.objects.filter(partido=partido)
        self.assertEqual(resultados.count(), 1)
        partido.refresh_from_db()
        self.assertFalse(partido.jugado)
        self.assertIsNone(partido.goles_local)
        self.assertIsNone(partido.goles_visitante)

        fixture_response = self.client.get(self.url)
        estados = fixture_response.context["estado_por_partido"]
        self.assertEqual(estados[partido.id]["estado"], "parcial")

        # Edición completa
        data.update(
            {
                ResultadoPartidoFixtureForm._field_name(self.categoria_b, "local"): 0,
                ResultadoPartidoFixtureForm._field_name(self.categoria_b, "visitante"): 3,
            }
        )
        response = self.client.post(url, data)
        self.assertRedirects(response, self.url)

        partido.refresh_from_db()
        self.assertTrue(partido.jugado)
        self.assertEqual(partido.goles_local, 2)
        self.assertEqual(partido.goles_visitante, 4)
        resultados = ResultadoCategoriaPartido.objects.filter(partido=partido)
        self.assertEqual(resultados.count(), 2)

        fixture_response = self.client.get(self.url)
        estados = fixture_response.context["estado_por_partido"]
        self.assertEqual(estados[partido.id]["estado"], "jugado")

        # GET precarga valores
        edit_response = self.client.get(url)
        form = edit_response.context["form"]
        self.assertEqual(
            form[ResultadoPartidoFixtureForm._field_name(self.categoria, "local")].value(),
            2,
        )
        self.assertEqual(
            form[ResultadoPartidoFixtureForm._field_name(self.categoria_b, "visitante")].value(),
            3,
        )

    def test_resultados_validation_requires_enteros(self):
        generate_fixture(self.torneo, self.clubes)
        partido = PartidoFixture.objects.filter(torneo=self.torneo).first()
        url = reverse("ligas:partido_fixture_resultados", args=[self.torneo.pk, partido.pk])
        data = {
            ResultadoPartidoFixtureForm._field_name(self.categoria, "local"): -1,
            ResultadoPartidoFixtureForm._field_name(self.categoria, "visitante"): "",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        field_name = ResultadoPartidoFixtureForm._field_name(self.categoria, "local")
        self.assertIn("Ingrese un entero ≥ 0", form[field_name].errors)

