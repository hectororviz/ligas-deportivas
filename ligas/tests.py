from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Club, Equipo, Liga


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
