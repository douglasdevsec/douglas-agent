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

### [ ] Hermes.exe de esta máquina de desarrollo sigue sin la corrección de detección de marca

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
