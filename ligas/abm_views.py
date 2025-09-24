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
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError

from .forms import EquipoGenerateForm, ResultadoPartidoFixtureForm
from .fixture import (
    FixtureAlreadyExists,
    FixtureGenerationError,
    generate_fixture,
)
from .models import (
    Club,
    Liga,
    Torneo,
    Ronda,
    Categoria,
    Equipo,
    Jugador,
    Arbitro,
    PartidoFixture,
    ResultadoCategoriaPartido,
    SiteIdentity,
)


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

    def can_manage_fixture(self):
        user = self.request.user
        return user.is_authenticated and user.has_perm("ligas.change_partidofixture")

    def get_torneo_categorias(self):
        if not hasattr(self, "_categorias_cache"):
            self._categorias_cache = list(
                Categoria.objects.filter(liga=self.torneo.liga).order_by("nombre")
            )
        return self._categorias_cache

    def _build_fixture_rows(self, clubs, partidos, categorias):
        rondas = {
            PartidoFixture.RONDA_IDA: {},
            PartidoFixture.RONDA_VUELTA: {},
        }
        for partido in partidos:
            rondas.setdefault(partido.ronda, {}).setdefault(partido.fecha_nro, []).append(partido)

        club_ids = [club.id for club in clubs]
        clubes_por_id = {club.id: club for club in clubs}

        try:
            resultados = list(
                ResultadoCategoriaPartido.objects.filter(partido__in=partidos, categoria__in=categorias)
            )
        except (ProgrammingError, OperationalError):
            resultados = []

        resultados_por_partido: dict[int, dict[int, ResultadoCategoriaPartido]] = {}
        for resultado in resultados:
            resultados_por_partido.setdefault(resultado.partido_id, {})[resultado.categoria_id] = resultado

        total_categorias = len(categorias)
        estado_por_partido: dict[int, dict[str, int | str]] = {}
        for partido in partidos:
            resultados_map = resultados_por_partido.get(partido.id, {})
            completados = sum(1 for categoria in categorias if categoria.id in resultados_map)
            if completados == 0:
                estado = "pendiente"
            elif completados == total_categorias and total_categorias > 0:
                estado = "jugado"
            else:
                estado = "parcial"
            estado_por_partido[partido.id] = {
                "estado": estado,
                "completados": completados,
                "total": total_categorias,
            }

        bye_por_fecha = {
            PartidoFixture.RONDA_IDA: {},
            PartidoFixture.RONDA_VUELTA: {},
        }
        for ronda, fechas in rondas.items():
            for fecha, lista in fechas.items():
                jugando = {match.club_local_id for match in lista} | {match.club_visitante_id for match in lista}
                libres_ids = [club_id for club_id in club_ids if club_id not in jugando]
                club_libre = clubes_por_id.get(libres_ids[0]) if libres_ids else None
                bye_por_fecha[ronda][fecha] = club_libre

        ronda_labels = {
            PartidoFixture.RONDA_IDA: "Ronda 1 (Ida)",
            PartidoFixture.RONDA_VUELTA: "Ronda 2 (Vuelta)",
        }
        ordered_rounds = [PartidoFixture.RONDA_IDA, PartidoFixture.RONDA_VUELTA]
        rounds_data = []
        for ronda in ordered_rounds:
            fechas = rondas.get(ronda, {})
            fechas_ordenadas = sorted(fechas.keys())
            items = []
            for numero in fechas_ordenadas:
                partidos_fecha = fechas[numero]
                partida_rows = [
                    {
                        "partido": partido,
                        "estado": estado_por_partido[partido.id]["estado"],
                        "tiene_resultados": estado_por_partido[partido.id]["completados"] > 0,
                    }
                    for partido in partidos_fecha
                ]
                items.append(
                    {
                        "numero": numero,
                        "partidos": partida_rows,
                        "libre": bye_por_fecha[ronda].get(numero),
                    }
                )
            rounds_data.append(
                {
                    "id": ronda,
                    "label": ronda_labels[ronda],
                    "fechas": items,
                }
            )

        return rounds_data, estado_por_partido

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clubes = self.get_participating_clubs()

        fixture_table_missing = False
        try:
            partidos_qs = (
                PartidoFixture.objects.filter(torneo=self.torneo)
                .select_related("club_local", "club_visitante")
                .order_by("ronda", "fecha_nro", "id")
            )
            partidos = list(partidos_qs)
        except (ProgrammingError, OperationalError):
            partidos = []
            fixture_table_missing = True


        fixture_exists = bool(partidos)
        categorias = self.get_torneo_categorias()
        rounds_data, estado_por_partido = self._build_fixture_rows(clubes, partidos, categorias)

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

        context.update(
            {
                "torneo": self.torneo,
                "fixture_exists": fixture_exists,

                "fixture_table_missing": fixture_table_missing,
                "fecha_count": fechas_totales,
                "categorias": categorias,
                "estado_por_partido": estado_por_partido,
                "can_generate": self.request.user.has_perm("ligas.add_partidofixture")
                and not fixture_table_missing,
                "can_manage_resultados": self.can_manage_fixture(),
                "has_bye": len(clubes) % 2 == 1,
                "club_count": len(clubes),
                "fixture_rounds_data": rounds_data,
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


class PartidoFixtureResultadoView(AdminBaseView, PermissionRequiredMixin, FormView):
    permission_required = "ligas.change_partidofixture"
    form_class = ResultadoPartidoFixtureForm
    template_name = "ligas/administracion/torneo_fixture_resultados.html"

    def dispatch(self, request, *args, **kwargs):
        self.torneo = get_object_or_404(Torneo.objects.select_related("liga"), pk=kwargs["pk"])
        self.partido = get_object_or_404(
            PartidoFixture.objects.select_related("torneo", "club_local", "club_visitante"),
            pk=kwargs["partido_id"],
            torneo=self.torneo,
        )
        self.categorias = list(
            Categoria.objects.filter(liga=self.torneo.liga).order_by("nombre")
        )
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user.is_authenticated and self.request.user.has_perm(
            "ligas.change_partidofixture"
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["categorias"] = self.categorias
        initial = {}
        resultados = ResultadoCategoriaPartido.objects.filter(partido=self.partido)
        for resultado in resultados:
            initial[ResultadoPartidoFixtureForm._field_name(resultado.categoria, "local")] = (
                resultado.goles_local
            )
            initial[ResultadoPartidoFixtureForm._field_name(resultado.categoria, "visitante")] = (
                resultado.goles_visitante
            )
        if self.request.method == "GET":
            kwargs["initial"] = initial
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            existentes = {
                resultado.categoria_id: resultado
                for resultado in ResultadoCategoriaPartido.objects.filter(partido=self.partido)
            }
            for categoria, goles_local, goles_visitante in form.iter_resultados():
                existente = existentes.get(categoria.id)
                if goles_local is None or goles_visitante is None:
                    if existente:
                        existente.delete()
                    continue

                if existente:
                    if (
                        existente.goles_local != goles_local
                        or existente.goles_visitante != goles_visitante
                    ):
                        existente.goles_local = goles_local
                        existente.goles_visitante = goles_visitante
                        existente.save(update_fields=["goles_local", "goles_visitante"])
                else:
                    ResultadoCategoriaPartido.objects.create(
                        partido=self.partido,
                        categoria=categoria,
                        goles_local=goles_local,
                        goles_visitante=goles_visitante,
                    )

            resultados_actuales = list(
                ResultadoCategoriaPartido.objects.filter(partido=self.partido)
            )
            total_categorias = len(self.categorias)
            completados = len(resultados_actuales)

            if completados == 0 or total_categorias == 0:
                self.partido.jugado = False
                self.partido.goles_local = None
                self.partido.goles_visitante = None
            elif completados == total_categorias:
                self.partido.jugado = True
                self.partido.goles_local = sum(r.goles_local for r in resultados_actuales)
                self.partido.goles_visitante = sum(r.goles_visitante for r in resultados_actuales)
            else:
                self.partido.jugado = False
                self.partido.goles_local = None
                self.partido.goles_visitante = None

            self.partido.save(update_fields=["jugado", "goles_local", "goles_visitante"])

        messages.success(self.request, "Resultados guardados")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ligas:torneo_fixture", kwargs={"pk": self.torneo.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get("form")
        context.update(
            {
                "torneo": self.torneo,
                "partido": self.partido,
                "categorias": self.categorias,
                "tiene_resultados": ResultadoCategoriaPartido.objects.filter(
                    partido=self.partido
                ).exists(),
                "categoria_rows": [
                    {
                        "categoria": categoria,
                        "local_field": form[ResultadoPartidoFixtureForm._field_name(categoria, "local")] if form else None,
                        "visitante_field": form[ResultadoPartidoFixtureForm._field_name(categoria, "visitante")] if form else None,
                    }
                    for categoria in self.categorias
                ],
            }
        )
        return context


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
