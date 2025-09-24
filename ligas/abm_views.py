from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.utils import OperationalError, ProgrammingError

from .forms import EquipoGenerateForm
from .fixture import (
    FixtureAlreadyExists,
    FixtureGenerationError,
    generate_fixture,
)
from .models import Club, Liga, Torneo, Ronda, Categoria, Equipo, Jugador, Arbitro, PartidoFixture, SiteIdentity


class AdminBaseView(LoginRequiredMixin):
    # Reutilizamos el login de /admin para no montar auth aparte
    login_url = "/admin/login/"
    raise_exception = False


class AdminHomeView(AdminBaseView, TemplateView):
    template_name = "ligas/administracion/index.html"


class AjaxTemplateMixin:
    """Render a lightweight template when requested via AJAX for modal use."""
    ajax_template_name = None

    def get_template_names(self):
        template_names = super().get_template_names()
        is_ajax = self.request.headers.get("x-requested-with") == "XMLHttpRequest"
        if is_ajax and self.ajax_template_name:
            return [self.ajax_template_name]
        return template_names


class AjaxCreateMixin(AjaxTemplateMixin):
    """Enhances CreateView to support 'save and add another' in AJAX modals."""
    def form_valid(self, form):
        is_ajax = self.request.headers.get("x-requested-with") == "XMLHttpRequest"
        add_another = bool(self.request.POST.get("add_another"))
        # Save object first
        self.object = form.save()
        if is_ajax and add_another:
            # Return an empty form to keep adding
            form_class = self.get_form_class()
            new_form = form_class(initial=self.get_initial())
            context = self.get_context_data(form=new_form)
            response = self.render_to_response(context)
            try:
                response["X-Add-Another-Success"] = "1"
                response["X-List-Url"] = self.get_success_url()
            except Exception:
                pass
            return response
        # Default behavior (redirect) – JS will detect and reload
        return super(AjaxTemplateMixin, self).form_valid(form)



class PageSizeMixin:
    """Allow changing the amount of rows rendered per page via querystring."""

    page_size_query_param = "per_page"
    page_size_options = (10, 25, 50, 100)
    _current_page_size = None

    def get_paginate_by(self, queryset):
        default = super().get_paginate_by(queryset)
        per_page = self.request.GET.get(self.page_size_query_param)
        try:
            per_page_int = int(per_page)
        except (TypeError, ValueError):
            per_page_int = default
        else:
            if per_page_int not in self.page_size_options:
                per_page_int = default

        self._current_page_size = per_page_int
        return per_page_int

    def get_current_page_size(self):
        return self._current_page_size or self.paginate_by

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_size_options"] = self.page_size_options
        context["current_page_size"] = self.get_current_page_size()
        context["page_size_query_param"] = self.page_size_query_param

        querydict = self.request.GET.copy()
        if "page" in querydict:
            querydict = querydict.copy()
            querydict.pop("page")

        context["pagination_query"] = urlencode(querydict, doseq=True)
        return context

# ========
# CLUB
# ========
class ClubListView(PageSizeMixin, AdminBaseView, PermissionRequiredMixin, ListView):
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


