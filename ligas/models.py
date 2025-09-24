from django.db import models
from django.db.models import F, Q
from django.core.validators import RegexValidator


# ==========
# ENTIDADES
# ==========

class Club(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    escudo_url = models.URLField(blank=True)
    direccion = models.TextField(blank=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Club"
        verbose_name_plural = "Clubes"

    def __str__(self) -> str:
        return self.nombre


class Liga(models.Model):
    nombre = models.CharField(max_length=120)
    temporada = models.CharField(max_length=20)  # ej: "2025"

    class Meta:
        unique_together = ("nombre", "temporada")
        ordering = ["-temporada", "nombre"]
        verbose_name = "Liga"
        verbose_name_plural = "Ligas"

    def __str__(self) -> str:
        return f"{self.nombre} {self.temporada}"


class Torneo(models.Model):
    liga = models.ForeignKey(Liga, on_delete=models.CASCADE, related_name="torneos")
    nombre = models.CharField(max_length=120)  # ej: "Apertura", "Clausura"

    class Meta:
        unique_together = ("liga", "nombre")
        ordering = ["liga__temporada", "nombre"]
        verbose_name = "Torneo"
        verbose_name_plural = "Torneos"

    def __str__(self) -> str:
        return f"{self.liga} - {self.nombre}"


class Ronda(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="rondas")
    nombre = models.CharField(max_length=60, default="Fase Única")  # o "Primera Ronda"

    class Meta:
        unique_together = ("torneo", "nombre")
        ordering = ["torneo__liga__temporada", "torneo__nombre", "nombre"]
        verbose_name = "Ronda"
        verbose_name_plural = "Rondas"

    def __str__(self) -> str:
        return f"{self.torneo} - {self.nombre}"


# =====================
# CATEGORÍAS / EQUIPOS
# =====================

class Categoria(models.Model):
    # Categoría por liga (p.ej. "2015 A", "Sub 11") con flags útiles
    liga = models.ForeignKey(Liga, on_delete=models.CASCADE, related_name="categorias")
    nombre = models.CharField(max_length=30)
    horario = models.TimeField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    suma_puntos_general = models.BooleanField(default=True)

    class Meta:
        unique_together = ("liga", "nombre")
        ordering = ["liga__temporada", "liga__nombre", "nombre"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self) -> str:
        return f"{self.nombre} - {self.liga}"


class Equipo(models.Model):
    # Equipo = Club compitiendo en una Categoría específica del Torneo
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="equipos")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="equipos")
    alias = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = ("club", "categoria")
        ordering = ["categoria__liga__temporada", "categoria__nombre", "club__nombre"]
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self) -> str:
        return f"{self.club} - {self.categoria.nombre}"


class Jugador(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="jugadores")
    apellido = models.CharField(max_length=120)
    nombre = models.CharField(max_length=120)
    dni = models.CharField(max_length=20, blank=True)
    fecha_nac = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["apellido", "nombre"]
        verbose_name = "Jugador"
        verbose_name_plural = "Jugadores"

    def __str__(self) -> str:
        return f"{self.apellido}, {self.nombre} - {self.equipo}"


class Arbitro(models.Model):
    apellido = models.CharField(max_length=120)
    nombre = models.CharField(max_length=120)

    class Meta:
        ordering = ["apellido", "nombre"]
        verbose_name = "Árbitro"
        verbose_name_plural = "Árbitros"

    def __str__(self) -> str:
        return f"{self.apellido}, {self.nombre}"


# =================
# FIXTURE / FECHAS
# =================

class Fecha(models.Model):
    # Fecha de una Ronda (número correlativo y día)
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE, related_name="fechas")
    numero = models.PositiveIntegerField()
    fecha = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("ronda", "numero")
        ordering = ["ronda__torneo__liga__temporada", "ronda__torneo__nombre", "numero"]
        verbose_name = "Fecha"
        verbose_name_plural = "Fechas"

    def __str__(self) -> str:
        return f"{self.ronda} - Fecha {self.numero}"


class Partido(models.Model):
    # Partido por categoría en una fecha
    fecha_ref = models.ForeignKey(Fecha, on_delete=models.CASCADE, related_name="partidos")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="partidos")
    local = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="partidos_local")
    visitante = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="partidos_visitante")
    arbitro = models.ForeignKey(Arbitro, on_delete=models.SET_NULL, null=True, blank=True)
    dia_hora = models.DateTimeField(null=True, blank=True)

    goles_local = models.PositiveIntegerField(default=0)
    goles_visitante = models.PositiveIntegerField(default=0)
    jugado = models.BooleanField(default=False)  # equivalente a "jugada"
    observaciones = models.TextField(blank=True)

    class Meta:
        unique_together = ("fecha_ref", "categoria", "local", "visitante")
        ordering = ["fecha_ref__ronda__torneo__liga__temporada",
                    "fecha_ref__ronda__torneo__nombre",
                    "fecha_ref__numero"]
        verbose_name = "Partido"
        verbose_name_plural = "Partidos"

    def __str__(self) -> str:
        return f"[{self.categoria.nombre}] {self.local} vs {self.visitante} - {self.fecha_ref}"


