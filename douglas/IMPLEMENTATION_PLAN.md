# IMPLEMENTATION_PLAN.md — plan vivo de Douglas Agent

**Convención: este archivo solo crece.** Nunca se borra un ítem. Un ítem
completado se marca `[x]` y se le agrega una línea `Resuelto:` con fecha y
commit/entrada de [`PROGRESS.md`](./PROGRESS.md) — pero se queda en el
archivo, no se mueve ni se elimina, para que quede el historial de qué se
planeó y cuándo se ejecutó. Un ítem nuevo se agrega al final de su sección
(o en una sección nueva si no encaja en las existentes), nunca insertado
reescribiendo contenido de arriba.

Cada ítem: qué falta, por qué importa, y qué se necesita para decidir/
ejecutar (una decisión del usuario, una investigación, o directamente
código). Si un ítem quedó pendiente de una decisión del usuario, se anota
exactamente cuál es la pregunta abierta.

---

## Pendientes activos

### [x] Hermes.exe de esta máquina de desarrollo sigue sin la corrección de detección de marca

El fix de detección de marca por ubicación del ejecutable (ver
`PROGRESS.md`, entrada del 2026-08-05/06 sobre Douglas/Hermes) solo toma
efecto en el binario que lo reciba. El `Hermes.exe` instalado en
`%LOCALAPPDATA%\hermes` en esta máquina sigue corriendo código anterior al
fix, así que sigue resolviendo su propio backend hacia el directorio de
Douglas cada vez que se abre — lo que vuelve a bloquear el update de
Douglas Agent si ambas apps están abiertas a la vez.

