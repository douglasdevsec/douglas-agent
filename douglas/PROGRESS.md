# PROGRESS.md — bitácora de progreso de Douglas Agent

**Convención: este archivo solo crece.** Cada sesión de trabajo (humana o de
un agente) agrega una entrada nueva al final, con fecha. Nunca se reescribe
ni se borra una entrada anterior — si algo cambió de rumbo, se anota una
entrada nueva que lo diga, no se edita la vieja. El objetivo es que cualquier
sesión futura (de cualquier herramienta: Claude Code, Antigravity, o un
humano leyendo en frío) pueda reconstruir *por qué* el código está como está
sin tener que releer `git log` completo ni la conversación original.

Qué va en una entrada: qué se hizo, por qué (el problema real, no solo la
tarea), qué archivos/commits quedaron, y cómo se verificó. Lo que NO va aquí:
detalle línea por línea de un fix (eso vive en el mensaje del commit y, si
tocó núcleo, en [`CORE_PATCHES.md`](./CORE_PATCHES.md)) — esto es la vista
de alto nivel para orientarse rápido.

Para el estado de tareas pendientes/en curso, ver
[`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) — ese archivo lleva el
"qué falta"; este lleva el "qué se hizo y por qué".

Para el registro específico de cada archivo del núcleo (fuera de `douglas/`)
que se tocó y por qué, ver [`CORE_PATCHES.md`](./CORE_PATCHES.md) — este
archivo (`PROGRESS.md`) es más amplio: cubre todo el trabajo, no solo los
toques al núcleo.

---

## 2026-08-05 — Identidad visual: toggle de tema + set de iconos propio

**Problema**: el modo oscuro/claro del sistema no tenía forma de cambiarse
desde la barra de título (ya existía el atajo Shift+X pero sin botón
visible), y todos los iconos de la interfaz eran literalmente los mismos
que Hermes Agent (fuente `@vscode/codicons`, la misma que usa el propio VS
Code) — Douglas Agent no tenía identidad visual propia más allá del texto.

**Qué se hizo**:
- Botón de tema claro/oscuro en la barra de título, al lado de "Open
  Settings", reutilizando el store de tema ya existente
  (`apps/desktop/src/themes/context.tsx`).
- Reemplazo del componente `Codicon` (usado en 95 archivos, 235+ usos) para
  que renderice iconos de Tabler (`@tabler/icons-react`, ya era dependencia
  parcial) en vez de la fuente de VS Code, mapeando cada nombre de codicon a
  un icono de Tabler equivalente semánticamente
  (`apps/desktop/src/components/ui/codicon-glyphs.ts`, ~160 iconos
  mapeados). Cero cambios en los 95 archivos que llaman `<Codicon name=...>`
  — el mapeo vive en un solo punto de entrada.
- `data-codicon` como atributo en el DOM para que tests (y futuro código)
  puedan identificar qué icono semántico se renderizó, independiente de qué
  icono de Tabler lo respalda.

**Verificación**: typecheck + eslint limpios; 3 tests que aserteban sobre la
vieja clase CSS `codicon-check` reescritos para usar `data-codicon`; suite
completa de tests del proyecto corrida (24 archivos fallando, ninguno
relacionado — confirmado cruzando la lista de archivos fallidos contra los
95 que usan `Codicon`).

**Commit**: `26cfc00a1`

---

## 2026-08-05 / 2026-08-06 — Douglas y Hermes no deben compartir instalación (3 rondas)

**Problema real** (descubierto probando la actualización de la app en vivo,
no en abstracto): un `Hermes.exe` instalado en la misma máquina que Douglas
Agent — migrado hace tiempo para correr este mismo código fusionado —
terminó lanzando su propio backend contra el `venv` de
`%LOCALAPPDATA%\douglas`, el mismo que usaba Douglas Agent.exe al mismo
tiempo. Los dos backends chocaron por locks de archivos, bloqueando el
auto-updater de Douglas Agent con "another Douglas Agent process is using
this installation". El objetivo de fondo: cuando la app se lance
públicamente, muchos usuarios ya tendrán el Hermes Agent original de
NousResearch instalado, y eso nunca debe causar conflicto.

Se resolvió en tres pasadas, cada una descubierta al probar la anterior
contra una instalación real:

**Ronda 1 — el fallback de "adoptar un directorio hermes existente" era
inseguro.** La cadena de resolución de home (`hermes_bootstrap.py`,
`main.ts::resolveHermesHome()`, `paths.rs::hermes_home()`) prefería un
`%LOCALAPPDATA%\douglas` existente, y si no, un `%LOCALAPPDATA%\hermes`
existente — diseñado para adoptar datos propios de antes del rebrand, pero
indistinguible de "hay una instalación ajena y genuina de Hermes en esta
máquina". Se eliminó el fallback: sin `DOUGLAS_HOME`/`HERMES_HOME`
explícitas, el default es SIEMPRE el directorio de douglas, nunca se
escanea un `hermes` existente. `tests-douglas/test_compat_home.py`
reescrito (18/18 pasan). **Commit `ab3486ce0`.**

**Ronda 2 — `install.ps1` persistía `HERMES_HOME`, no `DOUGLAS_HOME`, en el
entorno de usuario de Windows.** `HERMES_HOME` es la variable *propia* de
Hermes Agent, no una inventada por Douglas — y las variables de entorno de
Windows son por-usuario, no por-app. Cualquier instalación ajena y genuina
de Hermes heredaría el directorio de Douglas en la próxima terminal. Ahora
persiste `DOUGLAS_HOME`, y migra/borra un `HERMES_HOME` heredado si su
valor contiene `\douglas\`. **Commit `863ec8500`** (junto con la ronda 3).

**Ronda 3 — ni con la ronda 1+2 alcanzaba para el Hermes.exe migrado de
esta máquina de desarrollo**, porque entiende `DOUGLAS_HOME` con la misma
prioridad que Douglas Agent.exe (mismo código fusionado). Las tres
implementaciones ganan detección de marca por ubicación física del
ejecutable/checkout corriendo (`app.getPath('exe')` / `Path(__file__)` /
`current_exe()` contra `%LOCALAPPDATA%\hermes`) en vez de defaultear a
"douglas" incondicionalmente — la única señal que de verdad difiere entre
las dos instalaciones, porque toda otra identidad en tiempo de ejecución
(`app.getName()`, el AUMID) ya reporta "Douglas Agent" sin importar qué
ejecutable la lanzó. `tests-douglas/test_compat_home.py` gana 2 tests
(20/20 pasan), incluyendo uno que reproduce el incidente exacto. **Commit
`863ec8500`.**

**Limitación conocida, sin resolver todavía**: la detección de marca por
ubicación del ejecutable solo toma efecto en el binario que la reciba. El
`Hermes.exe` específico de esta máquina de desarrollo, al momento de
escribir esto, sigue corriendo código previo a estos fixes — sigue
apuntando al directorio de Douglas hasta que esa copia se actualice de
alguna forma. Ver [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md).

---

## 2026-08-05 / 2026-08-06 — Verde emerald como identidad de marca (tema + fondo del chat)

**Problema**: el modo oscuro por defecto (skin `nous`) usaba el azul
heredado de Nous Research. El instalador (`apps/bootstrap-installer`) ya
tenía su propia paleta verde emerald desde el rebrand anterior, pero el
desktop app nunca la adoptó.

**Qué se hizo**:
- Verificados los valores exactos que ya usaba el instalador
  (`apps/bootstrap-installer/src/styles.css` `:root.dark`) — escala emerald
  de Tailwind (`#052e21`/`#021a13`/`#065f46`/`#10b981`), la misma que ya
  usa el wordmark de la intro del chat (`text-emerald-600 dark:text-emerald-400`
  en `intro.tsx`).
- Dos temas nuevos en `apps/desktop/src/themes/presets.ts`: `douglas`
  (verde emerald en todo, igual al instalador) y `douglas-noir` (lienzo de
  chat casi negro, verde confinado a sidebar/popovers/acentos).
  `douglas-noir` es ahora el `DEFAULT_SKIN_NAME`.
- Imagen de fondo subida por el usuario, aplicada SOLO al área de chat
  principal (nunca sidebar, nunca popovers/diálogos, nunca una ventana
  secundaria/flotante — gateado explícitamente en
  `ThreadMessageList` vía `isSecondaryWindow()`), con un nuevo campo
  opcional `chatBackgroundImage` en el modelo `DesktopTheme`.
- Iteración de diseño: la imagen sola se veía demasiado saturada/precisa.
  Se separó en dos capas — imagen desenfocada (10px, sobredimensionada
  para que el blur no muestre bordes) + tinte semitransparente encima sin
  desenfocar, tomado del propio color de sidebar del tema vía
  `--theme-chat-background-tint` (así un tema sin imagen no hereda el
  tinte verde por accidente).

**Verificación**: sin poder tomar captura de pantalla en este entorno
(limitación del panel de navegador de la sesión), se verificó inyectando
JS en el servidor de desarrollo real y leyendo estilos computados: seeds de
color exactos, `backgroundImage`/`filter: blur()`/`backgroundColor` del DOM
real coincidiendo con lo diseñado, variable de tinte resolviendo a
`transparent` (no seteada) para temas sin imagen. 66→81 tests de
`themes/` y `thread/list` pasando a través de las iteraciones.

**Commits**: `6731be6a9` (temas + imagen), `f15d10fd7` (blur + tinte).

---

## 2026-08-06 — Higiene de documentación: `AGENTS.md`, `CAPABILITIES.md`, y este archivo

**Problema**: este repo no tiene `CLAUDE.md` — usa `AGENTS.md` como guía
para agentes de IA, pero ese archivo es casi enteramente el de Hermes
Agent original (heredado del fork); la sección específica de Douglas
("REGLAS DEL PROYECTO") es breve y no reflejaba lecciones aprendidas en
sesiones recientes (el patrón de variables de entorno globales
compartidas entre dos instalaciones del mismo código). Tampoco existía un
archivo vivo de progreso — `douglas/history/` guarda documentos de
planificación congelados del arranque del proyecto, no algo que se siga
actualizando.

**Qué se hizo**: este archivo (`PROGRESS.md`) y
[`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md), creados a pedido
explícito del usuario, con la convención de solo-agregar. Referencia
cruzada añadida en `AGENTS.md` (regla 9) y en la tabla de reglas de este
README. Nueva entrada en "Known Pitfalls" de `AGENTS.md` sobre variables de
entorno globales compartidas. `CAPABILITIES.md` (sección D10) actualizado:
el `appId`/protocolo que tenía anotado estaba desactualizado (aún decía
`com.nousresearch.hermes` / `hermes://`), y la línea de "TEMAS" no mencionaba
el mecanismo de `chatBackgroundImage` ni los presets `douglas`/`douglas-noir`.

---

## 2026-08-06 — Ronda 4: fix definitivo para el `Hermes.exe` de esta máquina (sin tocar su código)

**Problema real**: la limitación conocida de la ronda 3 (ver entrada
anterior) seguía sin resolverse — el `Hermes.exe` real instalado en esta
máquina bloqueaba el auto-updater de Douglas Agent cada vez que ambos
estaban abiertos a la vez. Se investigó a fondo el checkout real de
`%LOCALAPPDATA%\hermes\hermes-agent`: está en el commit `8f9cab5a57`
(2026-08-03), confirmado **anterior a la ronda 1** vía
`git merge-base --is-ancestor ab3486ce0 HEAD` (exit 1 = no es ancestro).
Su `hermes_bootstrap.py`, leído tal como está compilado ahí, hace dos
cosas: (1) alias `DOUGLAS_HOME` → `HERMES_HOME` (con `DOUGLAS_HOME`
ganando) leído del entorno del proceso por nombre, sin importar la ruta;
(2) sin ninguna variable seteada, prefiere un `~/.douglas`/
`%LOCALAPPDATA%\douglas` existente — la ruta hardcodeada, literal.

El usuario preguntó, como consulta, si cambiar la instalación por defecto
de Douglas Agent a `C:\Program Files (x86)\Douglas Agent` (una ubicación
distinta a la de Hermes) resolvería el problema. Investigado y descartado:
ataca el vector equivocado (la ubicación del `.exe` instalado, no la
variable de entorno global ni la ruta del HOME/datos de usuario, que ya
son directorios distintos), y además `Program Files` normalmente exige
elevación de administrador, lo que complicaría el auto-updater sin
necesidad.

**Qué se hizo** (2 cambios combinados, 100% del lado de Douglas, cero
cambios al binario de Hermes.exe):
1. `install.ps1` deja de persistir `DOUGLAS_HOME` a nivel de usuario de
   Windows por defecto (seguía seteándose a nivel de sesión, y sigue
   honrándose con máxima prioridad si el usuario la exporta manualmente).
   Validado empíricamente ANTES de implementar: se corrió
   `douglas.exe --version`/`doctor` con `DOUGLAS_HOME`/`HERMES_HOME`
   completamente eliminadas del proceso — resolvió el directorio real
   correctamente (config v33, 1 sesión, memorias, auth logueado), sin
   necesitar la variable para nada.
2. El directorio douglas-branded por defecto se renombra de
   `"douglas"`/`".douglas"` a `"douglas-agent"`/`".douglas-agent"` en las
   tres implementaciones, con migración de una sola vez (renombra en el
   lugar un `"douglas"` preexistente, atómico, nunca toca nada
   hermes-named). `install.ps1`/`install.sh` ganan el mismo paso de
   migración, más limpieza de un `DOUGLAS_HOME` persistido por una versión
   anterior de este mismo instalador.

Con esto, ningún proceso ajeno en la máquina (viejo o nuevo) puede heredar
ni adivinar el home de Douglas — ni por variable de entorno global ni por
ruta conocida. Un `Hermes.exe` viejo, al no encontrar nada en
`%LOCALAPPDATA%\douglas` (renombrado), simplemente crea su propio
directorio nuevo ahí, aislado, sin colisionar con los datos reales de
Douglas.

**Verificación**: 20/20 tests de `tests-douglas/test_compat_home.py` (3
pruebas de migración nuevas). `tsc`/`cargo check` limpios. Verificación
en vivo, la más importante: se invocó la función de migración directamente
contra el directorio real **mientras Douglas Agent.exe seguía corriendo**
(locks reales sobre `gateway.lock`, `auth.lock`, `state.db-wal`) — el
rename falló de forma segura (`OSError` capturado, sin crash), el
directorio viejo quedó 100% intacto. Confirma que la migración real (que
ocurrirá sola, automáticamente, la próxima vez que el usuario actualice y
reabra la app) se degrada de forma segura ante contención de archivos, y
se reintentará en el siguiente arranque sin la app abierta.

**Commits**: `fa9ab47fc`.

---

## 2026-08-06 — Regresión: el wordmark "DOUGLAS AGENT" + logo desaparecieron de la pantalla de nueva sesión

**Problema**: el usuario reportó (con captura) que la pantalla de nueva
sesión ya no mostraba el logo ni el wordmark "DOUGLAS AGENT" — solo el
fondo y la fila de íconos sociales. Esto ya se había implementado antes
(ver entrada del 2026-08-05, iniciativa 1) y funcionaba.

**Causa raíz**: regresión introducida por el propio cambio de esta sesión
que agregó el fondo del chat con imagen + tinte
(`apps/desktop/src/components/assistant-ui/thread/list.tsx`). Las dos
capas nuevas son `position: absolute` sin `z-index`. Por las reglas de
apilamiento de CSS2.1, un elemento posicionado con `z-index: auto` se
pinta *después* (encima) del contenido no-posicionado del mismo contexto
de apilamiento, sin importar el orden en el DOM — así que el tinte
translúcido terminaba pintándose arriba del componente `Intro` (logo +
wordmark), que nunca tuvo `position` propio. El wordmark usa
`text-emerald-600`/`emerald-400` sobre un tinte también verde oscuro, lo
que además hacía el efecto casi imperceptible incluso donde sí se veía
algo.

**Qué se hizo**: `-z-10` en ambas capas de fondo, devolviéndolas a la
etapa de apilamiento anterior al contenido en flujo normal — sin tocar el
contenedor de contenido ni ningún otro componente.

**Verificación**: 15/15 tests de `list.test.ts` pasan, `tsc` limpio. No
fue posible tomar una captura real de la app (limitación conocida del
panel de navegador de esta sesión, y la pantalla real requiere el IPC
bridge completo de Electron, no solo el servidor de desarrollo del
renderer). Se publicó una reproducción visual del mecanismo exacto
(mismos colores del tema Douglas Noir, mismos assets reales) como
artifact, mostrando antes/después del fix lado a lado.

**Commit**: `49933f6fb`.

---

## 2026-08-07 — Módulo Social: auditoría completa + arranque de la integración real de Facebook

### Por qué esta entrada es más larga que las anteriores

El usuario pidió explícitamente consolidar aquí **todo** el estado del
módulo Social — lo que ya documentaba `douglas/CORE_PATCHES.md` disperso
en 3 secciones distintas, más lo que la auditoría de hoy encontró en
código, más el plan de fases hacia adelante — porque dos documentos que
`CORE_PATCHES.md` referencia como fuente de los pasos reales de Meta
(`PROMPT-CAPA-SOCIAL-ETAPA-A.md`, `douglas/PLAN-CAPA-SOCIAL.md`) **no
existen en el repo** (verificado con `find` exhaustivo) — eran
aparentemente prompts de sesión que nunca se guardaron a disco. Esta
entrada + `IMPLEMENTATION_PLAN.md` pasan a ser la única fuente de verdad
viva para este módulo de aquí en adelante.

### Estado exacto encontrado en la auditoría (antes de tocar nada hoy)

**Frontend (`apps/desktop/src/app/social/`) — completo mockeado, "Etapa A,
Bloque 2" en `CORE_PATCHES.md`:**
- `index.tsx` (`SocialView`) — panel con las 6 redes (Facebook, Instagram,
  YouTube, LinkedIn, TikTok, X), botón Connect/Manage/Reconnect por fila.
- `connection-wizard.tsx` — asistente genérico dirigido por datos
  (`WizardStepDefinition[]`), sin backend: `validate()` es un
  `window.setTimeout` que siempre "tiene éxito".
- `approval-card.tsx` — tarjeta de aprobación de publicación, registrada
  como tool-card real para `toolName === 'social_publish'` en
  `message-parts.tsx` — pero **ningún backend emite ese tool call
  todavía**; solo se llega ahí vía el botón "Vista previa" con datos mock.
- `fixtures.ts` — todos los datos simulados (conexiones, pasos del
  wizard, preview de aprobación).
- `home-teaser.tsx` — fila de 6 íconos en el home del chat (post-Etapa A,
  aprobado y documentado aparte en `CORE_PATCHES.md`).
- El gating premium (`premium-gate.tsx`, ver abajo) envuelve tanto el
  panel como el teaser — confirmado consistente entre ambas superficies.

**Backend — no existe para ninguna de las 6 redes.** `plugins/platforms/`
tiene 21 adaptadores reales (WhatsApp, Slack, Telegram, Discord, IRC,
etc.) — cero para Facebook/Instagram/YouTube/TikTok/LinkedIn/X.
`douglas/plugins/` y `douglas/billing/` eran carpetas vacías (solo
`.gitkeep`) — `douglas/plugins/social_auth/`, mencionado en comentarios de
`fixtures.ts` como el destino futuro, nunca se había creado.

**El bloqueo de los botones — mecanismo confirmado, no real todavía:**
```ts
// apps/desktop/src/components/premium-gate.tsx (antes de hoy)
export function isPremiumUser(): boolean {
  return false
}
```
Flag hardcodeado, documentado en su propio comentario como "punto de
decisión mockeado" para que conectar el billing real después sea "un
cambio de un solo archivo". No consulta ningún backend.

**Billing real — existe, pero desconectado de Social.**
`hermes_cli/cli_billing_mixin.py` (1566 líneas) tiene un sistema de
suscripciones/Stripe real y funcional, pero es del **Nous Portal**
(`portal.nousresearch.com`) — el propio `douglas/README.md` ya aclara que
`douglas/billing/` sería un "cliente de pagos propio (Stripe),
**desacoplado del Nous Portal**" — es decir, Nous Portal es un sistema de
NousResearch, no el "Douglas Portal" que el usuario tiene en mente; son
conceptualmente distintos, no solo un rename pendiente. Nous Portal usa
OAuth device-code flow (`hermes_cli/auth.py`) contra un backend real y sí
expone `subscription_tier`/`has_active_subscription` — es la referencia
de patrón a seguir, pero no el sistema a reutilizar directamente.

### La decisión de arquitectura del usuario para este módulo (registrada aquí porque cambia el diseño mockeado original)

El usuario definió explícitamente el modelo de producto, distinto de lo
que el mock actual asumía:

1. **Douglas Agent es software para cualquier usuario del mundo**, de
   cuenta gratis a premium.
2. **Solo las cuentas premium** (con suscripción de Douglas Portal activa)
   tienen acceso al módulo Social — free lo ve bloqueado.
3. **Cada usuario usa sus propias credenciales** (`FACEBOOK_APP_ID`/
   `FACEBOOK_APP_SECRET`, y el equivalente por red) — **nunca** un app de
   Meta centralizada de Douglas. Esto es DISTINTO del wizard mockeado
   actual, cuyos pasos para Facebook (`fixtures.ts`) asumían "Página
   vinculada" + "Permisos" directo, como si Douglas ya tuviera su propia
   app de Meta y el usuario solo autorizara contra ella. El wizard se
   actualiza hoy para pedir primero App ID/App Secret propios del
   usuario (ver más abajo).
4. **Ningún usuario debe tocar un archivo `.env` a mano** — las
   credenciales se ingresan desde el frontend y el backend las persiste
   localmente (mismo patrón ya usado para WhatsApp Cloud/Slack/Telegram:
   `save_env_value()`/`get_env_value()` en `hermes_cli/config.py`,
   escritura atómica a `$HERMES_HOME/.env`, permisos 0600). Las
   credenciales del usuario **nunca salen de su máquina** — no hay
   almacenamiento centralizado de secretos de terceros en ningún backend
   de Douglas.
5. **El gate premium debe estar "blindado"** contra crackeo/modificación
   del binario local. Nota de diseño honesta: ninguna protección puramente
   del lado del cliente es 100% infalible (cualquier app instalada
   localmente puede inspeccionarse/parchearse) — el objetivo realista es
   que la funcionalidad dependa de un **token de entitlement verificable
   criptográficamente** emitido por un backend real de Douglas Portal
   (firmado con una clave privada del servidor; el cliente verifica la
   firma con una clave pública embebida), no solo de un `if` local — así
   un cliente parcheado no puede fabricar un token válido sin comprometer
   el servidor. Esto requiere un backend de Douglas Portal que **hoy no
   existe** (`douglas/billing/` sigue vacío) — es su propia fase, más
   grande que "endurecer un check". Ver fases en
   `IMPLEMENTATION_PLAN.md`.
6. **Por ahora, desbloqueado para pruebas** — decisión explícita y
   temporal del usuario mientras se construye el backend real, pieza por
   pieza, empezando por Facebook.

### Qué se hizo hoy

Ver `IMPLEMENTATION_PLAN.md` para el detalle fase por fase (arquitectura
completa, incluyendo lo pendiente). Resumen de lo que quedó funcionando
al cierre de esta sesión:
- `isPremiumUser()` → `true` temporal, comentado como solo-para-pruebas.
- `douglas/plugins/social_auth/` — módulo nuevo, backend real de
  almacenamiento de credenciales por usuario (Facebook: App ID, App
  Secret, Page ID), reutilizando `save_env_value`/`get_env_value`/
  `remove_env_value` — mismo patrón que WhatsApp Cloud/Slack, nunca
  reinventado.
- `GET`/`PUT /api/social/platforms/{platform_id}` en `hermes_cli/
  web_server.py` — toque mínimo de núcleo (registro de rutas + import),
  deliberadamente separado del registro de plataformas de *mensajería*
  (`PLATFORM_REGISTRY`), porque Social no es un gateway de chat con
  adaptador corriendo — es credenciales + publicación bajo demanda.
- `fixtures.ts` — pasos del wizard de Facebook actualizados: primero App
  ID/App Secret (propios del usuario), luego Page ID, luego el paso de
  autorización (todavía simulado — el OAuth real es la fase siguiente).
- `connection-wizard.tsx` — nuevo prop opcional `onValidateStep`, para
  que pasos específicos llamen al backend real sin romper el
  comportamiento mockeado de las otras 5 redes (que lo siguen usando sin
  ese prop).
- `index.tsx`/`hermes.ts` — conectan el wizard de Facebook al backend real
  para los pasos de credenciales; el paso final de autorización se deja
  claramente marcado como pendiente (Fase 3, OAuth), no se simula como
  "conectado" para no reportar un estado falso.

**Deliberadamente NO hecho hoy** (documentado como próximas fases, no
como olvido): el intercambio OAuth real de Facebook (requiere decidir la
estrategia de `redirect_uri` con el usuario — ver pregunta abierta en
`IMPLEMENTATION_PLAN.md`), el adaptador de publicación real a la Graph
API, el estado de conexión real en el panel (`MOCK_SOCIAL_CONNECTIONS`
sigue siendo estático — falta el `GET` que refleje si Facebook está
realmente configurado), y el backend de entitlement real de Douglas
Portal (el gate sigue siendo un flag hardcodeado, ahora en `true` en vez
de `false`, no un check real).

**Commit**: `34d65da02`.

---

## 2026-08-07 — Fase B2: OAuth real de Facebook (servidor loopback local)

**Decisión del usuario**: servidor loopback local (no el truco de pegar
URL manual que usa `plugins/platforms/google_chat/oauth.py`). Se investigó
el precedente ya existente en el repo antes de escribir código —
`hermes_cli/auth.py` ya tiene un flujo de OAuth loopback completo y
probado para Spotify (`_spotify_wait_for_callback`,
`_make_spotify_callback_handler`, `_can_open_graphical_browser`,
`_is_remote_session`) — se siguió ese mismo patrón para Facebook en vez de
inventar uno nuevo, con una diferencia clave documentada abajo.

**Qué se hizo**: `hermes_cli/social_oauth.py` (archivo nuevo). Flujo:

1. `start_facebook_oauth()` — valida que las credenciales de la Fase B1
   estén guardadas, genera un `state` (CSRF), arranca un hilo en segundo
   plano que levanta el servidor loopback y espera el callback, abre el
   navegador del sistema con la URL de autorización de Meta
   (`webbrowser.open()`, nunca un webview embebido — la sesión/2FA/passkey
   real del usuario vive en su navegador, la app nunca debe ver la
   contraseña), y **retorna inmediatamente** (no bloquea la petición HTTP).
2. El hilo en segundo plano espera el callback (mismo patrón de polling
   con deadline que el de Spotify), valida `state`, y si hay código,
   ejecuta el intercambio de 3 pasos que exige la Graph API de Meta:
   código → token de usuario de corta duración → token de usuario de larga
   duración (`fb_exchange_token`) → Page Access Token (que, al derivarse de
   un token de usuario de larga duración, no expira solo — solo si el
   usuario revoca el acceso o cambia su contraseña). Se guarda con el mismo
   `save_env_value` de siempre (`FACEBOOK_PAGE_ACCESS_TOKEN`).
3. El frontend consulta `get_facebook_oauth_status(state)` — el wizard
   (`index.tsx`) hace polling cada 1.5s hasta `success`/`error`/timeout.

**Diferencia clave vs. el patrón de Spotify**: Spotify usa un puerto
efímero asignado por el SO (`port=0`) porque su propio flujo PKCE no
depende de un `redirect_uri` pre-registrado exacto. **Facebook sí** — el
allowlist de "Valid OAuth Redirect URIs" de Meta exige coincidencia exacta
de string, puerto incluido, sin comodines. Un puerto aleatorio en cada
intento habría obligado a re-registrar la URL en el dashboard de Meta cada
vez — inviable. Se usa un puerto **fijo** (`53682`) que el usuario agrega
UNA sola vez a su app de Meta (`http://localhost:53682/facebook/callback`)
— mismo tipo de configuración de una sola vez que ya pide el wizard de
WhatsApp Cloud para su webhook. Documentado directamente en el primer paso
del wizard (`fixtures.ts`), no solo en código.

**Prerrequisito real que el usuario debe cumplir en Meta for Developers**
(no controlable desde el código): los permisos `pages_manage_posts`/
`pages_read_engagement`/`pages_show_list` solo funcionan sin fricción para
los propios admins/testers de la app de Meta. Para que CUALQUIER usuario
final autorice (no solo el dueño de la app), Meta exige pasar App Review
— esto aplica a cada usuario que traiga su propia app, no es algo que
Douglas pueda resolver una sola vez de forma centralizada, precisamente
porque cada quien tiene su propia app.

**Riesgo de seguridad considerado**: el intercambio usa `state` como
protección CSRF (comparado exacto contra lo que generó
`start_facebook_oauth()`); el App Secret nunca viaja en la URL de
autorización (confirmado con test dedicado); el registro de intentos en
memoria (`_ATTEMPTS`) nunca toca disco y se pierde al reiniciar la app —
no hay nada persistente que limpiar.

**Verificado**: `tests/hermes_cli/test_social_oauth.py`, 15 tests nuevos
— validación de credenciales, generación de `state`, el intercambio de 3
pasos con sus 3 rutas de error (código inválido, red caída, Page sin
token — este último cubre el caso real de "el usuario no es admin de esa
página"), y las rutas HTTP (`POST`/`GET` con credenciales faltantes,
estado desconocido, arranque exitoso) — todo sin abrir un navegador real
ni tocar la red real (`webbrowser.open`/`httpx.get`/el hilo del servidor
mockeados). `tsc --noEmit` y `eslint` limpios en el frontend.

**Pendiente (Fase B3)**: el adaptador que realmente publica en la Graph
API usando el `FACEBOOK_PAGE_ACCESS_TOKEN` guardado aquí, y conectar
`social_publish` como tool call real. Ver `IMPLEMENTATION_PLAN.md`.

**Commit**: `9963f112a`.

---

## 2026-08-07 — Banner de actualización en el sidebar + Gateway siempre visible

**Contexto**: antes de que el usuario actualizara manualmente para recibir
todo el trabajo de hoy (Social Fase B1/B2), pidió dos cambios adicionales
en la UI, verificados contra capturas reales de la app corriendo:

**1. Banner "Reiniciar para actualizar" en el sidebar del home.** Hasta
ahora la única forma de aplicar una actualización era abrir Settings >
About (`about-settings.tsx`, sin tocar) o esperar el toast de notificación
(`store/updates.ts::maybeNotifyUpdateAvailable`, también sin tocar) — la
mayoría de usuarios no abre Settings por su cuenta. Nuevo componente
`apps/desktop/src/app/chat/sidebar/update-banner.tsx`
(`SidebarUpdateBanner`), insertado en `chat/sidebar/index.tsx` justo debajo
de la lista de navegación (`SIDEBAR_NAV`). Reutiliza exactamente el mismo
estado que ya usa About (`$updateStatus`/`$updateApply`/
`startActiveUpdate()`) — nunca se inventó un mecanismo de update paralelo,
así que las dos superficies nunca pueden desincronizarse. Solo se renderiza
cuando `behind > 0 && supported && !applying` (misma condición exacta que
el botón "Update now" de About). Logo: `logo_white.png` en modo oscuro,
`logo_black.png` en modo claro, elegido por `renderedMode` (lo que
realmente se pinta en pantalla, no la preferencia cruda del usuario) — ver
`themes/context.tsx`. Número de versión: `$desktopVersion.appVersion` (la
versión actual en ejecución — el sistema de updates de este repo es
git-commit-based, "N commits behind", no semver clásico con una "versión
nueva" propia que mostrar).

**2. El indicador "Gateway" de la barra de estado ahora es imposible de
ocultar por accidente.** El usuario reportó que ya no se mostraba. Investigado:
el item `gateway-health` (`use-statusbar-items.tsx`) siempre estuvo en la
lista de items — nunca tuvo `hidden` condicional — pero SÍ es
toggleable por el usuario vía el menú de personalización de la barra de
estado (`statusbar-controls.tsx`, checkbox que oculta cualquier item sin
`lockedVisible: true`). Es decir, no fue un bug de código nuevo: la
funcionalidad de ocultar items ya existía y este item nunca estuvo
protegido contra ella, a diferencia de `command-center`. Se agregó
`lockedVisible: true` a `gateway-health` — mismo tratamiento que
`command-center` — para que el estado de conexión (si el agente está
vivo o no) nunca pueda desaparecer de la barra, sea que se ocultó por
accidente o a propósito.

**Verificado**: `tsc --noEmit` limpio (dos corridas independientes, sin
errores). `eslint` sin errores nuevos (los 6 warnings que aparecen en
`use-statusbar-items.tsx` son preexistentes, en líneas lejos de este
cambio — confirmado). `statusbar-visibility.test.tsx` 7/7 (corrido con
`--pool=threads` porque el pool `forks` por defecto sufrió timeout de
worker por la carga del sistema en ese momento — muchos procesos Node
concurrentes de las verificaciones de esta sesión). Consola del renderer
sin excepciones nuevas.

**Commit**: `d09c76dc8`.

---

## 2026-08-07 — El agente seguía autodescribiéndose como "la app Hermes" en el system prompt (no la identidad, el entorno)

**Problema real, reportado con evidencia**: el usuario le preguntó al agente
"¿quién eres? ¿para qué son los botones de rrss?" en una sesión nueva del
Douglas Agent real. Respondió correctamente "Soy Douglas Agent... por
DouglasDevSec" (la identidad ya estaba bien, arreglada en una sesión
anterior — ver entrada "Identidad del agente en chat" en
`CORE_PATCHES.md`), pero la segunda frase preguntó "¿Los ves en la
interfaz de la app **Hermes**...?" — una marca distinta apareciendo en la
misma respuesta.

**Investigación** (se descartaron hipótesis antes de tocar código):
- ¿`AGENTS.md` (el contributor doc, lleno de "Hermes Agent" a propósito)
  se estaba inyectando como contexto de proyecto? Se verificó
  `projects.db` de la instalación real — vacío, sin proyecto configurado.
  Descartado.
- ¿El cwd por defecto de una sesión nueva resuelve al árbol de
  instalación? Se revisó `resolveHermesCwd()` (`main.ts`) — ya evita
  explícitamente eso en un build empaquetado, cae a `app.getPath('home')`.
  Descartado.
- **Causa real, encontrada por grep dirigido en `agent/system_prompt.py` y
  `agent/prompt_builder.py`**: varios bloques de texto inyectados
  literalmente en el system prompt de **cada sesión** seguían diciendo
  "Hermes" — no comentarios de desarrollador, sino prosa que el modelo
  recibe tal cual. El más directo: la pista de plataforma `"desktop"` en
  `PLATFORM_HINTS` decía textualmente *"You are chatting inside the
  **Hermes desktop app**..."* — es decir, se le decía al modelo, en cada
  sesión de escritorio, que estaba dentro de "la app Hermes". Esto explica
  la respuesta observada de forma directa, no como alucinación del modelo.

**Qué se corrigió** (`agent/prompt_builder.py`, `agent/system_prompt.py`):
- `PLATFORM_HINTS["desktop"]`: "Hermes desktop app" → "Douglas Agent
  desktop app".
- `PLATFORM_HINTS["tui"]`: "Hermes terminal UI (TUI)" → "Douglas terminal
  UI (TUI)".
- `PLATFORM_HINTS["webui"]`: "Hermes WebUI" → "Douglas WebUI".
- Nota de steering mid-turn (`STEER_CHANNEL_NOTE`): "que Hermes appends" →
  "que Douglas appends".
- Nota de modo YOLO en la guía de `computer_use`: "when Hermes has none;
  explicit Hermes YOLO" → "Douglas"/"Douglas YOLO".
- Bloque de backend remoto (sandboxes): "NOT on the machine where Hermes
  itself is running... of the Hermes process" → "Douglas" x2 (dos
  variantes, con y sin probe de backend).
- Guía de skills: "troubleshoot Hermes Agent itself" → "troubleshoot
  Douglas Agent itself" — se dejó intacto el identificador real de la
  skill (`hermes-agent`, entre backticks) porque renombrar el archivo/id
  de la skill es un cambio de alcance distinto, no de texto.
- `system_prompt.py`: "Active Hermes profile: default" / "Active Hermes
  profile: {active_profile}" → "Active Douglas profile" — este es el
  bloque de perfil activo, inyectado en **toda** sesión (no solo
  desktop), así que también contribuía.

**Deliberadamente NO tocado**: comentarios de desarrollador (`# ... Hermes
install tree ...`), mensajes de `logger.warning(...)` (diagnóstico
interno, nunca llega al usuario ni al modelo), y referencias a "Hermes"
en tests que describen comportamiento histórico real (p. ej.
`test_dashboard_tui_backcompat.py`: "Older Hermes desktop app shells (<=
0.15.x)" — describe versiones que sí se llamaban Hermes) o sistemas
externos ajenos (`test_tini_compat_shim.py`: el catálogo "Hermes WebUI"
de Hostinger, un producto de terceros sin relación).

**Verificado**: `tests/agent/test_system_prompt.py` (19/20 — la única
falla es la ya documentada `test_coding_prompt_preserves_legacy_workspace_order`,
separador `/` vs `\` de Windows, preexistente, no causada por este
cambio), `tests/tools/test_cross_profile_guard.py` (10/10),
`tests/agent/test_platform_hint_desktop.py` (15/15) — los tres archivos
con aserciones sobre el texto exacto que cambié, actualizados en el mismo
commit. `tests/agent/` completo con filtro `prompt or platform_hint`:
191 pasan, 2 fallan — ambas las mismas dos fallas preexistentes ya
documentadas en la entrada "Identidad del agente en chat" de
`CORE_PATCHES.md` (fuga de estado entre tests vía contextvar, y el mismo
separador de ruta de Windows), confirmadas de nuevo con `git stash` antes
de esta sesión.

**Commit**: `203700ce9`.

---

## 2026-08-07 — El fix anterior no alcanzó: guard de identidad ampliado + reposición del botón de actualización

**El usuario probó de nuevo tras actualizar y "Hermes" seguía apareciendo**
— pero con una redacción distinta a la primera vez ("¿En la app Hermes,
en una web, en algún documento?" vs. la original "¿Los ves en la
interfaz de la app Hermes, en alguna página web, o en otro contexto?").
Esa diferencia de redacción es la pista clave: no es el mismo texto
repetido (no es un string cacheado verbatim) — es el modelo generando
una respuesta fresca cada vez y, aun así, llegando a "Hermes" como
adivinanza.

**Verificación antes de asumir que el fix anterior falló**: se confirmó
que el checkout real de la instalación del usuario
(`%LOCALAPPDATA%\douglas\hermes-agent`) está exactamente en el commit
`203700ce9` — el fix anterior sí llegó a disco. Se confirmó además que
`agent.prompt_builder.PLATFORM_HINTS['desktop']` ya no contiene la
palabra "Hermes" en absoluto (`'Hermes' in ... == False`, verificado en
vivo). Es decir: el texto que se corrigió la vez pasada genuinamente
ya no existe. El problema no era ese fix — era que **el guard de
identidad existente solo cubría preguntas directas** ("¿quién eres?"),
no esta clase de especulación indirecta (el modelo ofreciendo "Hermes"
como una de varias opciones dentro de una pregunta aclaratoria, cuando
no tiene contexto real de a qué se refiere el usuario).

**Qué se hizo**: se amplió la cláusula anti-extracción en los 3 lugares
donde vive (`DEFAULT_AGENT_IDENTITY` en `agent/prompt_builder.py`,
`DEFAULT_SOUL_MD` en `hermes_cli/default_soul.py`, `docker/SOUL.md`) para
cubrir explícitamente este caso: "cuando no sabes un detalle de la UI,
una función, o dónde el usuario está viendo algo — referite a la interfaz
SOLO como Douglas Agent. Nunca ofrezcas otro nombre de producto —
incluyendo 'Hermes' o 'Hermes Agent' — como adivinanza ni como una opción
entre varias, incluso dentro de una pregunta aclaratoria hecha porque te
falta contexto para responder."

**Verificado antes de aplicar** (lección ya aprendida en una sesión
anterior — ver "Blindaje anti-extracción" en `CORE_PATCHES.md`): se
corrió el propio escáner anti-inyección del repo
(`tools/threat_patterns.py::scan_for_threats`) contra el texto nuevo, en
ambos scopes (`all` y `strict`) — sin coincidencias, no se repite el
incidente donde una cláusula defensiva sonó como el propio ataque que
bloquea.

**Mecanismo de actualización para instalaciones reales**: la instalación
real del usuario ya tiene un `SOUL.md` sembrado en disco que coincide
byte a byte con el `DEFAULT_SOUL_MD` *anterior* (el de alcance angosto).
Se capturó ese texto exacto como `_NARROW_ANTI_EXTRACTION_SOUL_MD` y se
agregó a `_LEGACY_TEMPLATE_SOULS` — el mismo mecanismo de auto-upgrade ya
usado para el rebrand original (`_ensure_default_soul_md()`,
`hermes_cli/config.py`) lo reemplazará por el texto ampliado
automáticamente en el próximo arranque del backend, sin ningún paso
manual del usuario.

**Nota importante para la próxima prueba**: dado que el system prompt de
una sesión se cachea (`agent._cached_system_prompt`, "for the lifetime of
the AIAgent", con lógica de restauración al reanudar sesiones —
`agent/system_prompt.py::reconstruct_static_prefix()`), es posible que
una sesión de chat YA EXISTENTE (creada antes de este fix) conserve un
system prompt viejo cacheado. **Recomendado probar en una sesión
completamente nueva** ("New session"), no continuando una sesión
anterior, para que el resultado refleje el fix real.

**De paso**: el botón "Reiniciar para actualizar" (agregado en la entrada
anterior) se reposicionó a pedido del usuario — de justo debajo de la
navegación a justo arriba de `ProfileRail` (el pie de la barra lateral
con home/+/Manage).

**Verificado**: `tests/agent/test_prompt_builder.py` (55/55),
`tests/agent/test_system_prompt.py`/`test_platform_hint_desktop.py`,
`tests/tools/test_cross_profile_guard.py`, `tests/hermes_cli/test_config.py`
— 161 pasan, 3 fallan (las mismas 3 fallas preexistentes ya documentadas:
separador de ruta de Windows, fuga de contextvar entre tests, y
`HERMES_HOME` fijado en esta máquina real). `tsc`/`eslint` limpios en el
banner reposicionado.

**Commit**: `18110d9b1`.

---

## 2026-08-07 — El fix de identidad funcionó (probado en sesión nueva), pero el agente no sabía explicar el panel Social real

**Buena noticia primero**: el usuario probó en una sesión genuinamente
nueva ("Presentación y botones de...") y "¿quién eres?" ya NO mencionó
Hermes — el guard ampliado de la entrada anterior funcionó.

**Problema nuevo, distinto**: al preguntar específicamente por "el botón
lateral Social", el agente respondió que ese panel **no existe** en la
UI base de Douglas, y especuló con adivinanzas — un plugin/extensión
instalado, un tema que inyecta botones, u otra app que envuelve a
Douglas (mencionó "Franz, Rambox, Wavebox" como ejemplos). El agente no
tenía ningún conocimiento real del módulo Social construido en esta
misma sesión (Fases A/B1/B2) — nada en su system prompt lo describe, así
que ante la pregunta, adivinó en vez de decir la verdad.

**Qué se hizo**: se agregó una descripción concisa y precisa del panel
Social real al hint de plataforma `PLATFORM_HINTS["desktop"]`
(`agent/prompt_builder.py`) — siempre inyectado en toda sesión de
escritorio (no depende de que el modelo decida cargar una skill): qué es
(panel en la barra lateral para conectar Facebook/Instagram/YouTube/
LinkedIn/TikTok/X), qué tan real es cada red HOY (solo Facebook funciona
de verdad), y los pasos exactos para conectar Facebook (App ID/Secret
propios del usuario, Page ID, autorización en el navegador). Termina con
una instrucción explícita: "no adivines con plugins, extensiones, temas,
u otras apps" — apunta directo al patrón de falla observado.

**Decisión de diseño**: se puso en el hint de plataforma (siempre
inyectado) en vez de una skill cargada bajo demanda — a pesar de que
`fixtures.ts` (comentarios de Etapa A) ya mencionaba una futura skill
`social-connect`. Se prefirió el hint porque es 100% confiable (no
depende de que el modelo decida que la pregunta amerita cargar una
skill) — coincide con lo que el usuario pidió explícitamente
("blindado", "la respuesta siempre sea correcta"). Trade-off consciente:
infla un poco el system prompt de cada sesión de escritorio a cambio de
esa garantía.

**⚠️ Nota de mantenimiento — este texto se desactualiza si el módulo
Social avanza sin actualizarlo también**: cuando se complete la Fase B3
(adaptador de publicación real) o la Fase C (YouTube), o cuando el gate
premium deje de estar desbloqueado para pruebas, este bloque en
`PLATFORM_HINTS["desktop"]` debe actualizarse en el mismo cambio — si
no, el agente empezará a darle a los usuarios información desactualizada
sobre su propio producto, el mismo tipo de problema que motivó esta
entrada.

**Verificado**: `tools/threat_patterns.py::scan_for_threats` limpio (both
scopes) contra el texto nuevo. `tests/agent/test_platform_hint_desktop.py`
+ `tests/agent/test_prompt_builder.py`: 70/70 pasan (1 skip preexistente).

**Commit**: `26aaccf31`.

---

## 2026-08-07 — "Messaging platforms failed to load" al abrir Messaging poco después de iniciar la app

**No es un tema de Social/OAuth** — el usuario estaba probando el panel
de Messaging (Telegram) para comparar comportamiento, y encontró dos
problemas separados:

**1. Timeout real, causa identificada — clase de bug ya conocida (#48504).**
El mensaje "Timed out connecting to Douglas Agent backend after 15000ms"
viene de `getMessagingPlatforms()` (`apps/desktop/src/hermes.ts`), que no
tenía el timeout generoso (`STARTUP_REQUEST_TIMEOUT_MS`, 60s) que ya se
le dio a otras llamadas de arranque (`/api/model/info`, etc.) — usaba el
default corto (`DEFAULT_FETCH_TIMEOUT_MS`, 15s, `hardening.ts`). El
comentario ya existente junto a esas otras llamadas explica exactamente
este patrón: la ráfaga de llamadas de arranque puede tardar más de 15s
en un backend "vivo pero ocupado" (recién iniciado, todavía terminando
su propio arranque), y eso se veía como un "failed to load" espurio. Se
agregó `timeoutMs: STARTUP_REQUEST_TIMEOUT_MS` a `getMessagingPlatforms()`,
mismo patrón exacto que las otras 7 llamadas que ya lo tienen.

**2. "Failed to save Telegram" — no es un bug, es la validación
funcionando correctamente.** El usuario puso `@DouglasDev27` (su
@username de Telegram) en el campo "Allowed Telegram user IDs", pero ese
campo exige **IDs numéricos** obtenidos de `@userinfobot` (el propio
texto de la UI ya lo dice: "Comma-separated numeric IDs from
@userinfobot"). Se le explicó cómo obtener el ID numérico real.

**Verificado**: `tsc --noEmit`/`eslint` limpios (sandbox sincronizado).
Sin tests dedicados a este timeout específico — cambio de una línea,
mismo patrón ya cubierto implícitamente por el resto de llamadas con
`STARTUP_REQUEST_TIMEOUT_MS`.

**Commit**: `eae245843`.

---

## 2026-08-07 — Rebrand del catálogo de plataformas de mensajería + Telegram "Connected" pero no responde

**Rebrand**: las 23 descripciones de plataformas de mensajería en
`hermes_cli/web_server.py::_PLATFORM_OVERRIDES` decían "Hermes" (ej.
"Run Hermes from Telegram DMs, groups, and topics.", visible tal cual en
el panel Messaging del usuario) — corregidas todas a "Douglas Agent". No
se tocaron las `docs_url` (siguen apuntando a
`hermes-agent.nousresearch.com`, atribución correcta a Nous Research
por licencia MIT) ni las 2 entradas de temas/skins "Hermes Teal" en otra
parte del archivo (fuera de alcance — son nombres de esquema de color,
no descripciones de mensajería; quedan anotadas para una pasada
separada si el usuario la pide).

**Telegram real, diagnosticado con logs reales, no especulación**: el
usuario conectó Telegram, la UI mostró "Connected", envió 3 mensajes de
prueba (confirmados entregados/leídos por Telegram — doble check) y el
bot nunca respondió. Se revisó `gateway_state.json` (gateway corriendo,
`platforms.telegram.state: "connected"`) y `logs/agent.log`/`errors.log`
con timestamps reales:

1. `19:14:53` — se guarda `TELEGRAM_BOT_TOKEN` (primer intento, el de
   `@DouglasDev27` como allowed user fue rechazado por la validación,
   documentado en la entrada anterior).
2. `19:34:42` — el gateway (proceso separado, PID propio) arranca y se
   conecta a Telegram. En ese instante loguea *"No env user allowlists
   configured... will deny unknown senders"* — confirma que en el
   momento de conectar, el proceso del gateway todavía no veía ningún
   `TELEGRAM_ALLOWED_USERS`.
3. `19:35:00` — "[Telegram] Connected to Telegram (polling mode)" — el
   bot ya está vivo y sondeando, pero con política deny-por-defecto (sin
   allowlist).
4. `19:35:34` — *después* de que el gateway ya estaba conectado, se
   guarda `TELEGRAM_ALLOWED_USERS` (el ID numérico correcto) vía el
   panel Messaging.

**Causa raíz confirmada en código**: `save_env_value()`
(`hermes_cli/config.py`) sí actualiza `os.environ` — pero del **proceso
que atiende la petición HTTP** (el dashboard/API), no del proceso del
gateway (PID separado, `gateway_state.json` lo confirma). Los procesos
de SO no comparten variables de entorno entre sí después de arrancar —
el gateway ya había leído (y logueado) su política de allowlist al
conectar, y esa lectura fue **una sola vez al inicio**
(`gateway/run.py`, línea ~10436: `os.getenv(v)` dentro del bloque de
arranque del gateway, no en el loop de manejo de mensajes). Guardar
credenciales nuevas actualiza el archivo `.env` en disco, pero el
gateway ya en marcha no lo vuelve a leer solo — necesita reiniciarse.

**Cómo se soluciona**: el propio flujo de guardado ya lo anticipa —
`apps/desktop/src/app/messaging/index.tsx::handleSave()` muestra un
toast de éxito con un botón de acción "reiniciar" (`m.restartToReconnect`
+ `restartGatewayAction`), pero requiere que el usuario lo pulse
explícitamente; si se pierde o se descarta el toast, queda en este
estado silenciosamente roto. Indicado al usuario: click en el indicador
"Gateway" de la barra de estado (ahora siempre visible, ver entrada del
2026-08-07 "El fix anterior no alcanzó") → "Restart Gateway"
(`gateway-menu-panel.tsx`, `runGatewayRestart()`).

**Posible mejora de producto, no implementada, solo señalada**: auto-
reiniciar el gateway automáticamente al guardar credenciales de
mensajería (en vez de depender del toast/botón) resolvería esta clase de
problema de raíz, pero interrumpiría cualquier turno de agente en curso
en ese momento — trade-off real, no se decidió unilateralmente.

**Commit**: `5aad5da8c`.

---

## 2026-08-07 — CORRECCIÓN: dos afirmaciones mías eran falsas (barra de estado, icono de barra de tareas)

El usuario señaló, con razón, que le he dicho que cosas funcionan sin
haberlas verificado en la app real — sólo verifiqué que el código
compila. Esta entrada corrige el registro.

### ❌ FALSO: "el indicador Gateway ahora siempre se ve"

Afirmado en la entrada del 2026-08-07 ("Banner de actualización en el
sidebar + Gateway siempre visible") y repetido después. **Es incorrecto.**
`apps/desktop/src/store/statusbar-prefs.ts:10`:

```ts
export const $statusbarVisible = persistentAtom(STATUSBAR_VISIBLE_STORAGE_KEY, false, Codecs.bool)
```

La barra de estado **completa está desactivada por defecto** (opt-in por
diseño, comentado en ese mismo archivo: "Off by default — the bar is
opt-in"). Mi cambio (`lockedVisible: true` en el ítem `gateway-health`)
sólo impide ocultar ese ítem **dentro de una barra ya visible** — no hace
nada si la barra entera está oculta, que es el estado por defecto de
cualquier instalación nueva. Razoné sobre la capa equivocada.

Cómo se muestra realmente: `Ctrl+Shift+S` (`view.toggleStatusbar`,
`apps/desktop/src/lib/keybinds/actions.ts:116`). Para reiniciar el
gateway sin la barra: `Ctrl+K` → "Restart gateway"
(`command-palette/index.tsx:871`).

### ❌ FALSO: "era caché de iconos de Windows" (icono de barra de tareas)

Diagnóstico anterior (entrada del 2026-08-06, marcado como "Resuelto" en
`IMPLEMENTATION_PLAN.md`): se concluyó que era caché de iconos del shell
porque el `.exe` tenía el icono correcto embebido. **El icono nunca
apareció**, tras múltiples reinicios y actualizaciones — así que ese
diagnóstico era erróneo o incompleto.

**Investigación real de esta ronda** (todo verificado contra la
instalación en vivo, no contra el repo):
- El `.exe` en ejecución (`release/win-unpacked/Douglas Agent.exe`, PID
  real confirmado con `Get-Process`) SÍ tiene el icono verde correcto
  embebido — extraído con `ExtractAssociatedIcon` e inspeccionado
  visualmente. ✓
- `resources/icon.ico` y `assets/icon.ico` existen ambos, así que
  `getAppIconPath()` (`main.ts:810`) sí resuelve a un archivo real. ✓
- El acceso directo del Start Menu apunta al exe correcto con
  `IconLocation` correcto. ✓
- **PERO**: la app llama `app.setAppUserModelId("com.douglasdevsec.douglas-agent")`
  (confirmado en el bundle compilado `dist/electron-main.mjs`), y
  **ningún acceso directo lleva ese AUMID grabado** (verificado leyendo
  el `.lnk` vía `IPropertyStore`, `System.AppUserModel.ID` → vacío).

Windows exige que exista un acceso directo del Start Menu con el
`System.AppUserModel.ID` coincidente para resolver icono/agrupación de la
barra de tareas cuando una app declara un AUMID propio. La causa es
`scripts/install.ps1:3284`, que crea el acceso directo con
`WScript.Shell.CreateShortcut` — esa API COM **no puede** escribir el
AUMID (sólo campos básicos: TargetPath, IconLocation, Arguments...).
Requiere `IPropertyStore`.

**Intento de parche en caliente FALLIDO**: se intentó estampar el AUMID
en el `.lnk` existente con C# inline (`IShellLinkW` + `IPropertyStore`).
El archivo creció de 2708 a 2829 bytes, pero al releerlo el valor sigue
vacío (`vt=0`) — el marshalling del `PROPVARIANT` en el helper inline es
incorrecto. **No dar por resuelto**: la causa raíz está identificada y
verificada, la corrección no.

**Camino correcto pendiente** (no implementado en esta ronda): Electron
expone `shell.writeShortcutLink(path, op, { appUserModelId })`, que sí
graba la propiedad correctamente. Lo más robusto es que la app repare su
propio acceso directo al arrancar en Windows (auto-heal), en vez de
depender de que el instalador PowerShell lo haga — así también arregla
las instalaciones ya existentes sin reinstalar.

### Lección de proceso

`tsc` limpio, `eslint` limpio y tests en verde **no son evidencia de que
una función se vea o funcione en la app real**. Para cualquier cambio
observable por el usuario: verificar contra la instalación real (proceso
en ejecución, archivos en disco, logs del backend) o decir explícitamente
que no se pudo verificar — nunca afirmar que funciona.

**Commit**: pendiente al momento de escribir esta entrada.
