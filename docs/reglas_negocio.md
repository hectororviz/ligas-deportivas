# Reglas de negocio existentes

Este documento resume las reglas de negocio implementadas en la aplicación Django original para que puedan reutilizarse al migrar la solución a Flutter. La información está organizada en torno al dominio deportivo, los procesos administrativos y, en especial, la generación automática del fixture.

## 1. Dominio y relaciones principales

### 1.1. Estructura de la competencia
- **Club (`Club`)**: entidad base con nombre único, escudo y dirección opcionales. Ordenados alfabéticamente.
- **Liga (`Liga`)**: agrupador temporal (por ejemplo, "Liga Metropolitana 2024"). Se define por `nombre` y `temporada`, únicos en conjunto, y sirve como raíz para categorías y torneos.
- **Torneo (`Torneo`)**: subdivisión de una liga (Apertura, Clausura, etc.). Cada torneo se asocia a una única liga y su combinación `(liga, nombre)` debe ser única.
- **Ronda (`Ronda`)**: fases internas dentro de un torneo (Fase Única, Playoffs, etc.). Actualmente se utiliza para numerar fechas de una única fase regular.

### 1.2. Participantes y planteles
- **Categoría (`Categoria`)**: división etaria o competitiva dentro de una liga. Indica si está activa, el horario habitual y si sus resultados suman a una tabla general.
- **Equipo (`Equipo`)**: asociación de un club con una categoría específica; corresponde al equipo que jugará cada encuentro de esa categoría. Un club sólo puede tener un equipo por categoría.
- **Jugador (`Jugador`)**: pertenece a un equipo y almacena datos personales básicos.
- **Árbitro (`Arbitro`)**: catálogo independiente para designaciones.

### 1.3. Calendario y resultados
- **Fecha (`Fecha`)**: número correlativo y día opcional dentro de una ronda.
- **Partido (`Partido`)**: representa el encuentro por categoría ya calendarizado en una fecha concreta e incluye asignación de árbitro, marcador y banderas de jugado.
- **PartidoFixture (`PartidoFixture`)**: tabla generada automáticamente que arma el fixture “base” para un torneo completo (ida y vuelta). Sirve como master de cruces por club; sobre él se cargan resultados globales y, opcionalmente, resultados por categoría (`ResultadoCategoriaPartido`).
- **ReglaPuntos** y **TablaPosicion**: definen la parametrización del sistema de puntuación (3-1-0, topes de goles, WO) y la tabla materializada para consultas rápidas. Actualmente el recálculo de tablas está pendiente de automatización, pero el modelo describe los campos necesarios.

### 1.4. Identidad del sitio
`SiteIdentity` encapsula colores, logo y enlaces sociales mostrados en la portada pública y en el panel administrativo.

## 2. Reglas operativas implementadas

### 2.1. ABM centralizado por permisos
- Toda gestión se realiza desde un panel con autenticación de Django (`/admin/login`).
- Cada vista administrativa exige un permiso específico (`view_*`, `add_*`, `change_*`, `delete_*`). La navegación lateral oculta opciones sin permiso.
- Las altas y ediciones se realizan mediante modales AJAX reutilizables; esto permite guardar y continuar creando registros sin abandonar la lista.

### 2.2. Generación masiva de equipos por liga
- Desde la pantalla de equipos existe una acción “Generar” que recibe un club y una liga.
- La regla crea, para cada categoría de la liga seleccionada, un registro `Equipo` asociado al club. El alias sugerido sigue el patrón `"{club} - {categoria}"`.
- Si el equipo ya existía se respeta el alias personalizado; si estaba vacío se autocompleta.
- Se muestran mensajes diferenciados: cantidad creada, cantidad omitida o advertencia si la liga aún no tiene categorías.

### 2.3. Gestión de fixture y resultados
- En la vista de fixture de un torneo se listan todos los clubes con equipos en la liga correspondiente. Si hay menos de dos clubes se bloquea la generación.
- Las fechas por ronda se calculan como `N-1` cuando el número de clubes `N` es par, o `N` cuando es impar (por la presencia del “libre”).
- Los partidos se agrupan por ronda (ida/vuelta) y fecha. Cada fila muestra estado agregado (`pendiente`, `parcial`, `jugado`) según la cantidad de categorías con resultado cargado.
- Los resultados se editan en un formulario dinámico que exige completar ambos marcadores (local/visitante) o dejar ambos vacíos. Al completar todas las categorías el partido se marca como jugado y se consolidan los totales globales.

## 3. Algoritmo de generación del fixture

La generación se implementa mediante el **método del círculo** (round-robin). Las reglas clave son:

