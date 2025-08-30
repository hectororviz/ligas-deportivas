from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView

from .models import Club, Torneo, Ronda, Categoria, Equipo, Jugador, Arbitro, SiteIdentity
from django.views.generic.edit import UpdateView
from django.contrib import messages
from django.shortcuts import redirect
from django.db.utils import OperationalError, ProgrammingError


class AdminBaseView(LoginRequiredMixin):
    # Reutilizamos el login de /admin para no montar auth aparte
    login_url = "/admin/login/"
    raise_exception = False


class AdminHomeView(AdminBaseView, TemplateView):
    template_name = "ligas/administracion/index.html"


# ========
# CLUB
# ========
class ClubListView(AdminBaseView, PermissionRequiredMixin, ListView):
    permission_required = "ligas.view_club"
    model = Club
    template_name = "ligas/administracion/club_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q)
        return qs


class ClubCreateView(AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_club"
    model = Club
    fields = ["nombre", "escudo_url", "direccion"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:club_list")


class ClubUpdateView(AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_club"
    model = Club
    fields = ["nombre", "escudo_url", "direccion"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:club_list")


class ClubDeleteView(AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_club"
    model = Club
    template_name = "ligas/administracion/confirm_delete.html"
    success_url = reverse_lazy("ligas:club_list")


# ========
# TORNEO
# ========
class TorneoListView(AdminBaseView, PermissionRequiredMixin, ListView):
    permission_required = "ligas.view_torneo"
    model = Torneo
    template_name = "ligas/administracion/torneo_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("liga")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(liga__nombre__icontains=q) | Q(liga__temporada__icontains=q))
        return qs


class TorneoCreateView(AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_torneo"
    model = Torneo
    fields = ["liga", "nombre"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:torneo_list")


class TorneoUpdateView(AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_torneo"
    model = Torneo
    fields = ["liga", "nombre"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:torneo_list")


class TorneoDeleteView(AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_torneo"
    model = Torneo
    template_name = "ligas/administracion/confirm_delete.html"
    success_url = reverse_lazy("ligas:torneo_list")


# ========
# RONDA
# ========
class RondaListView(AdminBaseView, PermissionRequiredMixin, ListView):
    permission_required = "ligas.view_ronda"
    model = Ronda
    template_name = "ligas/administracion/ronda_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("torneo", "torneo__liga")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(torneo__nombre__icontains=q) | Q(torneo__liga__nombre__icontains=q))
        return qs


class RondaCreateView(AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_ronda"
    model = Ronda
    fields = ["torneo", "nombre"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:ronda_list")


class RondaUpdateView(AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_ronda"
    model = Ronda
    fields = ["torneo", "nombre"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:ronda_list")


class RondaDeleteView(AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_ronda"
    model = Ronda
    template_name = "ligas/administracion/confirm_delete.html"
    success_url = reverse_lazy("ligas:ronda_list")


# ===========
# CATEGORIA
# ===========
class CategoriaListView(AdminBaseView, PermissionRequiredMixin, ListView):
    permission_required = "ligas.view_categoria"
    model = Categoria
    template_name = "ligas/administracion/categoria_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("torneo", "torneo__liga")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(torneo__nombre__icontains=q) | Q(torneo__liga__nombre__icontains=q))
        return qs


class CategoriaCreateView(AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_categoria"
    model = Categoria
    fields = ["torneo", "nombre", "horario", "activa", "suma_puntos_general"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:categoria_list")


class CategoriaUpdateView(AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_categoria"
    model = Categoria
    fields = ["torneo", "nombre", "horario", "activa", "suma_puntos_general"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:categoria_list")


class CategoriaDeleteView(AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_categoria"
    model = Categoria
    template_name = "ligas/administracion/confirm_delete.html"
    success_url = reverse_lazy("ligas:categoria_list")


# ========
# EQUIPO
# ========
class EquipoListView(AdminBaseView, PermissionRequiredMixin, ListView):
    permission_required = "ligas.view_equipo"
    model = Equipo
    template_name = "ligas/administracion/equipo_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("club", "categoria", "categoria__torneo")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(club__nombre__icontains=q) | Q(categoria__nombre__icontains=q) | Q(alias__icontains=q))
        return qs


class EquipoCreateView(AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_equipo"
    model = Equipo
    fields = ["club", "categoria", "alias"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:equipo_list")


class EquipoUpdateView(AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_equipo"
    model = Equipo
    fields = ["club", "categoria", "alias"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:equipo_list")


class EquipoDeleteView(AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_equipo"
    model = Equipo
    template_name = "ligas/administracion/confirm_delete.html"
    success_url = reverse_lazy("ligas:equipo_list")


# =========
# JUGADOR
# =========
class JugadorListView(AdminBaseView, PermissionRequiredMixin, ListView):
    permission_required = "ligas.view_jugador"
    model = Jugador
    template_name = "ligas/administracion/jugador_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("equipo", "equipo__club", "equipo__categoria")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(apellido__icontains=q) | Q(nombre__icontains=q) | Q(dni__icontains=q) | Q(equipo__club__nombre__icontains=q))
        return qs


class JugadorCreateView(AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_jugador"
    model = Jugador
    fields = ["equipo", "apellido", "nombre", "dni", "fecha_nac"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:jugador_list")


class JugadorUpdateView(AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_jugador"
    model = Jugador
    fields = ["equipo", "apellido", "nombre", "dni", "fecha_nac"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:jugador_list")


class JugadorDeleteView(AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_jugador"
    model = Jugador
    template_name = "ligas/administracion/confirm_delete.html"
    success_url = reverse_lazy("ligas:jugador_list")


# =========
# ARBITRO
# =========
class ArbitroListView(AdminBaseView, PermissionRequiredMixin, ListView):
    permission_required = "ligas.view_arbitro"
    model = Arbitro
    template_name = "ligas/administracion/arbitro_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(apellido__icontains=q) | Q(nombre__icontains=q))
        return qs


class ArbitroCreateView(AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_arbitro"
    model = Arbitro
    fields = ["apellido", "nombre"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:arbitro_list")


class ArbitroUpdateView(AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_arbitro"
    model = Arbitro
    fields = ["apellido", "nombre"]
    template_name = "ligas/administracion/form.html"
    success_url = reverse_lazy("ligas:arbitro_list")


class ArbitroDeleteView(AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_arbitro"
    model = Arbitro
    template_name = "ligas/administracion/confirm_delete.html"
    success_url = reverse_lazy("ligas:arbitro_list")


# =================
# CONFIGURACIÓN
# =================

class IdentidadView(AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_siteidentity"
    model = SiteIdentity
    fields = [
        "site_title", "sidebar_bg", "accent_color", "logo_url",
        "facebook_url", "instagram_url", "tiktok_url", "whatsapp_url", "twitter_url",
    ]
    template_name = "ligas/configuracion/identidad.html"
    success_url = reverse_lazy("ligas:identidad")

    def get_object(self, queryset=None):
        return SiteIdentity.get_solo()

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except (OperationalError, ProgrammingError):
            messages.error(request, "Faltan migraciones para 'Identidad'. Ejecutá: python manage.py migrate")
            return redirect("ligas:admin_home")

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except (OperationalError, ProgrammingError):
            messages.error(request, "Faltan migraciones para 'Identidad'. Ejecutá: python manage.py migrate")
            return redirect("ligas:admin_home")