# =====================
# FIXTURE POR TORNEO
# =====================


class FixturePartido(models.Model):
    RONDA_IDA = 1
    RONDA_VUELTA = 2
    RONDAS = (
        (RONDA_IDA, "Ronda 1 (Ida)"),
        (RONDA_VUELTA, "Ronda 2 (Vuelta)"),
    )

    torneo = models.ForeignKey(
        Torneo, on_delete=models.PROTECT, related_name="fixture_partidos"
    )
    ronda = models.SmallIntegerField(choices=RONDAS)
    fecha_nro = models.SmallIntegerField()
    local = models.ForeignKey(
        Equipo, on_delete=models.PROTECT, related_name="fixture_partidos_local"
    )
    visitante = models.ForeignKey(
        Equipo, on_delete=models.PROTECT, related_name="fixture_partidos_visitante"
    )
    played = models.BooleanField(default=False)
    goles_local = models.IntegerField(null=True, blank=True)
    goles_visitante = models.IntegerField(null=True, blank=True)
    programada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~Q(local=F("visitante")),
                name="chk_fixture_local_distinto_visitante",
            ),
            models.UniqueConstraint(
                fields=["torneo", "ronda", "fecha_nro", "local", "visitante"],
                name="uq_partido_fixture",
            ),
        ]
        ordering = [
            "torneo__liga__temporada",
            "torneo__nombre",
            "ronda",
            "fecha_nro",
            "local__club__nombre",
        ]
        verbose_name = "Partido de fixture"
        verbose_name_plural = "Partidos de fixture"

    def __str__(self) -> str:
        return (
            f"[{self.torneo}] Fecha {self.fecha_nro} Ronda {self.get_ronda_display()}: "
            f"{self.local} vs {self.visitante}"
        )


# ===========================
# EVENTOS Y REGLAS DE PUNTOS
# ===========================

class EventoPartido(models.Model):
    GOL = "GOL"
    TA = "TA"
    TR = "TR"
    WO = "WO"
    TIPOS = [
        (GOL, "Gol"),
        (TA, "Tarjeta Amarilla"),
        (TR, "Tarjeta Roja"),
        (WO, "Walkover"),
    ]

    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name="eventos")
    minuto = models.PositiveIntegerField(null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="eventos", null=True, blank=True)
    jugador = models.ForeignKey(Jugador, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=3, choices=TIPOS)
    detalle = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["partido_id", "minuto", "id"]
        verbose_name = "Evento de partido"
        verbose_name_plural = "Eventos de partido"

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} - {self.partido}"


class ReglaPuntos(models.Model):
    # Reglas por categoría (3/1/0, bonus WO, tope de goles)
    categoria = models.OneToOneField(Categoria, on_delete=models.CASCADE, related_name="regla_puntos")
    puntos_victoria = models.IntegerField(default=3)
    puntos_empate = models.IntegerField(default=1)
    puntos_derrota = models.IntegerField(default=0)
    puntos_walkover_ganador = models.IntegerField(default=3)
    puntos_walkover_perdedor = models.IntegerField(default=0)
    diferencia_maxima_goles = models.PositiveIntegerField(default=0)  # 0 = sin tope

    class Meta:
        verbose_name = "Regla de puntos"
        verbose_name_plural = "Reglas de puntos"

    def __str__(self) -> str:
        return f"Reglas {self.categoria}"


# ======================
# TABLA DE POSICIONES
# ======================

class TablaPosicion(models.Model):
    # "Materializada" (la recalculás tras actualizar un partido)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="tabla")
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="tabla")
    puntos = models.IntegerField(default=0)
    pj = models.PositiveIntegerField(default=0)
    pg = models.PositiveIntegerField(default=0)
    pe = models.PositiveIntegerField(default=0)
    pp = models.PositiveIntegerField(default=0)
    gf = models.PositiveIntegerField(default=0)
    gc = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("categoria", "equipo")
        ordering = ["-puntos", "-pg", "gc", "-gf"]
        verbose_name = "Tabla de posiciones"
        verbose_name_plural = "Tablas de posiciones"

    @property
    def dg(self) -> int:
        return self.gf - self.gc

    def __str__(self) -> str:
        return f"{self.categoria} - {self.equipo} ({self.puntos} pts)"


# ======================
# CONFIGURACIÓN / IDENTIDAD
# ======================

hex_color_validator = RegexValidator(
    regex=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
    message="Debe ser un color HEX válido, ej: #111827 o #2563eb",
)


class SiteIdentity(models.Model):
    # Singleton para identidad del sitio
    site_title = models.CharField(max_length=80, default="Sistema de Ligas")
    sidebar_bg = models.CharField(max_length=7, default="#111827", validators=[hex_color_validator])
    accent_color = models.CharField(max_length=7, default="#2563eb", validators=[hex_color_validator])
    logo_url = models.URLField(blank=True, help_text="URL de la imagen (max 300x300).")
    # Redes sociales
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    whatsapp_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)

    class Meta:
        verbose_name = "Identidad del sitio"
        verbose_name_plural = "Identidad del sitio"

    def __str__(self) -> str:
        return "Identidad"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