1. **Normalización de clubes**: se eliminan nulos y duplicados preservando el orden original. Todos los clubes deben existir en base de datos (tener `pk`).
2. **Preparación de slots**: si la cantidad de clubes es impar, se agrega un marcador `None` que representa el “bye”. El total de fechas por ronda es `total_slots - 1`.
3. **Rotación circular**: en cada fecha se emparejan los extremos de la lista (`arrangement`). Tras registrar los cruces se hace una rotación manteniendo fijo el primer elemento y moviendo el último a la segunda posición.
4. **Asignación de localías**: en fechas impares (1-indexadas) el primer elemento de cada pareja oficia de local; en las pares se invierte. Esto garantiza balance de localías.
5. **Cálculo de byes**: cuando aparece el marcador `None`, el club enfrentado queda libre en esa fecha. Cada club tendrá exactamente un descanso por ronda en torneos con N impar.
6. **Generación de vuelta**: se replica la ronda de ida invirtiendo local/visitante por cruce y conservando el orden de fechas.
7. **Persistencia transaccional**: antes de crear registros se verifica, en una transacción atómica, que el torneo no tenga fixture previo. Si existe, se aborta con `FixtureAlreadyExists`. Errores de migración u operaciones de base se capturan como `FixtureGenerationError` con un mensaje orientado a correr migraciones.

### 3.1. Complejidad y conteos
- Cantidad total de partidos creados: `N * (N - 1)` (cada club enfrenta a todos dos veces).
- Por ronda se generan `(total_slots - 1) * (total_slots / 2)` partidos; en caso impar `total_slots = N + 1` incluye el bye.
- Balanceo: al finalizar la generación, cada club juega la misma cantidad de veces de local y visitante. Se verificó con pruebas unitarias.

### 3.2. Ejemplo trabajado (6 clubes)
```
Clubes: A, B, C, D, E, F (N = 6, par)
Fechas por ronda = 5

Fecha 1 ida: (A vs F), (B vs E), (C vs D)
Fecha 2 ida: (F vs D), (E vs C), (A vs B)
...
Fecha 5 ida: (A vs C), (B vs F), (D vs E)

Ronda de vuelta: mismas parejas invertidas, manteniendo el orden de fechas.
Total de partidos = 6 * 5 = 30 (15 por ronda).
```

### 3.3. Ejemplo trabajado (5 clubes)
```
Clubes: A, B, C, D, E (N = 5, impar)
Se agrega un slot "Libre" (total_slots = 6)
Fechas por ronda = 5 (total_slots - 1)

En cada fecha un club queda libre; tras cinco fechas todos descansaron una vez.
Total de partidos = 5 * 4 = 20 (10 por ronda).
```

## 4. Gestión de resultados por categoría

- El formulario dinámico genera campos `categoria_{id}_local` y `categoria_{id}_visitante` para cada categoría asociada a la liga del torneo.
- La validación fuerza que ambos campos estén presentes o ausentes simultáneamente.
- Durante el guardado se actualizan o eliminan resultados existentes y se recalcula el estado global del partido:
  - **Sin resultados** o **categorías pendientes**: el partido vuelve a estado pendiente, sin totales globales.
  - **Todas las categorías cargadas**: `jugado = True` y se consolidan sumas de goles para mostrar un marcador general en el fixture.

## 5. Reglas auxiliares

- **Mensajería y permisos**: cada acción concluye con feedback (`messages.success/info/warning/error`) según el resultado. Esto debe replicarse en Flutter para mantener la comunicación con el usuario administrativo.
- **Manejo de integridad**: los modelos definen `unique_together` y `ordering` para asegurar consistencia. Cualquier migración a Flutter debe respetar estas restricciones en la nueva capa de datos o API.
- **Identidad del sitio**: los colores y logos son parametrizables; se recomienda contemplar un endpoint o repositorio centralizado para que la app Flutter los consuma y refleje cambios en tiempo real.

## 6. Consideraciones para la reimplementación en Flutter

1. **Persistencia**: mantener la lógica de fixture y resultados del lado del backend (Django o nuevo servicio) garantiza consistencia. La app Flutter debería consumir endpoints que expongan estas operaciones.
2. **Transaccionalidad**: la generación del fixture debe seguir siendo atómica. Si se reimplementa el backend, replicar la verificación de existencia y los bloqueos de escritura concurrentes.
3. **Estados del fixture**: conservar la semántica de `pendiente/parcial/jugado` para que la UI mobile pueda mostrar progresos parciales cuando faltan resultados de alguna categoría.
4. **Cálculo de tablas**: aunque hoy no se actualiza automáticamente, el modelo de datos permite implementar un servicio que recalcule `TablaPosicion` al confirmar resultados. Planificar este feature si la app Flutter requerirá tablas actualizadas.
5. **Byes y calendario**: cuando el número de clubes es impar, la UI debe mostrar explícitamente el club libre en cada fecha para evitar confusiones.

Con esta descripción se preservan las reglas de negocio críticas para la nueva implementación. Se recomienda complementar con los diagramas de datos y, si se expone una API, documentar los contratos para cada flujo (generar fixture, cargar resultados, crear equipos, etc.).