**Pregunta abierta para el usuario** (presentada, sin respuesta al momento
de escribir esto): ¿cómo debe recibir esa copia local de Hermes.exe el fix?
- (a) Dejar que corra su propio auto-update una vez (su propio mecanismo,
  no Douglas empujándole nada — pero técnicamente sigue "recibiendo código
  de este repo").
- (b) Reconstrucción/reinstalación manual de solo esa copia local, sin
  dejar una relación de auto-update activa.
- (c) Aceptar la limitación y no probar ambas apps abiertas a la vez hasta
  decidir.

No hay una solución puramente del lado de Douglas — el código que falla
está en el otro binario. Ver `PROGRESS.md` para el análisis completo de por
qué las variables de entorno globales no alcanzan para diferenciar dos
instalaciones del mismo código fusionado.

**Resuelto**: 2026-08-06 (ronda 4) — **ninguna de las 3 opciones (a/b/c)
de arriba hizo falta**. Se encontró una cuarta vía, 100% del lado de
Douglas, que no requiere ningún cambio al binario de `Hermes.exe`: dejar
de persistir `DOUGLAS_HOME` a nivel de usuario de Windows (el vector real
que ese `Hermes.exe` viejo heredaba automáticamente, sin terminal de por
medio) + renombrar el home por defecto de Douglas fuera de
`"douglas"`/`".douglas"` (la ruta hardcodeada que el fallback de esa build
vieja reconoce), con migración automática de instalaciones reales
existentes. Ver `PROGRESS.md`, entrada del 2026-08-06 "Ronda 4", para el
análisis completo (incluye por qué mover el directorio de *instalación*
del `.exe` a `Program Files` — consultado por el usuario — no habría
alcanzado por sí solo) y la verificación en vivo contra la instalación
real.

### [ ] Evaluar el merge con upstream (Hermes Agent v2026.8.3 / v0.20.0)

El fork está 62 commits adelante y ~905-908 commits atrás de
`upstream/main` (NousResearch/hermes-agent). El release v2026.8.3 es
enorme: ~3,650 commits, ~5,200 archivos, ~559k inserciones desde v0.19.0
— reescritura completa del desktop app (Artifacts, Plugin SDK,
quick-entry, multi-ventana, wave de rendimiento 60fps), voz conversacional,
A2A v1.0, webhooks salientes, y una sección de seguridad con CVEs de
dependencias parchadas.

**Investigado, sin ejecutar** (2026-08-06): no se encontró una sección
explícita de "Breaking Changes", pero el riesgo real es que el desktop
rediseñado toca exactamente los mismos archivos que el rebrand de Douglas
(branding, temas, instalador, `main.ts`) — alto riesgo de conflictos
extensos. El "auto-migration support floor" de configs (v12) que
menciona el release ya lo tiene este fork (`hermes_cli/config_migrations.py`),
no es nuevo.

**Confirmado peligroso**: el botón "Sync fork" de GitHub ofrece "Discard 62
commits" — borraría los 62 commits propios de Douglas para igualar a
upstream. **No usar ese botón.**

**Recomendación pendiente de aprobación**: crear una rama de integración
aparte (ej. `sync/upstream-v2026.8.3`) desde `main`, hacer `git merge`
local del tag `v2026.8.3` ahí (no en `main` directo), resolver conflictos
con atención especial en los archivos que ya documenta
[`CORE_PATCHES.md`](./CORE_PATCHES.md), probar extensamente, y solo
entonces mergear a `main`. Dado el tamaño, es un proyecto en sí mismo.

**Pregunta abierta para el usuario**: ¿arrancar la rama de integración
ahora, o queda pendiente hasta después de estabilizar el trabajo de
rebrand/tema en curso?

### [ ] `appId` de Windows sin resolver — duplicación en "Agregar o quitar programas"

Documentado en detalle en `douglas/README.md`, sección "Instalador NSIS /
identidad `appId` sin resolver". El cambio de `appId` de
`com.nousresearch.hermes` a `com.douglasdevsec.douglas-agent` hace que
Windows trate una instalación Douglas como una app completamente distinta
de una instalación Hermes previa — no hay pérdida de datos, pero sí una
segunda entrada en el desinstalador y un segundo acceso directo del Start
Menu. Deliberadamente sin tocar todavía — va junto con el renombrado
pendiente de `hermes-setup.exe` → `douglas-setup.exe` en
`apps/bootstrap-installer/src-tauri/src/paths.rs::installer_dest()`, antes
de la primera release pública.

### [ ] Módulo Social — plan de fases completo (Facebook primero, luego YouTube y el resto)

Ver `PROGRESS.md`, entrada del 2026-08-07, para la auditoría completa del
estado y la decisión de arquitectura del usuario. Resumen de esa
arquitectura: software multi-usuario (free/premium), cada usuario trae sus
propias credenciales de cada red (nunca una app de Meta/Google centralizada
de Douglas, nunca edición manual de `.env`), el módulo Social solo es
usable con una suscripción de Douglas Portal activa, y ese gate debe
resistir modificación local del cliente — hoy desbloqueado a propósito
para poder probar mientras se construye.

**Fase A — Frontend mockeado.** ✅ Completa antes de esta sesión (ver
`douglas/CORE_PATCHES.md`, "Capa social — Etapa A, Bloque 2" y "post-Etapa
A"). Panel, wizard genérico, tarjeta de aprobación registrada en el
pipeline de tools, teaser en el home, gate premium — todo construido,
todo mockeado.

**Fase B1 — Desbloqueo temporal + credenciales de Facebook.** ✅ Completa.
- [x] `isPremiumUser()` → `true` temporal, para poder probar.
- [x] `hermes_cli/social_platforms.py` — almacenamiento local de
  `FACEBOOK_APP_ID`/`FACEBOOK_APP_SECRET`/`FACEBOOK_PAGE_ID` por usuario,
  reutilizando `save_env_value`/`get_env_value`/`remove_env_value`
  (mismo patrón que WhatsApp Cloud/Slack/Telegram — nunca un almacén
  centralizado, nunca sale de la máquina del usuario). **Nota**: no quedó
  en `douglas/plugins/social_auth/` como se sugería originalmente en
  `fixtures.ts` — `douglas/` no es un paquete Python instalable (ver
  `CORE_PATCHES.md`, entrada de hoy, para el porqué completo). El futuro
  adaptador de publicación (Fase B3) sí irá en `plugins/platforms/facebook/`.
- [x] `GET`/`PUT /api/social/platforms/{platform_id}` en
  `hermes_cli/web_server.py` (toque mínimo de núcleo, registrado en
  `CORE_PATCHES.md`) — 8/8 tests en `tests/hermes_cli/test_social_platforms.py`.
- [x] Wizard de Facebook (`fixtures.ts`/`connection-wizard.tsx`/
  `index.tsx`) pide App ID/App Secret propios primero, luego Page ID, y
  guarda de verdad contra el backend de arriba — sin fingir que el paso
  final de autorización (todavía mockeado) ya está "conectado".

**Resuelto**: 2026-08-07. Ver `PROGRESS.md`, entrada del 2026-08-07, y
`CORE_PATCHES.md` para el detalle de verificación completo.

**Fase B2 — OAuth real de Facebook (pendiente).**
Intercambio de código de autorización contra la Graph API de Meta, usando
las credenciales que el propio usuario ingresó en B1. Guardar el resultado
(Page Access Token) con el mismo `save_env_value`.

**Pregunta abierta para el usuario**: estrategia de `redirect_uri`. Meta
exige un redirect URI válido para el flujo OAuth estándar de "Facebook
Login for Business". Dos caminos investigados (ver `PROGRESS.md` de hoy
para el detalle de qué ya existe en el repo como precedente):
- (a) **Servidor loopback temporal** — Electron levanta un `http://
  127.0.0.1:<puerto>/callback` efímero solo durante el flujo de conexión,
  captura el código, lo cierra. Meta permite `localhost` como redirect URI
  en apps en modo desarrollo. Más limpio para una app de escritorio, pero
  nuevo en este repo (ningún adaptador existente lo hace así).
- (b) **Pegado manual de URL** — mismo truco que ya usa
  `plugins/platforms/google_chat/oauth.py` (`redirect_uri` deliberadamente
  roto, el usuario copia el parámetro `code` de la URL fallida y lo pega
  de vuelta). Ya hay precedente funcionando en este repo, pero es una peor
  experiencia de usuario para un flujo que debería sentirse nativo desde
  el frontend.

**Fase B3 — Adaptador de publicación real (pendiente).**
`plugins/platforms/facebook/adapter.py`, siguiendo el patrón canónico ya
documentado en `AGENTS.md` (`plugins/platforms/irc/adapter.py`).
Publicación de texto + imagen a la Page vía Graph API usando el Page
Access Token de B2. Conectar `social_publish` como tool call real que el
agente pueda emitir — hoy el `approval-card.tsx` solo se alcanza con
datos mock.

**Fase B4 — Estado de conexión real en el panel (pendiente).**
`MOCK_SOCIAL_CONNECTIONS` en `fixtures.ts` sigue siendo estático. Falta un
`GET` que refleje si Facebook está realmente configurado/conectado, para
que el panel dependiente de estos datos deje de mostrar un estado
inventado.

**Fase C — Repetir B1-B4 para YouTube.**
Proyecto en Google Cloud + YouTube Data API v3 + pantalla de consentimiento
OAuth por parte de cada usuario (mismo modelo BYO-credenciales). El repo
ya depende de `google-api-python-client` (hoy solo usado para Google
Chat/Workspace) — reutilizable para el auth, no para upload de video, que
hay que construir. `plugins/platforms/google_chat/oauth.py` es la
referencia OAuth más cercana que ya existe en el repo (ver Fase B2).

**Fase D — Repetir para Instagram, LinkedIn, TikTok, X.**
Instagram depende de tener una Page de Facebook vinculada (Meta lo exige),
así que naturalmente sigue después de Facebook, no en paralelo.

**Fase E — Entitlement real de Douglas Portal, blindado (pendiente, proyecto propio).**
Esta es la pieza más grande y la única que no es "construir un adaptador
más" — requiere un backend de Douglas Portal que **hoy no existe en
absoluto** (`douglas/billing/` sigue vacío, es un scaffold). Diseño
propuesto (sin construir todavía): el backend emite un token de
entitlement firmado (ej. JWT con clave privada del servidor) cuando la
suscripción está activa; el cliente desktop verifica la firma con una
clave pública embebida en el build, sin confiar en ningún flag local. Así
un usuario que parchee su copia local del cliente no puede fabricar un
token válido sin comprometer el servidor — el objetivo realista de
"blindado", no una promesa de invulnerabilidad total (ninguna app
instalada localmente lo es).

**Preguntas abiertas para el usuario, antes de diseñar Fase E a fondo**:
¿Douglas Portal se construye sobre Stripe directo (como ya insinúa
`douglas/README.md` para `douglas/billing/`), o se evalúa reutilizar/
integrar con algo del sistema de Nous Portal? ¿Cuándo se prioriza esta
fase — antes o después de tener Facebook/YouTube funcionando de punta a
punta con el gate desbloqueado?

### [ ] Deuda pre-existente sin commitear: swap de icono de marca

Desde antes de esta sesión (sin tocar, ver nota en cada resumen de commit
de esta sesión): `apps/desktop/assets/icon.png` borrado y
`apps/desktop/assets/logo_green.png` agregado, ambos sin commitear todavía.
No se tocó porque no era parte de las tareas pedidas explícitamente en las
sesiones que produjeron este archivo. Si el swap ya está completo y
verificado, falta commitearlo; si sigue en progreso, falta terminarlo.

---

## Completados (quedan aquí como registro — no borrar)

### [x] Icono de la aplicación no se mostraba en la barra de tareas

Investigado a fondo: el `.exe` instalado ya tenía el icono correcto
embebido (verificado extrayéndolo directo del binario), y el AUMID estaba
consistente entre código y `package.json`. No era un bug de código — era
caché de iconos de Windows en la máquina específica del usuario. Se limpió
`IconCache.db` + `iconcache_*.db`, se corrió `ie4uinit.exe -show`, se
reinició Explorer.
**Resuelto**: 2026-08-06. Sin commit (no era un bug de código).

### [x] Toggle de tema claro/oscuro + set de iconos propio (Tabler en vez de VS Code codicons)

Ver `PROGRESS.md`, entrada del 2026-08-05.
**Resuelto**: 2026-08-05. Commit `26cfc00a1`.

### [x] Douglas Agent nunca debe compartir instalación/venv con Hermes (3 rondas)

Ver `PROGRESS.md`, entrada del 2026-08-05/06. Fallback inseguro de
directorio existente eliminado; persistencia de env var movida de
`HERMES_HOME` a `DOUGLAS_HOME`; detección de marca por ubicación del
ejecutable agregada a las tres implementaciones (TS/Python/Rust).
**Resuelto**: 2026-08-05 (ronda 1, commit `ab3486ce0`), 2026-08-06 (rondas
2-3, commit `863ec8500`).

### [x] Identidad verde emerald: temas `douglas`/`douglas-noir` + fondo del chat con imagen

Ver `PROGRESS.md`, entrada del 2026-08-05/06.
**Resuelto**: 2026-08-05/06. Commits `6731be6a9`, `f15d10fd7`.

### [x] `PROGRESS.md` + `IMPLEMENTATION_PLAN.md` + revisión de `AGENTS.md`/`CAPABILITIES.md`

Este mismo trabajo. Ver `PROGRESS.md`, entrada del 2026-08-06.
**Resuelto**: 2026-08-06. Sin commit todavía al momento de escribir esta
línea — ver el commit inmediatamente posterior en `git log -- douglas/IMPLEMENTATION_PLAN.md`.
