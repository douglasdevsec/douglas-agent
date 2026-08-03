# CORE_PATCHES.md — Registro de toques al núcleo de Hermes

Cada vez que un cambio de Douglas Agent toca un archivo fuera de `douglas/`
(fuera de la capa de producto), se anota aquí. El objetivo es poder revisar
de un vistazo toda la superficie de fricción con `upstream/main` antes de
cada intento de `git merge upstream/main`.

Formato por entrada:

```
## <ruta del archivo>
- **Motivo**: por qué fue necesario tocar el núcleo en vez de extenderlo
  desde douglas/.
- **Alternativa descartada**: qué otra forma se consideró (plugin, hook,
  wrapper) y por qué no alcanzaba.
- **Commit**: hash del commit que lo introdujo.
```

## hermes_bootstrap.py

- **Qué:** añade `normalize_douglas_env()` (y sus helpers
  `_douglas_home_candidates()` / `_resolve_default_douglas_home()`),
  llamada como la primera línea del bloque de import-time del módulo.
  Copia `DOUGLAS_<X>` → `HERMES_<X>` en `os.environ` para toda variable
  (ganando sobre una `HERMES_<X>` ya presente), y si `HERMES_HOME` sigue
  sin definir tras eso, resuelve el directorio por defecto según la cadena
  documentada en `douglas/README.md`.
- **Por qué:** es el único módulo importado primero por *todos* los entry
  points Python (`hermes`, `hermes-agent`, `hermes-acp`,
  `python -m gateway.run`, `batch_runner.py`, `cron/scheduler.py` — según
  su propio docstring), así que normalizar aquí cubre los 284 llamadores de
  `get_hermes_home()` y los ~35 sitios con fallback hardcodeado sin tocar
  ninguno de ellos — todos leen `HERMES_HOME` de `os.environ`.
- **Alternativa descartada:** (a) wrapper de shell externo — no cubre el
  desktop (Electron spawnea Python directamente, sin pasar por ningún
  wrapper) ni instalaciones vía `python -m gateway.run` directo; (b)
  `douglas/compat.py` importado desde `hermes_constants.py` — invierte la
  dirección de dependencia núcleo→capa de producto, y falla si `douglas/`
  no está en el PYTHONPATH (instalación como paquete, Docker, tests
  aislados con `sys.path` recortado).
- **Riesgo de merge:** bajo — función nueva, ~75 líneas, no modifica
  ninguna función ni línea existente del archivo, solo antepone una
  llamada nueva al bloque de efectos de import ya existente.
- **Commit:** `feat(compat): add Douglas/Hermes home and env resolution`

## apps/desktop/electron/main.ts

- **Qué:** `resolveHermesHome()` gana una rama nueva antes de cada paso
  existente: `DOUGLAS_HOME` (env), lectura de registro de
  `DOUGLAS_HOME` en Windows, y comprobación de existencia de
  `%LOCALAPPDATA%\douglas` / `~/.douglas` antes de caer en la lógica
  original de Hermes (que queda sin modificar).
