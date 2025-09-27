# Ligas Deportivas

Aplicación web en Django para administrar ligas deportivas con panel unificado para ligas, clubes, fixture y configuraciones de identidad visual. El proyecto expone una navegación pública mínima y un panel moderno optimizado para flujo de trabajo diario de secretarías deportivas.【F:ligas/templates/ligas/base_admin.html†L1-L210】【F:ligas/templates/ligas/home.html†L1-L34】

## Requisitos para continuar el desarrollo

### Dependencias comunes
- Python 3.13 o superior (requerido por `pyproject.toml`).【F:pyproject.toml†L1-L18】
- Git.
- PostgreSQL opcional para desarrollo (el proyecto cae a SQLite si no hay variables de entorno configuradas).【F:config/settings.py†L42-L71】

### Windows
1. Instalar [Python 3.13](https://www.python.org/downloads/windows/) marcando la opción *Add python.exe to PATH*.
2. Crear un entorno virtual desde PowerShell:
   ```powershell
   py -3.13 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Actualizar `pip` e instalar dependencias con `pip` leyendo la configuración del proyecto:
   ```powershell
   python -m pip install --upgrade pip
   pip install -e .
   ```
4. Copiar `.env.example` a `.env` (o crear uno nuevo) y definir `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` y, si se usa PostgreSQL, las variables `POSTGRES_*` correspondientes.【F:config/settings.py†L21-L71】

### Linux
1. Instalar Python 3.13 mediante el gestor de paquetes o [pyenv](https://github.com/pyenv/pyenv) y asegurarse de tener `python3.13` en el PATH.
2. Crear el entorno virtual:
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   ```
3. Actualizar `pip` e instalar las dependencias declaradas en `pyproject.toml`:
   ```bash
   python -m pip install --upgrade pip
   pip install -e .
   ```
4. Configurar el archivo `.env` igual que en Windows.【F:config/settings.py†L21-L71】

### Comandos de desarrollo útiles
- Ejecutar migraciones: `python manage.py migrate`.
- Crear un superusuario para acceder a `/admin/`: `python manage.py createsuperuser`.
- Levantar el servidor de desarrollo: `python manage.py runserver`.
- Correr la batería de pruebas automatizadas: `python manage.py test`.【F:ligas/tests.py†L1-L200】

## Requisitos para desplegar en un servidor
1. Sistema operativo Linux (Ubuntu/Debian recomendados) con Python 3.13 instalado.
2. Base de datos PostgreSQL 14+ (recomendado) o SQLite para despliegues pequeños.【F:config/settings.py†L42-L71】
3. Variables de entorno definidas para `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `ALLOWED_HOSTS` (via servidor web) y credenciales `POSTGRES_*` en caso de usar PostgreSQL.【F:config/settings.py†L21-L71】
4. Dependencias instaladas dentro de un entorno virtual: `pip install -e .`.
5. Servidor WSGI/ASGI (Gunicorn, uWSGI o Daphne) invocando `config.wsgi` o `config.asgi` según corresponda.【F:config/wsgi.py†L1-L16】【F:config/asgi.py†L1-L16】
6. Servidor web inverso (Nginx/Apache) para terminación TLS y servir archivos estáticos. Generar los estáticos con `python manage.py collectstatic` antes de publicar.
7. Programar el proceso de migraciones en cada despliegue (`python manage.py migrate`).

## Descripción de la herramienta
La plataforma ofrece un panel lateral con menús contextuales, modales reutilizables para altas y edición, soporte para colapsar la barra y persistir preferencias en `localStorage`, lo que facilita administrar entidades sin salir del flujo de trabajo.【F:ligas/templates/ligas/base_admin.html†L1-L210】
La vista pública inicial expone el título del sitio, acceso directo al panel administrativo y enlaces a redes sociales definidos por la identidad del sitio.【F:ligas/templates/ligas/home.html†L1-L34】【F:ligas/templates/ligas/configuracion/identidad.html†L1-L74】

## Workflow actual
1. **Inicio de sesión**: se utiliza la autenticación estándar de Django (`/admin/login/`) y los permisos asignados controlan qué secciones aparecen en el menú lateral.【F:ligas/abm_views.py†L1-L110】【F:ligas/templates/ligas/base_admin.html†L25-L138】
2. **Gestión diaria**:
   - Las listas (ligas, clubes, torneos, rondas, categorías, equipos, jugadores, árbitros) comparten paginación configurable mediante querystring y acciones en modales para alta/edición/eliminación.【F:ligas/abm_views.py†L110-L420】【F:ligas/templates/ligas/administracion/liga_list.html†L1-L34】
   - Los formularios se cargan en modales AJAX que permiten guardar y seguir creando registros sin abandonar la página actual.【F:ligas/abm_views.py†L44-L109】【F:ligas/templates/ligas/administracion/_modal_form.html†L1-L57】
3. **Fixture**:
   - Desde cada torneo se puede generar el fixture con método de “círculo”, revisar rondas/fechas y cargar resultados por categoría; los estados del partido cambian automáticamente según los datos ingresados.【F:ligas/abm_views.py†L182-L420】【F:ligas/fixture.py†L1-L120】【F:ligas/templates/ligas/administracion/torneo_fixture.html†L1-L76】
   - El formulario de resultados valida que ambos marcadores estén presentes y calcula el estado general del partido.【F:ligas/forms.py†L1-L69】【F:ligas/abm_views.py†L400-L480】
4. **Identidad visual**: la pantalla de configuración permite definir colores, logo y enlaces sociales que se reflejan en todo el panel y home público.【F:ligas/abm_views.py†L720-L760】【F:ligas/templates/ligas/configuracion/identidad.html†L1-L74】
5. **Pruebas**: existe una suite de tests que cubre generación de equipos por liga, creación del fixture, flujo de resultados y validaciones para mantener la calidad antes de publicar cambios.【F:ligas/tests.py†L1-L280】

## Funcionalidades implementadas
- **Modelado completo de la competencia**: ligas, torneos, rondas, categorías, equipos, jugadores, árbitros y reglamentos de puntos, con ordenamientos y restricciones de integridad definidos en los modelos.【F:ligas/models.py†L1-L240】【F:ligas/models.py†L240-L360】【F:ligas/models.py†L360-L460】
- **Panel administrativo unificado** con navegación lateral sensible a permisos, tablas paginadas y acciones en modales para operaciones CRUD rápidas.【F:ligas/templates/ligas/base_admin.html†L1-L210】【F:ligas/urls.py†L3-L74】
- **Generación automática de fixture ida/vuelta** usando el método de círculo, con manejo de byes y control de migraciones pendientes.【F:ligas/fixture.py†L1-L160】【F:ligas/abm_views.py†L182-L320】
- **Carga y seguimiento de resultados por categoría** que actualiza estado del partido y valida datos antes de persistirlos.【F:ligas/forms.py†L1-L69】【F:ligas/abm_views.py†L360-L480】
- **Configuración centralizada de identidad y redes sociales**, reflejada en el home público y el panel lateral.【F:ligas/models.py†L420-L460】【F:ligas/abm_views.py†L720-L760】【F:ligas/templates/ligas/home.html†L1-L34】
- **Suite de pruebas automatizadas** que cubre generación de equipos, fixture y flujos de resultados para asegurar regresiones mínimas.【F:ligas/tests.py†L1-L280】

## Próximos pasos sugeridos
- Agregar documentación para despliegues con Docker y scripts de inicialización.
- Exponer API pública para consumo móvil (REST/GraphQL) basada en la estructura ya modelada.
- Integrar cálculos automáticos de tabla de posiciones actualizando `TablaPosicion` al guardar resultados.
