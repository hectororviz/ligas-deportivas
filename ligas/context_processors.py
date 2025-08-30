from django.db.utils import OperationalError, ProgrammingError
from .models import SiteIdentity


def identity(request):
    """Inyecta la identidad del sitio en el contexto de templates.
    Tolera falta de migraciones/tablas devolviendo defaults in-memory.
    """
    default = {
        "site_title": "Sistema de Ligas",
        "sidebar_bg": "#111827",
        "accent_color": "#2563eb",
        "logo_url": "",
    }
    try:
        obj = SiteIdentity.get_solo()
        return {"identity": obj}
    except (OperationalError, ProgrammingError):
        # Tabla aún no creada, devolvemos defaults simples
        class Obj:
            site_title = default["site_title"]
            sidebar_bg = default["sidebar_bg"]
            accent_color = default["accent_color"]
            logo_url = default["logo_url"]

        return {"identity": Obj()}