class ClubCreateView(AjaxCreateMixin, AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_club"
    model = Club
    fields = ["nombre", "escudo_url", "direccion"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:club_list")


class ClubUpdateView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_club"
    model = Club
    fields = ["nombre", "escudo_url", "direccion"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:club_list")


class ClubDeleteView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_club"
    model = Club
    template_name = "ligas/administracion/confirm_delete.html"
    ajax_template_name = "ligas/administracion/_modal_confirm_delete.html"
    success_url = reverse_lazy("ligas:club_list")


# ========
# TORNEO
# ========
class TorneoListView(PageSizeMixin, AdminBaseView, PermissionRequiredMixin, ListView):
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


class TorneoCreateView(AjaxCreateMixin, AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_torneo"
    model = Torneo
    fields = ["liga", "nombre"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:torneo_list")


class TorneoUpdateView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_torneo"
    model = Torneo
    fields = ["liga", "nombre"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:torneo_list")


class TorneoDeleteView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_torneo"
    model = Torneo
    template_name = "ligas/administracion/confirm_delete.html"
    ajax_template_name = "ligas/administracion/_modal_confirm_delete.html"
    success_url = reverse_lazy("ligas:torneo_list")


class TorneoFixtureView(AdminBaseView, PermissionRequiredMixin, TemplateView):
    permission_required = "ligas.view_torneo"
    template_name = "ligas/administracion/torneo_fixture.html"

    def dispatch(self, request, *args, **kwargs):
        self.torneo = get_object_or_404(Torneo.objects.select_related("liga"), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("ligas:torneo_fixture", kwargs={"pk": self.torneo.pk})

    def get_participating_clubs(self):
        if not hasattr(self, "_clubes_cache"):
            clubes_qs = (
                Club.objects.filter(equipos__categoria__liga=self.torneo.liga)
                .distinct()
                .order_by("nombre")
            )
            self._clubes_cache = list(clubes_qs)
        return self._clubes_cache

    def _build_fixture_context(self, clubs, partidos):
        rondas = {
            PartidoFixture.RONDA_IDA: {},
            PartidoFixture.RONDA_VUELTA: {},
        }
        for partido in partidos:
            rondas.setdefault(partido.ronda, {}).setdefault(partido.fecha_nro, []).append(partido)

        for fechas in rondas.values():
            for lista in fechas.values():
                lista.sort(key=lambda match: (match.club_local.nombre, match.club_visitante.nombre))

        club_ids = {club.id for club in clubs}
        libres = {
            PartidoFixture.RONDA_IDA: {},
            PartidoFixture.RONDA_VUELTA: {},
        }
        for ronda, fechas in rondas.items():
            for fecha, lista in fechas.items():
                jugando = {match.club_local_id for match in lista} | {match.club_visitante_id for match in lista}
                libres_ids = list(club_ids - jugando)
                club_libre = None
                if libres_ids:
                    id_libre = libres_ids[0]
                    club_libre = next((club for club in clubs if club.id == id_libre), None)
                libres[ronda][fecha] = club_libre

        fechas_por_ronda = {
            ronda: sorted(fechas.keys())
            for ronda, fechas in rondas.items()
        }

        rounds_data = []
        ordered_rounds = [PartidoFixture.RONDA_IDA, PartidoFixture.RONDA_VUELTA]
        for ronda in ordered_rounds:
            fechas = rondas.get(ronda, {})
            fechas_ordenadas = sorted(fechas.keys())
            items = []
            for numero in fechas_ordenadas:
                items.append(
                    {
                        "numero": numero,
                        "partidos": fechas[numero],
                        "libre": libres[ronda].get(numero),
                    }
                )
            rounds_data.append(
                {
                    "id": ronda,
                    "fechas": items,
                }
            )

        return rondas, libres, fechas_por_ronda, rounds_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clubes = self.get_participating_clubs()

        fixture_table_missing = False
        try:
            partidos_qs = (
                PartidoFixture.objects.filter(torneo=self.torneo)
                .select_related("club_local", "club_visitante")
                .order_by("ronda", "fecha_nro", "club_local__nombre", "club_visitante__nombre")
            )
            partidos = list(partidos_qs)
        except (ProgrammingError, OperationalError):
            partidos = []
            fixture_table_missing = True

        fixture_exists = bool(partidos)
        rondas, libres, fechas_por_ronda, rounds_data = self._build_fixture_context(clubes, partidos)

        if fixture_exists:
            fechas_totales = max(match.fecha_nro for match in partidos)
        else:
            cantidad_clubes = len(clubes)
            if cantidad_clubes == 0:
                fechas_totales = 0
            elif cantidad_clubes % 2 == 0:
                fechas_totales = cantidad_clubes - 1
            else:
                fechas_totales = cantidad_clubes

        ronda_labels = {
            PartidoFixture.RONDA_IDA: "Ronda 1 (Ida)",
            PartidoFixture.RONDA_VUELTA: "Ronda 2 (Vuelta)",
        }
        rounds_view = [
            {
                "id": data["id"],
                "label": ronda_labels[data["id"]],
                "fechas": data["fechas"],
            }
            for data in rounds_data
        ]

        context.update(
            {
                "torneo": self.torneo,
                "clubes": clubes,
                "club_count": len(clubes),
                "fixture_exists": fixture_exists,
                "fixture_table_missing": fixture_table_missing,
                "fixture_rondas": rondas,
                "fixture_libres": libres,
                "fixture_fechas": fechas_por_ronda,
                "fecha_count": fechas_totales,
                "can_generate": self.request.user.has_perm("ligas.add_partidofixture")
                and not fixture_table_missing,
                "has_bye": len(clubes) % 2 == 1,
                "ronda_labels": ronda_labels,
                "fixture_rounds_data": rounds_view,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm("ligas.add_partidofixture"):
            raise PermissionDenied

        clubes = self.get_participating_clubs()
        if len(clubes) < 2:
            messages.error(request, "Se necesitan al menos dos clubes para crear un fixture.")
            return redirect(self.get_success_url())

        try:
            created = generate_fixture(self.torneo, clubes)
        except FixtureAlreadyExists:
            messages.info(request, "El torneo ya tiene un fixture generado.")
        except FixtureGenerationError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Se generó el fixture con {len(created)} partidos.")
        return redirect(self.get_success_url())


# ========
# RONDA
# ========
class RondaListView(PageSizeMixin, AdminBaseView, PermissionRequiredMixin, ListView):
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


class RondaCreateView(AjaxCreateMixin, AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_ronda"
    model = Ronda
    fields = ["torneo", "nombre"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:ronda_list")


class RondaUpdateView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_ronda"
    model = Ronda
    fields = ["torneo", "nombre"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:ronda_list")


class RondaDeleteView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_ronda"
    model = Ronda
    template_name = "ligas/administracion/confirm_delete.html"
    ajax_template_name = "ligas/administracion/_modal_confirm_delete.html"
    success_url = reverse_lazy("ligas:ronda_list")


# ===========
# CATEGORIA
# ===========
class CategoriaListView(PageSizeMixin, AdminBaseView, PermissionRequiredMixin, ListView):
    permission_required = "ligas.view_categoria"
    model = Categoria
    template_name = "ligas/administracion/categoria_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("liga")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(liga__nombre__icontains=q) | Q(liga__temporada__icontains=q))
        return qs


class CategoriaCreateView(AjaxCreateMixin, AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_categoria"
    model = Categoria
    fields = ["liga", "nombre", "horario", "activa", "suma_puntos_general"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:categoria_list")


class CategoriaUpdateView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_categoria"
    model = Categoria
    fields = ["liga", "nombre", "horario", "activa", "suma_puntos_general"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:categoria_list")


class CategoriaDeleteView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_categoria"
    model = Categoria
    template_name = "ligas/administracion/confirm_delete.html"
    ajax_template_name = "ligas/administracion/_modal_confirm_delete.html"
    success_url = reverse_lazy("ligas:categoria_list")


# ========
# EQUIPO
# ========
class EquipoListView(PageSizeMixin, AdminBaseView, PermissionRequiredMixin, ListView):
    permission_required = "ligas.view_equipo"
    model = Equipo
    template_name = "ligas/administracion/equipo_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("club", "categoria", "categoria__liga")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(club__nombre__icontains=q) | Q(categoria__nombre__icontains=q) | Q(alias__icontains=q))
        return qs


class EquipoCreateView(AjaxCreateMixin, AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_equipo"
    model = Equipo
    fields = ["club", "categoria", "alias"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:equipo_list")


class EquipoGenerateView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, FormView):
    permission_required = "ligas.add_equipo"
    form_class = EquipoGenerateForm
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/equipo_generate_modal.html"
    success_url = reverse_lazy("ligas:equipo_list")

    def form_valid(self, form):
        club = form.cleaned_data["club"]
        liga = form.cleaned_data["liga"]
        categorias = list(liga.categorias.all())

        if not categorias:
            messages.warning(self.request, f"La liga {liga} no tiene categorías asociadas.")
            return super().form_valid(form)

        created = 0
        for categoria in categorias:
            alias = f"{club.nombre} - {categoria.nombre}"
            equipo, created_flag = Equipo.objects.get_or_create(
                club=club,
                categoria=categoria,
                defaults={"alias": alias},
            )
            if created_flag:
                created += 1
            elif not equipo.alias:
                equipo.alias = alias
                equipo.save(update_fields=["alias"])

        skipped = len(categorias) - created

        if created:
            message = f"Se generaron {created} equipo{'s' if created != 1 else ''} para {club} en {liga}."
            if skipped:
                message += f" {skipped} ya existían."
            messages.success(self.request, message)
        else:
            messages.info(
                self.request,
                f"No se crearon equipos nuevos: ya existían para todas las categorías de {liga}.",
            )

        return super().form_valid(form)


class EquipoDetailView(AdminBaseView, PermissionRequiredMixin, DetailView):
    permission_required = "ligas.view_equipo"
    model = Equipo
    template_name = "ligas/administracion/equipo_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Prefetch jugadores for display
        ctx["jugadores"] = self.object.jugadores.all().order_by("apellido", "nombre")
        return ctx

class EquipoUpdateView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_equipo"
    model = Equipo
    fields = ["club", "categoria", "alias"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:equipo_list")


class EquipoDeleteView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_equipo"
    model = Equipo
    template_name = "ligas/administracion/confirm_delete.html"
    ajax_template_name = "ligas/administracion/_modal_confirm_delete.html"
    success_url = reverse_lazy("ligas:equipo_list")


# =========
# JUGADOR
# =========
class JugadorListView(PageSizeMixin, AdminBaseView, PermissionRequiredMixin, ListView):
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


class JugadorCreateView(AjaxCreateMixin, AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_jugador"
    model = Jugador
    fields = ["equipo", "apellido", "nombre", "dni", "fecha_nac"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:jugador_list")

    def get_initial(self):
        initial = super().get_initial()
        equipo_id = self.request.GET.get("equipo")
        if equipo_id:
            try:
                initial["equipo"] = Equipo.objects.get(pk=equipo_id)
            except Equipo.DoesNotExist:
                pass
        return initial


class JugadorUpdateView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_jugador"
    model = Jugador
    fields = ["equipo", "apellido", "nombre", "dni", "fecha_nac"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:jugador_list")


class JugadorDeleteView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_jugador"
    model = Jugador
    template_name = "ligas/administracion/confirm_delete.html"
    ajax_template_name = "ligas/administracion/_modal_confirm_delete.html"
    success_url = reverse_lazy("ligas:jugador_list")


# =========
# ARBITRO
# =========
class ArbitroListView(PageSizeMixin, AdminBaseView, PermissionRequiredMixin, ListView):
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


class ArbitroCreateView(AjaxCreateMixin, AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_arbitro"
    model = Arbitro
    fields = ["apellido", "nombre"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:arbitro_list")


class ArbitroUpdateView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_arbitro"
    model = Arbitro
    fields = ["apellido", "nombre"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:arbitro_list")


class ArbitroDeleteView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_arbitro"
    model = Arbitro
    template_name = "ligas/administracion/confirm_delete.html"
    ajax_template_name = "ligas/administracion/_modal_confirm_delete.html"
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
# ========
# LIGA
# ========
class LigaListView(PageSizeMixin, AdminBaseView, PermissionRequiredMixin, ListView):
    permission_required = "ligas.view_liga"
    model = Liga
    template_name = "ligas/administracion/liga_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(temporada__icontains=q))
        return qs


class LigaCreateView(AjaxCreateMixin, AdminBaseView, PermissionRequiredMixin, CreateView):
    permission_required = "ligas.add_liga"
    model = Liga
    fields = ["nombre", "temporada"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:liga_list")


class LigaUpdateView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, UpdateView):
    permission_required = "ligas.change_liga"
    model = Liga
    fields = ["nombre", "temporada"]
    template_name = "ligas/administracion/form.html"
    ajax_template_name = "ligas/administracion/_modal_form.html"
    success_url = reverse_lazy("ligas:liga_list")


class LigaDeleteView(AjaxTemplateMixin, AdminBaseView, PermissionRequiredMixin, DeleteView):
    permission_required = "ligas.delete_liga"
    model = Liga
    template_name = "ligas/administracion/confirm_delete.html"
    ajax_template_name = "ligas/administracion/_modal_confirm_delete.html"
    success_url = reverse_lazy("ligas:liga_list")