- **Por qué:** el desktop no arranca desde el CLI — calcula la ruta en
  TypeScript y se la pasa explícita al proceso Python hijo al spawnearlo
  (`HERMES_HOME` pineada, ver comentario "Explicitly pin HERMES_HOME for
  the child" más abajo en el mismo archivo). Sin este espejo, el desktop
  seguiría resolviendo `~/.hermes`/`%LOCALAPPDATA%\hermes` sin saber que
  `~/.douglas`/`%LOCALAPPDATA%\douglas` existe.
- **Alternativa descartada:** ninguna — es la única forma de cubrir este
  componente, dado que no ejecuta ningún código Python antes de decidir
  la ruta.
- **Riesgo de merge:** bajo-medio — la función original queda intacta
  como fallback exacto (mismas ramas, mismo orden), solo se antepone la
  capa Douglas encima. `readWindowsUserEnvVar()` y `normalizeHermesHomeRoot()`
  ya eran genéricas por parámetro — no requirieron cambios.
- **Commit:** `feat(compat): add Douglas/Hermes home and env resolution`

## apps/bootstrap-installer/src-tauri/src/paths.rs

- **Qué:** `hermes_home()` gana la misma rama `DOUGLAS_HOME`/existencia de
  directorio douglas-nombrado antes de la lógica Hermes original (intacta
  como fallback).
- **Por qué:** el instalador nativo corre *antes* de que exista Python o
  el propio checkout de Hermes — es la tercera pieza que debe conocer la
  cadena Douglas de forma independiente, ya documentada en este archivo
  como "Mirrors hermes_constants.get_hermes_home()" antes de este cambio.
- **Alternativa descartada:** ninguna — mismo razonamiento que `main.ts`.
- **Riesgo de merge:** bajo — misma forma que el cambio en `main.ts`,
  función original preservada como fallback.
- **Commit:** `feat(compat): add Douglas/Hermes home and env resolution`

## apps/desktop/electron/main.ts (2/2 — normalización DOUGLAS_DESKTOP_*)

- **Qué:** un bloque nuevo, insertado justo antes de la resolución de
  `HERMES_HOME`, que copia cualquier `DOUGLAS_DESKTOP_<X>` presente a
  `HERMES_DESKTOP_<X>` en `process.env` (ganando sobre un valor ya
  presente). Cubre `HERMES_DESKTOP_REMOTE_URL`, `_REMOTE_TOKEN`,
  `HERMES_DESKTOP_APP_NAME`, y cualquier variable futura con ese
  prefijo, sin tocar los ~7 sitios que ya leen esas variables
  (`main.ts`, `hardening.ts`).
- **Por qué:** mismo patrón que `hermes_bootstrap.py::normalize_douglas_env()`
  en el lado Python (Paso 2) — normalizar una vez, muy al principio,
  en vez de envolver cada sitio de lectura individualmente.
- **Alternativa descartada:** envolver cada uno de los ~7
  `process.env.HERMES_DESKTOP_*` con un fallback — viola la misma
  regla de "no tocar los llamadores existentes" que motivó el diseño
  del Paso 2.
- **Riesgo de merge:** bajo — bloque nuevo de ~9 líneas, no modifica
  ninguna línea existente.
- **Commit:** `fix(brand): resolve Paso 3 follow-up items`

## apps/desktop/electron/main.ts (3/3 — URI scheme `douglas://`)

- **Qué:** `HERMES_PROTOCOL` (constante única) se reemplaza por
  `DEEP_LINK_PROTOCOLS = ['douglas', 'hermes']` — el registro con el SO
  (`app.setAsDefaultProtocolClient`) ahora ocurre para ambos schemes, y
  la detección de un deep link entrante (`_extractDeepLink`) acepta
  cualquiera de los dos. Al reconstruir un link pendiente
  (`ipcMain.handle('hermes:deep-link-ready', ...)`) se usa
  `CANONICAL_DEEP_LINK_PROTOCOL = 'douglas'` — solo se generan links
  `douglas://` desde ahora, `hermes://` queda como entrada aceptada por
  compatibilidad con enlaces existentes en docs/dashboard.
- **Por qué:** pedido explícito — "se añade, no se sustituye".
- **Alternativa descartada:** ninguna — es la forma directa de añadir
  un scheme sin romper el existente.
- **Riesgo de merge:** bajo — mismo patrón que el archivo ya usaba
  (una constante controla el comportamiento en 3 sitios), solo pasa de
  string a array e itera.
- **Commit:** `feat(protocol): register douglas:// alongside hermes:// deep links`

## apps/desktop/electron/userdata-migration.ts (nuevo) + main.ts (4/4 — migración de userData)

- **Qué:** módulo nuevo, `migrateUserDataFromLegacyHermes()`, más un
  bloque en `main.ts` que lo invoca justo antes de la primera lectura
  de `app.getPath('userData')` (línea del bloque de sandbox de
  Windows). Si el directorio nuevo (`productName` = "Douglas Agent")
  está vacío/no existe y el legado (`productName` = "Hermes", mismo
  padre vía `app.getPath('appData')`) tiene datos, **copia** (nunca
  mueve) el contenido completo — preservando el modo de cada archivo,
  crítico para `native-oauth-tokens.json` — y escribe un marcador
  `.migrated-from-hermes` con qué se copió y cuántos archivos. Si la
  copia falla a mitad de camino, no se escribe el marcador (permite
  reintento en el próximo arranque) y `main.ts` muestra un
  `dialog.showErrorBox` en el primer tick de `app.whenReady()` — antes
  de `createWindow()` — explicando qué pasó y dónde sigue estando el
  dato original (nunca se borra ni se mueve).
- **Por qué:** hallazgo de revisión pre-merge del Paso 3 —
  `productName` cambió de `"Hermes"` a `"Douglas Agent"` en
  `4c8da5049`, y Electron resuelve `userData` por defecto como
  `path.join(app.getPath('appData'), productName)`. Sin este parche,
  cualquier usuario existente pierde silenciosamente
  `connection.json`, `window-state.json`, `active-profile.json`,
  `native-oauth-tokens.json`, etc. — el mismo directorio HERMES_HOME
  ya tenía cadena de compatibilidad (Pasos 2/3 arriba); `userData` de
  Electron (un concepto totalmente distinto — vive bajo
  `appData`/Roaming, no bajo `LOCALAPPDATA`/`HERMES_HOME`) no tenía
  ninguna.
- **Decisión de diseño (pedida explícitamente):** migrar, no fijar
  (`app.setPath` apuntando para siempre al nombre viejo) — anclarse a
  "Hermes" a perpetuidad es deuda permanente. La ruta legado se
  calcula con `path.join(appDataPath, 'Hermes')` donde `appDataPath`
  viene de `app.getPath('appData')` (la propia resolución de
  Electron) — el módulo no contiene un solo literal de ruta específico
  de plataforma (`%APPDATA%`, `Application Support`, `.config`); por
  construcción no tiene ramas condicionadas a la plataforma que
  probar por separado.
- **`apps/bootstrap-installer`:** no tiene un `userData` propio al
  estilo Electron — su equivalente (`hermes_home()` en `paths.rs`) ya
  usa la cadena Douglas/Hermes desde el Paso 3 y no deriva de
  `productName`/`identifier` de Tauri (que, de hecho, siguen sin
  rebrandear: `tauri.conf.json` todavía dice `"productName": "Hermes"`).
  Nada que migrar ahí todavía.
- **Alternativa descartada:** `app.setPath('userData', <ruta vieja>)`
  al arrancar — descartada explícitamente por decisión de producto
  (ver arriba); habría evitado el problema pero fijado el nombre
  "Hermes" en el disco de todo usuario nuevo para siempre.
- **Riesgo de merge:** bajo — archivo nuevo aislado + ~30 líneas
  insertadas en dos puntos de `main.ts` (antes del bloque de sandbox
  de Windows, y al inicio de `whenReady().then()`); no modifica
  ninguna lectura de `userData` existente.
- **Tests:** `apps/desktop/electron/userdata-migration.test.ts` — legado
  con datos + nuevo vacío → migra; ambos con datos → no toca nada;
  ninguno con datos → instalación limpia; marcador ya presente →
  idempotente; fallo de copia a mitad → error reportado, legado
  intacto, sin marcador. Ejecutado y verificado manualmente con
  `node --experimental-strip-types` (el `node_modules` de este
  checkout está roto — ver nota de reinstalación aparte — así que
  `npm run test:desktop:platforms` no pudo confirmarse en esta
  sesión; recomendado correrlo tras la reinstalación limpia).
- **Commit:** *(pendiente — sin commit todavía en esta sesión)*

## Corrección — `DOUGLAS_DESKTOP_REMOTE_URL` (verificación, no bug)

Un reporte previo de esta sesión afirmó que
`process.env.DOUGLAS_DESKTOP_REMOTE_URL` nunca se lee y que el texto
de ayuda en `hardening.ts` (líneas ~68/81) era engañoso. Eso era
**incorrecto** — producto de un `grep` sobre el literal
`DOUGLAS_DESKTOP_REMOTE_URL` que no encontró el normalizador genérico
de `main.ts:517-521` (`key.startsWith('DOUGLAS_DESKTOP_')`), documentado
arriba en "Paso 3 (2/2)". Verificado de nuevo línea por línea: el
bloque corre en el top-level del módulo, antes de cualquiera de los
~7 sitios que leen `process.env.HERMES_DESKTOP_*` (el primero está a
~6900 líneas de distancia) — `DOUGLAS_DESKTOP_REMOTE_URL` sí funciona,
mapeado a `HERMES_DESKTOP_REMOTE_URL` antes de que nada lo consuma. El
texto de ayuda es correcto tal cual está. No se tocó nada aquí.

## apps/desktop/electron/main.ts (5 — AppUserModelId)

- **Qué:** `app.setAppUserModelId('com.nousresearch.hermes')` →
  `'com.douglasdevsec.douglas-agent'`, con comentario explicando por
  qué (alinea con `build.appId`/`executableName`/nombre de acceso
  directo NSIS, que ya habían cambiado).
- **Por qué:** hallazgo de auditoría — dejar el AUMID viejo mientras
  el exe, el `appId` y el nombre del acceso directo ya cambiaron era
  incoherente, no protector: un acceso directo nuevo se crea de todas
  formas sin agrupar con uno viejo, porque apunta a un `.exe` con
  nombre distinto independientemente del AUMID.
- **Qué rompe (decisión consciente, no un bug):** un usuario que
  actualiza desde una instalación Hermes pierde el agrupamiento de la
  barra de tareas / jump list / permisos de notificación del icono
  anclado viejo — se resetean, hay que volver a anclar. No hay pérdida
  de datos (esto no toca `userData` ni `HERMES_HOME`).
- **Riesgo de merge:** trivial — una constante de tipo string.
- **Commit:** *(pendiente)*

## apps/desktop/electron/main.ts (6 — blindaje de `safeStorage.decryptString()`)

- **Qué:** `decryptDesktopSecret()` gana un parámetro `context` y,
  en el `catch` de `safeStorage.decryptString()` (antes silencioso,
  `catch { return '' }`): registra vía `rememberLog` qué secreto
  falló y por qué, y dispara `notifyCredentialDecryptFailure()` — una
  función nueva que muestra, una sola vez por sesión (deduplicada con
  un flag de módulo), `dialog.showErrorBox('Douglas Agent', 'Tus
  credenciales guardadas no pudieron leerse tras la actualización.
  Vuelve a conectar tus cuentas.')`, en cuanto la app está lista
  (inmediato si `app.isReady()`, encolado en `app.whenReady()` si no).
  Los 8 sitios que llaman a `decryptDesktopSecret()` ahora pasan una
  etiqueta de contexto (`'native OAuth tokens (<url>)'`, `'remote
  gateway token'`, `'SSH token (profile <p>)'`, etc.) para que el log
  diga cuál credencial fue.
- **Por qué:** decisión explícita de producto tras el hallazgo de
  `safeStorage`/Keychain (ver `douglas/README.md`, "Verificar en
  hardware real" #1) — **no** intentar migrar la clave del llavero
  (no verificable sin hardware macOS/Linux; adivinar sería peor que no
  hacer nada), sino blindar el fallo: nunca crash, nunca estado
  corrupto, siempre tratado como "no autenticado" (el retorno `''` ya
  hacía esto en los 8 call sites, sin cambios ahí), mensaje explícito
  en vez de un error genérico, y el archivo cifrado nunca se borra —
  puede volver a descifrar si el usuario revierte de versión.
- **Alternativa descartada:** intentar re-encriptar/migrar la clave
  automáticamente — descartada explícitamente por decisión de
  producto: no hay forma de verificar que funcione sin el hardware, y
  un intento de migración fallido silenciosamente sería peor que el
  mensaje explícito.
- **Riesgo de merge:** bajo — el `catch` ya existía y ya devolvía
  `''`; el cambio es puramente aditivo (logging + una notificación
  deduplicada), ningún call site cambia su manejo del valor de
  retorno.
- **Verificación pendiente:** no se puede confirmar en esta sesión
  que el fallo de descifrado realmente ocurre en macOS/Linux tras el
  rebrand — ver `douglas/README.md`, "Verificar en hardware real" #1.
- **Commit:** *(pendiente)*

## Investigación — "el gateway no arranca" (no era el gateway)

Reporte del usuario: al abrir la app, pantalla de error "Douglas Agent
couldn't start / Desktop IPC bridge is unavailable", app se cierra
sola. Investigado a fondo antes de tocar nada, como se pidió.

**Causa raíz confirmada:** ninguna relación con el rebranding ni con el
backend Python. `apps/desktop/dist/` (el build de producción del
renderer) llevaba desde el **27 de julio** sin regenerarse — seis días
de antigüedad respecto al código fuente actual — y el bundle
`index-Apv7o_hR.js` referenciaba una variable `emptySessionsText` que
ya no existe en el código fuente actual (`ReferenceError:
emptySessionsText is not defined`, capturado en
`AppData/Local/hermes/logs/desktop.log`, dentro del error boundary de
la lista de sesiones). El crash del renderer ocurre milisegundos
*después* de que el backend reporta "ready" — el gateway sí arranca;
lo que se rompe es la UI intentando pintar sobre un bundle obsoleto.

Confirmado con `npm run build` (regenera `dist/` desde el código
actual) + relanzamiento: mismo arranque, mismo backend, sin el
`ReferenceError`. Verificado también por separado que la lógica de
resolución del backend (`resolveHermesHome()`, `resolveHermesBackend()`,
`ensureRuntime()`) no cambió una sola línea de comportamiento entre
`80d358dd8` y `HEAD` — el diff completo de esas funciones son
únicamente los dos textos corregidos en el commit de typos, nada de
lógica.

Entorno Python en esta máquina: totalmente configurado desde el 19 de
julio (`%LOCALAPPDATA%\hermes\hermes-agent\venv`, `config.yaml`,
`auth.json`, sesiones reales) — no es un clon nuevo sin configurar.
`HERMES_HOME` resuelve consistentemente a esa ruta vía un valor de
registro de Windows heredado de un `install.ps1` antiguo
(`HKCU\Environment\HERMES_HOME`), que gana antes de que la lógica de
existencia de directorio (`%LOCALAPPDATA%\douglas` vs `\hermes`)
llegue a evaluarse. `%LOCALAPPDATA%\douglas` también existe en esta
máquina (config/auth/sesiones propios, sin `hermes-agent/` — probablemente
de un uso separado del entrypoint `douglas` instalado vía pip) pero
nunca entra en juego aquí por el registro; **queda como riesgo teórico
real para una máquina nueva sin ese registro heredado**, no descartado,
solo no es lo que pasó en esta sesión.

**No es un problema del código de este repo — es un artefacto local de
esta máquina de desarrollo.** No se abre ninguna acción de código para
esto; documentado aquí para que quede claro qué se investigó y qué se
descartó.

## apps/desktop/src — huecos de branding que el Paso 3 no cubrió

- **Qué:** cuatro strings más, encontrados con una búsqueda dirigida
  tras entender el patrón (ver "por qué" abajo): `WORDMARK = 'HERMES
  AGENT'` en `components/chat/intro.tsx` (el banner grande de la
  pantalla de nueva sesión — cambiado a `'DOUGLAS AGENT'`, con fuente
  Dimitri Swank nueva vía `@font-face` en `styles.css` y color
  `text-emerald-600 dark:text-emerald-400` en vez del `text-midground`
  genérico); dos `<DecodeText text="HERMES" />` (mismo componente
  reutilizado en `app/contrib/context.tsx` y
  `components/pane-shell/tree/renderer/tree-group.tsx`, el estado
  vacío de un panel — cambiados a `'DOUGLAS AGENT'`); y `<p>Uninstall
  Hermes</p>` en `app/settings/uninstall-section.tsx` (cambiado a
  `Uninstall Douglas Agent`).
- **Por qué se escaparon del Paso 3:** el commit de i18n
  (`cdbf73000`) rebrandeó `apps/desktop/src/i18n/*.ts` — el
  diccionario de strings traducibles. Estos cuatro son literales de
  JS/JSX **fuera** de ese diccionario: una `const` de módulo
  (`WORDMARK`), texto pasado directo a un prop (`text="HERMES"`), y
  texto JSX inline (`<p>Uninstall Hermes</p>`). Una búsqueda con
  alcance en los archivos de i18n nunca los habría visto.
- **Barrido con el patrón corregido:** `grep` de "Hermes" en
  `apps/desktop/src/**/*.{ts,tsx}` fuera de `i18n/`, filtrando
  identificadores (`window.hermesDesktop`, eventos `hermes:*`,
  `HERMES_PATHS_MIME`, tipos, imports — todo correcto sin tocar) y
  comentarios de código (no visibles al usuario, no tocados). Dos
  strings visibles quedaron **intencionalmente sin cambiar** por ser
  referencias reales a algo externo, mismo criterio que "Hermes
  Cloud" en el Paso 3 original:
  - `app/settings/billing/errors.ts:64` — "the portal's Hermes Agent
    page" — nombra una página real en `portal.nousresearch.com`.
  - `app/settings/constants.ts:45` — "Hosted Hermes & Nous-trained
    models" — descripción real del grupo de proveedores `NOUS_` (ese
    mismo portal).
- **Riesgo de merge:** bajo — cinco cambios de texto/estilo aislados
  más un `@font-face` nuevo, ningún cambio de lógica.
- **Verificado:** `tsc --build tsconfig.json` (0 errores) + `npm run
  build` + relanzamiento real de la app — capturado visualmente:
  "DOUGLAS AGENT" en verde esmeralda, fuente Dimitri Swank, en la
  pantalla de nueva sesión.

## apps/desktop/electron/main.ts (7 — aviso de `dist/` desfasado)

- **Qué:** `warnIfRendererBundleStale()`, llamada desde
  `resolveRendererIndex()` cada vez que se resuelve sin servidor de
  desarrollo. Compara la fecha de `dist/index.html` contra el archivo
  `.ts`/`.tsx` más reciente bajo `src/` (escaneo acotado a 4000
  archivos); si `src/` es más nuevo por más de 5 minutos, escribe un
  aviso (consola + `desktop.log`) indicando que puede haber un bundle
  desfasado y sugiriendo `npm run build`. Nunca bloquea el arranque.
- **Por qué:** hallazgo de esta sesión — un `dist/` de 6 días de
  antigüedad produjo un `ReferenceError` en el renderer que parecía
  "el gateway no arranca" (ver `douglas/README.md`, "Si la app arranca
  y muere"). `npm run dev` nunca lee `dist/`, así que nada más en el
  proyecto podía haber avisado de esto.
- **Decisión de diseño (importante):** gateado en el `app.isPackaged`
  **real** de Electron, no en el `IS_PACKAGED` combinado del módulo —
  intencional. La primera versión de este parche usaba `IS_PACKAGED`
  y el aviso nunca disparaba en la prueba, precisamente porque
  `HERMES_DESKTOP_IS_PACKAGED=1` (el override manual usado para probar
  el código de modo empaquetado desde un checkout de desarrollo) hace
  `IS_PACKAGED` verdadero — exactamente el patrón que este aviso
  existe para detectar. Corregido antes de mergear, verificado con una
  prueba end-to-end real (ver abajo).
- **Alternativa descartada:** comparar contra el `install-stamp.json`
  o el bundle de `electron-main.mjs` en vez de escanear `src/` —
  descartada porque ninguno de los dos se actualiza al mismo ritmo que
  el renderer específicamente; un desfase entre `electron-main.mjs`
  (que sí se regenera en cada `npm run dev`) y `dist/assets` habría
  dado falsos positivos constantes en flujo de desarrollo normal.
- **Riesgo de merge:** bajo — función nueva, aislada, solo logging,
  ningún cambio de comportamiento de arranque.
- **Verificado end-to-end:** tocar `src/main.tsx` + retrasar
  artificialmente `dist/index.html` 1 hora + lanzar con
  `HERMES_DESKTOP_IS_PACKAGED=1 electron .` → el aviso apareció
  correctamente ("dist/ looks stale: ... ~1.0 hour(s) newer..."). Tras
  corregir el bug de gating (`IS_PACKAGED` → `app.isPackaged`),
  re-probado y confirmado. `tsc --build tsconfig.electron.json` (0
  errores) en cada iteración.

## Verificación real — Fase 1, cierre

- **Migración de userData contra datos reales (autorizada
  explícitamente):** copia completa de `%APPDATA%\Douglas Agent\` a
  `.backup-manual` (verificada byte a byte: 1215 archivos, mismo
  tamaño total, muestreo de archivos clave idéntico) antes de tocar
  nada; renombrado a `.pre-test`; arranque real de la app.
  Resultado: migró 80/80 archivos desde `%APPDATA%\Hermes\` real,
  `.migrated-from-hermes` con el contenido esperado (`migratedFrom`,
  `migratedAt`, `fileCount`, lista completa de archivos), y
  `%APPDATA%\Hermes\` quedó exactamente igual que antes (80 archivos,
  mismo tamaño en bytes) — confirmando que fue copia, no movimiento.
  `native-oauth-tokens.json` no existe en los datos reales de esta
  máquina (OAuth nativo nunca se usó) — la preservación de permisos
  para ese archivo específico sigue solo cubierta por el test unitario
  sintético, no por esta prueba real. Carpeta original restaurada y
  verificada idéntica al backup; backup manual dejado en disco para
  que el usuario decida si lo borra.
- **Cadena de resolución en "máquina limpia" simulada:** no se pudo
  probar lanzando la app real sin tocar el registro — dos intentos
  (`ln -s`/shadow de `reg.exe` vía PATH, y exclusión de
  `System32` del PATH del proceso hijo) fallaron por razones no
  relacionadas con el registro (el shadow no interceptó de forma
  fiable; excluir `System32` rompió el arranque interno de
  Electron/Chromium — `Error: Failed to get 'appData' path` — antes de
  llegar siquiera al código de la app). En su lugar, se verificó la
  lógica exacta con una réplica fiel del algoritmo de
  `resolveHermesHome()` (rama Windows), usando la función real
  `readWindowsUserEnvVar()` sin modificar (importada de su módulo,
  con un `exec` inyectado que simula "valor no encontrado" — el mismo
  resultado que un `reg query` real fallaría en una máquina limpia,
  sin tocar `HKCU\Environment` en ningún momento) y rutas de sandbox
  para `%LOCALAPPDATA%`/home. Las tres ramas (solo `douglas`, solo
  `hermes`, ninguna) resolvieron correctamente. Documentado como
  verificación parcial en "Riesgos abiertos" — la réplica prueba el
  algoritmo, no la app real arrancando en una máquina sin el valor de
  registro heredado.
- **Commit:** *(pendiente)*

## Reconciliación con upstream/main — native-token-store.ts (post-recuperación)

- **Contexto:** al recuperar `main` desde el PR mergeado con snapshot
  obsoleto (ver reporte de recuperación en el hilo de trabajo) y
  rehacer `git merge upstream/main`, upstream trajo 4 commits que
  tocan la misma zona que el blindaje de `safeStorage` de la Fase 1:
  extraen la persistencia de tokens nativos a un archivo nuevo,
  `apps/desktop/electron/native-token-store.ts`
  (`persistNativeTokenSet` / `loadNativeTokenSet` +
  `interface NativeTokenStoreIo`), y corrigen un bug real (#73271):
  el parser de recarga usaba `parseTokenResponse` (formato
  snake_case de las respuestas del gateway) sobre un blob que en
  realidad es el `NativeTokenSet` normalizado en camelCase que este
  mismo módulo escribió — la excepción resultante se tragaba en cada
  arranque y se manifestaba como "se cierra la sesión en cada
  reinicio". El archivo nuevo usa `parseStoredTokenSet` correctamente
  y además redacta `user:password@` de la URL del gateway antes de
  loguear errores de descifrado (`redactGatewayUrl`).
- **Decisión: se queda la versión de upstream completa**, sin
  reescribirla. Motivo: arquitectura genuinamente superior
  (inyección de dependencias, testeable sin runtime de Electron),
  corrige un bug real preexistente, y añade una protección de
  seguridad (redacción de credenciales en logs) que no existía antes.
  No había nada que "mi versión hiciera mejor" en este archivo
  específico — no lo tocaba.
- **El blindaje de `decryptDesktopSecret` (Fase 1) NO es redundante
  — se mantiene intacto.** Motivo: `NativeTokenStoreIo.decrypt` es un
  punto de inyección; en `main.ts`, `_nativeTokenStoreIo()` inyecta
  exactamente `decrypt: decryptDesktopSecret` — es decir, el
  try/catch, el degradado a `''` sin lanzar, el log vía
  `rememberLog`, y el diálogo único
  `notifyCredentialDecryptFailure()` con el mensaje explícito en
  español siguen siendo el camino real de descifrado, ahora invocado
  una capa más adentro (`loadNativeTokenSet` → `io.decrypt` →
  `decryptDesktopSecret`) en vez de inline. Además,
  `decryptDesktopSecret` sigue siendo usado directamente por los
  otros 7 sitios de descifrado de `main.ts` (tokens de gateway
  remoto, tokens SSH por perfil y globales) que
  `native-token-store.ts` no toca. La versión de upstream, por sí
  sola, solo loguea a `desktop.log` (`io.rememberLog`) cuando el
  descifrado falla — no muestra ningún diálogo al usuario. Sin
  `decryptDesktopSecret` inyectado como la implementación real,
  upstream no cumpliría el requisito 3 de la Fase 1 (mensaje
  explícito y visible al usuario). Confirmado con grep tras el
  merge: los 7 call sites originales de `decryptDesktopSecret` siguen
  presentes y sin cambios.
- **Los 4 requisitos originales de blindaje de `safeStorage` (Fase
  1) siguen cumplidos tras el merge combinado:**
  1. Todo `safeStorage.decryptString()` sigue envuelto en try/catch
     — vía `decryptDesktopSecret`, ahora también reenvuelto por el
     try/catch propio de `loadNativeTokenSet`.
  2. Degradado a "no autenticado" sin crash — ambas capas devuelven
     `null`/`''` en vez de lanzar hacia arriba.
  3. Mensaje explícito al usuario — sigue siendo
     `notifyCredentialDecryptFailure()`, sin cambios.
  4. Nunca se borra el archivo cifrado en un fallo de lectura — ni
     `decryptDesktopSecret` ni `loadNativeTokenSet` tocan el archivo
     en la rama de error; `loadNativeTokenSet` explícitamente deja
     la entrada intacta "for retry".
- **Conflicto de fusión real:** solo `_loadNativeTokens()` en
  `main.ts` (mi lógica inline referenciaba una variable `secret` que
  ya no existía en el contexto nuevo). Resuelto tomando la versión de
  upstream completa, que delega en
  `loadNativeTokenSet(baseUrl, _nativeTokenStoreIo())`.
- **Icono de Windows (`80c86c494`): sí aplica.** El cambio en
  `main.ts` (preferir `resources/icon.ico` / `assets/icon.ico` de
  borde completo sobre el PNG con margen como ícono de la ventana en
  Windows) fusionó sin conflicto y aplica tal cual a esta app.
  Investigar esta zona además destapó un bug real y preexistente en
  el propio `icon.ico` de Douglas Agent — generado con `.save()`
  llamado sobre un frame de 16×16 ya reducido en vez de la imagen
  maestra a resolución completa, produciendo silenciosamente un
  archivo de un solo frame de 727 bytes desde el primer commit del
  ícono (`30abfa66c`). Corregido y regenerado (`icon.ico` de
  `apps/desktop/assets` y de
  `apps/bootstrap-installer/src-tauri/icons`): 7 tamaños presentes,
  96.1% de cobertura de píxel a 256px. Sin relación con el commit de
  upstream, pero probablemente habría seguido sin detectarse sin este
  merge.
- **Riesgo de merge:** bajo — la superficie pública que el resto de
  `main.ts` usa (`persistNativeTokenSet` / `loadNativeTokenSet` vía
  `_nativeTokenStoreIo()`) no cambió de forma incompatible; los 8
  call sites de `decryptDesktopSecret` fuera de este archivo no se
  tocaron.
- **Verificado:** `tsc --build tsconfig.electron.json --force` y
  `tsc --build tsconfig.json --force` sin errores tras el merge;
  `git status` limpio; `tests-douglas/` 18/18 (el traceback de
  `PermissionError` visto tras la última prueba es un fallo de
  limpieza de pytest en un symlink temporal de Windows, posterior a
  que las 18 pruebas ya reportaran PASSED — no es un fallo de
  prueba); `npm run build` completo sin errores; `npm run dev`
  arranca, la ventana de Electron permanece abierta (5 procesos
  estables, sin el crash "Desktop IPC bridge is unavailable" del
  hallazgo de Fase 1) — el único error en el log es
  `Timed out connecting to Douglas Agent backend after 15000ms`,
  consistente con el entorno Python/venv no configurado en este
  checkout de desarrollo (hallazgo ya documentado en la Fase 1, no
  una regresión de este merge).
- **Commit:** `afce28165` "Merge upstream/main into main (recovered
  base)".

## Capa social — Etapa A, Bloque 2 (frontend mockeado)

Sin backend real: todo mockeado (`apps/desktop/src/app/social/fixtures.ts`).
Cuatro piezas, todas nuevas, siguiendo patrones ya existentes en vez de
inventar los propios (investigado primero, ver el punto de entrada del
prompt Etapa A):

- **2.1 Panel de configuración de redes** —
  `apps/desktop/src/app/social/index.tsx` (`SocialView`). Usa el primitivo
  `Panel`/`PanelHeader` (`app/overlays/panel.tsx`, el mismo que cron/
  webhooks) y `ListRow` (`app/settings/primitives.tsx`) para las 6 filas de
  red — es el shape existente más cercano a "fila con estado + botón de
  acción", no uno nuevo.
- **2.2 Asistente de conexión** —
  `apps/desktop/src/app/social/connection-wizard.tsx`. Sin primitivo de
  stepper reutilizable en el repo (confirmado); se construyó uno nuevo,
  pero copiando el idioma estado→icono de `StageRow` en
  `desktop-install-overlay.tsx`. Parametrizado por
  `WizardStepDefinition[]` — los pasos reales de Meta quedan pendientes de
  la experiencia real del usuario conectando a mano (ver
  `PROMPT-CAPA-SOCIAL-ETAPA-A.md`, nota ⚠️ en A2). Validación 100%
  simulada (`window.setTimeout`).
- **2.3 Tarjeta de aprobación** —
  `apps/desktop/src/app/social/approval-card.tsx`
  (`SocialApprovalCard`) + registro en
  `apps/desktop/src/components/assistant-ui/thread/message-parts.tsx`
  (`ChainToolFallback`, nueva rama `toolName === 'social_publish'`,
  siguiendo el patrón exacto de `components/assistant-ui/tool/approval.tsx`
  para tarjetas interactivas embebidas en el hilo). **Sin backend, nadie
  emite hoy un tool call `social_publish` real** — el registro en el
  pipeline es real y queda listo para Etapa C, pero se ejercita en esta
  etapa vía el botón "Vista previa" del panel (2.1), que monta el mismo
  componente con datos mock dentro de un `Dialog`. Documentado en el propio
  componente para que no se lea como "ya conectado a un tool real".
- **2.4 Gating premium** —
  `apps/desktop/src/components/premium-gate.tsx` (`PremiumGate`,
  `isPremiumUser()`). Deliberadamente en `components/`, no en `app/social/`
  — es el único punto de decisión "¿es premium?" para reutilizar en
  cualquier otra superficie de pago futura, no solo redes sociales.
  Confirmado que no existía nada parecido en el repo (ni lock+upsell modal,
  ni gating por tier) antes de esto.

**Núcleo tocado** (rastreado aquí por la regla de compatibilidad — nada
renombrado, todo aditivo):
- `apps/desktop/src/app/routes.ts` — nueva ruta `/social`
  (`SOCIAL_ROUTE`), `'social'` añadido a `AppView`/`AppRouteId`/
  `OVERLAY_VIEWS`.
- `apps/desktop/src/app/types.ts` — `'social'` añadido a `SidebarNavId`.
- `apps/desktop/src/app/chat/sidebar/index.tsx` — nueva entrada en
  `SIDEBAR_NAV` (ícono `megaphone`, ruta `/social`) + condición de
  `active`.
- `apps/desktop/src/app/shell/hooks/use-overlay-routing.ts` — deriva
  `socialOpen` igual que `webhooksOpen`/`cronOpen`.
- `apps/desktop/src/app/contrib/wiring.tsx` — lazy import de `SocialView`
  + render condicional en `socialOpen`.
- `apps/desktop/src/app/hooks/use-keybinds.ts` y
  `apps/desktop/src/lib/keybinds/actions.ts` — acción `nav.social`
  registrada (sin atajo por defecto, igual que `nav.cron`/`nav.agents`).
- `apps/desktop/src/i18n/types.ts` — nuevo bloque `social` en
  `Translations`.
- `apps/desktop/src/i18n/en.ts` — contenido real del namespace `social` +
  `sidebar.nav.social` + `keybinds.actions['nav.social']`.
- `apps/desktop/src/i18n/zh.ts` — **placeholder en inglés**, marcado
  `TODO(i18n)` en el propio archivo. Es el único locale tipado
  directamente contra `Translations` (los demás pasan por
  `defineLocale()`, que hace merge con claves opcionales sobre `en` — ver
  `i18n/define-locale.ts`), así que sin este bloque `tsc --build` fallaba
  en `zh.ts` aunque `ar.ts`/`ja.ts`/`zh-hant.ts` no necesitaban tocarse.
  Pendiente: pasada de traducción real antes de publicar la capa social en
  chino simplificado.
- `apps/desktop/src/components/assistant-ui/thread/message-parts.tsx` —
  nueva rama en `ChainToolFallback` (ver 2.3 arriba).

**Decisión sin implementar, reportada para revisión aparte (regla 0.4/R6,
no elegido unilateralmente):** `apps/desktop/src/app/social/*/
assets/brand/logo_black.png` (ver sección "Iconografía e ilustraciones"
más arriba) — confirmado que no aplica aquí, `BrandMark` no lo necesita.
Pendiente real distinto: el origen de la captura que motivó el botón bajo
"Automation" resultó ser un mockup aparte, no código existente — se
resolvió preguntando antes de construir (ver conversación), no se asumió.

**Verificado:** `tsc --build` (electron + renderer) sin errores;
`eslint` limpio tras `--fix` (solo orden de imports); `npm run build`
completo; `tests-douglas/` 18/18. `npm run dev` no se relanzó para esta
verificación — el puerto 5174 ya tenía una sesión activa con una conexión
ESTABLISHED (aparente sesión de `dev-sandbox.sh` en curso) y no se tocó
para no interrumpir trabajo en curso; verificación visual pendiente de
confirmación directa.
- **Commit:** *(pendiente)*

## Identidad del agente en chat — de "Hermes Agent / Nous Research" a "Douglas Agent / DouglasDevSec"

**Motivo:** el usuario preguntó "¿quién eres?" / "¿eres humano?" al agente real y
respondió "Soy Hermes Agent... creado por Nous Research" — el rebrand de la
Fase 1 solo tocó `apps/desktop/` (UI de Electron); el system prompt del
backend Python nunca se tocó.

### Dónde vivía el texto (un solo choke point, no strings dispersos)

- `agent/prompt_builder.py` — `DEFAULT_AGENT_IDENTITY` (fallback si no hay
  `SOUL.md`) y `HERMES_AGENT_HELP_GUIDANCE` (ambas alimentan
  `agent/system_prompt.py::build_system_prompt_parts`, la única ruta real
  hacia el prompt que ve el modelo — confirmado también usado por
  `agent/codex_responses_adapter.py` y `agent/transports/codex.py` vía el
  mismo import, así que un solo lugar cubre las tres transports).
- `hermes_cli/default_soul.py` — `DEFAULT_SOUL_MD`, sembrado en
  `HERMES_HOME/SOUL.md` en el primer arranque. **Gana sobre
  `DEFAULT_AGENT_IDENTITY`** si el archivo existe (ver
  `agent/system_prompt.py:189-201`) — por eso hacía falta tocar los dos
  lugares, no solo uno.
- `docker/SOUL.md` — archivo sembrado para instalaciones Docker, mismo texto,
  tocado por consistencia aunque no es la ruta de instalación típica de un
  usuario de Douglas Agent en desktop.

### Blindaje anti-extracción (nuevo, primero en el repo)

Se pidió explícitamente resistir prompts complejos/inyección que intenten
sacarle al modelo que está construido sobre Hermes/Nous Research. No existía
ningún guard de identidad en el repo (sí existe uno de seguridad de comandos,
`CronPromptInjectionBlocked` en `cron/scheduler.py`, pero es de otra clase de
ataque). Se añadió una cláusula explícita a `DEFAULT_AGENT_IDENTITY` /
`DEFAULT_SOUL_MD` / `docker/SOUL.md` instruyendo al modelo a mantener la
identidad Douglas Agent/DouglasDevSec sin importar cómo se le pida lo
contrario.

**Iteración real durante la verificación:** la primera redacción de esa
cláusula usaba la frase "a request to ignore previous instructions" — el
propio escáner anti-inyección del repo (`tools/threat_patterns.py`,
patrón `ignore\s+...\s+instructions`, scope "all") la detectó como
inyección de prompt y bloqueó el `SOUL.md` sembrado
(`test_empty_dir_loads_seeded_global_soul` lo capturó en rojo). Reescrito
sin las frases gatillo literales ("ignore previous instructions",
"hypothetical", "role-play") manteniendo la misma intención defensiva —
verificado contra los ~30 patrones de `threat_patterns.py` uno por uno
antes de aplicar. Lección: cualquier instrucción defensiva que describa el
ataque que bloquea corre el riesgo de sonar como el propio ataque.

### Instalaciones ya sembradas — mecanismo de auto-upgrade existente, no uno nuevo

`hermes_cli/config.py::_ensure_default_soul_md()` ya upgradeaba en el sitio
cualquier `SOUL.md` que coincidiera *exactamente* con una plantilla conocida
sin intención del usuario (antes: solo los scaffolds de solo-comentarios de
instaladores viejos). Se añadieron dos entradas nuevas a
`_LEGACY_TEMPLATE_SOULS` (`hermes_cli/default_soul.py`) — sin construir nada
nuevo, reutilizando el mecanismo tal cual:

1. `_PRE_DOUGLAS_DEFAULT_SOUL_MD` — el `DEFAULT_SOUL_MD` anterior, verbatim
   (Hermes/Nous sin tocar).
2. `_PARTIAL_REBRAND_SOUL_MD` — hallazgo real inspeccionando esta máquina:
   `%LOCALAPPDATA%\douglas\SOUL.md` (fechado 2026-07-26, de una pasada de
   rebrand anterior) tenía "Douglas Agent" pero **"created by Nous
   Research"** sin corregir — un find/replace a medias, no algo que el
   usuario escribió. Mismo tratamiento: entra a la lista de plantillas sin
   intención de usuario, se auto-corrige solo.

Verificado con las dos instalaciones reales de esta máquina:
`%LOCALAPPDATA%\hermes\SOUL.md` ya coincidía byte a byte con el
`DEFAULT_SOUL_MD` nuevo (se auto-actualizó solo durante esta sesión, sin
intervención manual — confirma que el mecanismo corre en cada arranque del
backend). `%LOCALAPPDATA%\douglas\SOUL.md` (el que probablemente usa la app
de escritorio real, dado que `resolveHermesHome()` prioriza un directorio
`douglas` existente sobre `hermes`) coincide con `_PARTIAL_REBRAND_SOUL_MD`
— `is_legacy_template_soul()` devuelve `True` — se corregirá solo en el
próximo arranque del backend.

### Tests

Dos tests upstream afirmaban el string literal "Hermes Agent" en el prompt
construido — actualizados a "Douglas Agent" porque el cambio de contenido es
intencional (`tests/agent/test_prompt_builder.py`,
`tests/run_agent/test_run_agent.py`). Ningún otro test en el repo depende
del texto viejo (barrido completo con grep antes de tocar nada) — las otras
referencias a "Hermes Agent"/"Nous Research" en `tests/` son de dominios
distintos sin relación (cabecera de copyright Apache 2.0, detección del
modelo LLM "Nous Hermes", nombre de un proveedor OAuth) y no se tocaron.

**Fallas preexistentes descubiertas durante la verificación, no causadas por
este cambio** (confirmado con `git stash` contra cada una individualmente):
`test_build_system_prompt_records_stable_prefix` (fuga de estado entre tests
vía un `contextvars.ContextVar` de warnings de truncado no drenado, más un
mock incompleto), `test_coding_prompt_preserves_legacy_workspace_order`
(separador de ruta `/` vs `\`, específico de Windows),
`TestGetHermesHome::test_default_path` (esta máquina real tiene
`HERMES_HOME` fijado por variable de entorno, el test asume un entorno
limpio), `test_interruptible_anthropic_interrupt_never_closes_shared_client`
(falta el paquete `anthropic` en este `.venv`). Documentadas aquí, no
arregladas — fuera de alcance de este cambio.

**Verificado:** `tests/agent/test_prompt_builder.py`,
`tests/agent/test_system_prompt.py`, `tests/agent/test_system_prompt_restore.py`,
`tests/hermes_cli/test_config.py`, `tests/run_agent/test_run_agent.py`
(subset filtrado + verificación de las 4 fallas preexistentes vía stash);
`tests-douglas/` 18/18.
- **Commit:** *(pendiente)*

## Capa social — teaser en el home (logo + iconos, post-Etapa A)

Aprobado por el usuario tras revisar plan con 4 decisiones explícitas
(ubicación, gating, superficies, frecuencia) — implementado con los
valores por defecto propuestos, sin objeción.

- **Logo** — `assets/logo_green.png` (raíz, ya protegido) copiado a
  `apps/desktop/src/assets/brand/logo_green.png` (mismo patrón que
  `logo_white.png`/`logo_black.png`), añadido a `.gitattributes` con
  `merge=keepours`. Renderizado en
  `apps/desktop/src/components/chat/intro.tsx`, arriba del wordmark.
- **Iconos de redes** — `apps/desktop/src/app/social/home-teaser.tsx`
  (`SocialHomeTeaser`), fila de 6 iconos reutilizando `NETWORK_ICONS`
  (Bloque 2), envuelta en `PremiumGate` (Bloque 2.4) — mismo gate que el
  panel `/social`, así que free/premium nunca queda inconsistente entre
  las dos superficies. Cada icono navega a `SOCIAL_ROUTE`.
- **Decisiones tomadas** (por defecto, sin objeción del usuario): fila
  debajo del párrafo de bienvenida; gating premium igual que el panel;
  solo en `<Intro>` del chat principal, no en el Kanban vacío (no se
  tocó `plugins/kanban/board.tsx`); se muestra en cada sesión nueva
  vacía, no solo la primera vez (sin bandera persistida).
- **Detalle de implementación no obvio:** el contenedor raíz de
  `<Intro>` es `pointer-events-none` (el resto del componente es
  puramente decorativo) — el wrapper del teaser necesitó
  `pointer-events-auto` explícito para que los iconos sean clicables.
- **Verificado:** `tsc --build` y `eslint` limpios, `npm run build`
  completo, captura real de la ventana de Electron en ejecución (no un
  mock ni una pestaña de navegador suelta) confirmando el render
  correcto — logo + 6 iconos visibles bajo el texto de bienvenida.
- **Commit:** *(pendiente)*

## Fix — `<button>` anidado en `PremiumGate`

Bug real, encontrado en vivo (no en tests): al probar la app corriendo,
la consola de React marcaba `<button> cannot contain a nested <button>`.
`PremiumGate` envolvía su contenido gateado en un `<button>` propio —
pero ese contenido YA incluye botones interactivos en las dos superficies
donde se usa: las acciones Connect/Manage/Reconnect de cada fila en
`app/social/index.tsx`, y los 6 iconos clicables de
`app/social/home-teaser.tsx`. HTML no permite botones anidados; React lo
advierte y el comportamiento de click queda ambiguo entre navegadores.

**Arreglo:** el wrapper exterior de `PremiumGate` pasó de `<button>` a
`<div role="button" tabIndex={0}>` con `onClick`/`onKeyDown` (Enter/
Espacio) propios — mismo contrato de teclado y lector de pantalla, sin
anidar controles interactivos. El contenido interior sigue
`pointer-events-none` cuando el usuario no es premium, así que el único
punto de interacción real sigue siendo el wrapper.
- **Verificado:** `tsc --build` y `eslint` limpios; confirmado en la
  ventana de Electron real que el warning de consola desaparece tras el
  fix (HMR).
- **Commit:** *(pendiente)*
