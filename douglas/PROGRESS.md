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
