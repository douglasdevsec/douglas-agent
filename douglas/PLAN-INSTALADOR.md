# Plan — Rebrand del instalador multiplataforma (Windows/macOS/Linux)

**Estado: plan únicamente. Nada de esto se ha ejecutado.** Investigado con
dos pasadas de lectura completas sobre el código real (no supuestos) —
ver hallazgos exactos abajo, con archivo:línea. Cuando digas que arranque,
sigo el orden de la sección 7.

Este documento cierra un pendiente ya anotado explícitamente en
`douglas/README.md` ("Instalador NSIS / identidad `appId` sin resolver" —
"va junto con el renombrado de `hermes-setup` … en la sesión previa a la
primera release pública, no antes"). Esa sesión es esta.

---

## 0. Alcance

Hay **tres mecanismos de instalación** distintos, cada uno con su propia
marca a corregir:

1. **Instalador Tauri** (`apps/bootstrap-installer/`) — el GUI firmado que
   el usuario final descarga y ejecuta. Produce `hermes-setup.exe` en
   Windows (equivalente en macOS/Linux). Es el que **menos** se tocó en la
   Fase 1 — casi todo su texto sigue en Hermes/Nous Research.
2. **electron-builder** (`apps/desktop/package.json`, target del propio
   Douglas Agent.exe/.app/.AppImage) — el que **más** se tocó ya en Fase 1
   (appId, productName, nsis.*, mac.extendInfo, etc.), pero tiene una fuga
   real: un script post-empaquetado reescribe los metadatos del .exe de
   Windows de vuelta a "Hermes"/"Nous Research".
3. **`scripts/install.ps1` / `install.sh` / `install.cmd`** — los scripts
   que el instalador Tauri invoca por debajo, y que un usuario avanzado
   también puede correr solos vía `irm .../install.ps1 | iex`.

---

## 1. Cómo leer la clasificación

Cada hallazgo está etiquetado:

- **TEXTO** — cosmético puro (título de ventana, texto de banner,
  descripción). Cero riesgo de compatibilidad. Cambiar siempre.
- **CLAVE** — identificador (bundle id, nombre de paquete, nombre de
  servicio/LaunchAgent/systemd, URL de clonado). Cambiarlo tiene
  consecuencias reales (instalaciones duplicadas, rutas rotas para
  usuarios existentes, integraciones externas). Necesita tu decisión
  explícita — ver sección 5.
- **RUTA** — nombre de archivo/ejecutable/acceso directo. Alto impacto
  visual, riesgo de compatibilidad bajo-medio (nadie tiene una instalación
  previa real de Douglas Agent con el nombre viejo, según lo ya documentado
  — "antes de la primera release pública").
- **BUG** — no es de branding, es un bug real que encontré investigando
  esto. Lo anoto para que decidas si lo arreglamos en el mismo pase.

---

## 2. Windows

### 2.1 Instalador Tauri (`apps/bootstrap-installer/`)

**`src-tauri/tauri.conf.json`** — prácticamente nada tocado todavía:

| Línea | Campo | Valor actual | Tipo |
|---|---|---|---|
| 3 | `productName` | `"Hermes"` | CLAVE |
| 5 | `identifier` | `"com.nousresearch.hermes.setup"` | CLAVE |
| 16 | `app.windows[0].title` | `"Hermes"` | TEXTO |
| 37 | `bundle.shortDescription` | `"Hermes"` | TEXTO |
| 38 | `bundle.longDescription` | `"Installs Hermes Agent on your machine. Drives scripts/install.ps1…"` | TEXTO |
| 39 | `bundle.publisher` | `"Nous Research"` | TEXTO |
| 40 | `bundle.copyright` | `"Copyright © 2026 Nous Research"` | TEXTO |

No hay bloques `nsis`/`wix`/`msi` en todo el archivo (confirmado, cero
resultados) — Tauri usa su bundler NSIS por defecto sin overrides.

**`src-tauri/src/paths.rs`** — `installer_dest()` (líneas 115-122):

```rust
pub fn installer_dest() -> PathBuf {
    let name = if cfg!(target_os = "windows") { "hermes-setup.exe" } else { "hermes-setup" };
    hermes_home().join(name)
}
```

Solo el nombre de archivo (`hermes-setup.exe`) sigue viejo — **RUTA**. El
directorio donde se escribe (`hermes_home()`) ya es Douglas-aware (mismo
resolver `DOUGLAS_HOME` → `HERMES_HOME` → `%LOCALAPPDATA%\douglas` →
`%LOCALAPPDATA%\hermes` legado documentado en `douglas/README.md`).

**`src-tauri/Cargo.toml`**:

| Línea | Campo | Valor actual | Tipo |
|---|---|---|---|
| 2 | `name` | `"hermes-bootstrap"` | CLAVE (nombre del crate) |
| 4 | `description` | `"Hermes Setup — signed installer that drives scripts/install.ps1"` | TEXTO |
| 5 | `authors` | `["Nous Research <info@nousresearch.com>"]` | TEXTO |
| 14 | `[[bin]] name` | `"Hermes-Setup"` | **RUTA** — este es el que realmente nombra el `.exe` producido, sobreescribe el nombre del paquete |

**`hermes-setup.manifest`** (manifest de Windows, embebido vía `build.rs`):
`assemblyIdentity name="NousResearch.Hermes.Setup"` (CLAVE),
`<description>Hermes Setup</description>` (TEXTO).

**Iconos** (`src-tauri/icons/`): ya confirmados correctos de la Fase 1 —
`128x128.png`, `128x128@2x.png`, `32x32.png`, `icon.icns`, `icon.ico`. Sin
trabajo pendiente aquí.

**Frontend (`apps/bootstrap-installer/src/`)** — todo TEXTO, nada de esto
es identificador:

| Archivo:línea | Texto actual |
|---|---|
| `index.html:6` | `<title>Hermes</title>` |
| `routes/welcome.tsx:34,36` | `"HERMES AGENT"` (wordmark visible + duplicado `aria-hidden`) |
| `routes/success.tsx:51,53` | `"Hermes is ready"` (visible + `aria-hidden`) |
| `routes/success.tsx:58` | texto que menciona el comando `hermes desktop` |
| `routes/progress.tsx:53,56,57` | `"Updating Hermes"`, `"Setting up Hermes Agent"`, `"Hermes is updating…"`, `"The Hermes installer is downloading…"` |
| `store.ts:392` | label de paso `"Hermes repository"` |
| `package.json:2,5` | `"name": "@hermes/bootstrap-installer"` (CLAVE, nombre de paquete npm interno, no publicado), descripción `"Hermes Setup — signed installer…"` (TEXTO) |
| `styles.css` | clases `hermes-fade-in`/`hermes-glow` — no visibles al usuario, cosmético solo para quien lee el código |

`brand-mark.tsx` ya usa `logo_white.png` (confirmado en Fase 1, sin
pendiente).

### 2.2 electron-builder / NSIS (`apps/desktop/package.json`)

El bloque `build` **ya está mayormente rebrandeado**: `appId`,
`productName`, `executableName`, `artifactName`, `nsis.shortcutName`,
`nsis.uninstallDisplayName`, `win.legalTrademarks` — todos dicen ya
"Douglas Agent" / `com.douglasdevsec.douglas-agent`. Sin bloques `.nsh`/
`.nsi`/`.wxs` custom en todo el repo (confirmado, cero resultados).

**Pero hay una fuga real**: `apps/desktop/scripts/set-exe-identity.mjs`
(hook `afterPack`, corre en cada build empaquetado de Windows, INCLUYENDO
el instalador) escribe directamente en los recursos PE del `.exe` — esto
es lo que ve un usuario en **clic derecho → Propiedades → Detalles** en el
Explorador de Windows:

```js
// líneas 64-69
'version-string': {
  ProductName: 'Hermes',
  FileDescription: 'Hermes',
  CompanyName: 'Nous Research',
  LegalCopyright: 'Copyright (c) 2026 Nous Research'
}
```

**Este es probablemente el hallazgo más importante de todo el plan** — es
el punto donde alguien revisa las propiedades del archivo del instalador y
ve "Hermes"/"Nous Research" pese a que el `productName` de package.json ya
dice Douglas Agent. TEXTO, pero de máxima visibilidad.

`before-pack.mjs:95,121` tiene un *fallback* `'Hermes.exe'`/`'Hermes'`
usado solo si `packager.appInfo.productFilename` no está disponible —
riesgo bajo, ya no debería activarse con `productName` corregido, pero
vale la pena corregir el literal igual por higiene.

### 2.3 `scripts/install.ps1` / `install.cmd`

| Línea(s) | Contenido | Tipo |
|---|---|---|
| 213-221 (`Write-Banner`) | `"* Hermes Agent Installer"`, `"An open source AI agent by Nous Research."` | TEXTO |
| 145-146 | `$RepoUrlSsh`/`$RepoUrlHttps` → `NousResearch/hermes-agent.git` | **CLAVE — ver sección 5, punto crítico** |
| 32 | `$HermesHome` (nombre de variable) por defecto `$env:LOCALAPPDATA\hermes` | RUTA/CLAVE — ver sección 5 |
| 3116-3117 | `$exeCandidates` busca literalmente `win-unpacked\Hermes.exe` / `win-arm64-unpacked\Hermes.exe` | **BUG** — ver sección 6 |
| 3167-3226 (`New-DesktopShortcuts`) | accesos directos `Programs\Hermes.lnk`, `Desktop\Hermes.lnk`, descripción `'Hermes Agent'` | RUTA + TEXTO |
| `install.cmd` líneas 3,8,11,15,19,24 | banner `"Hermes Agent Installer"` + URLs `hermes-agent.nousresearch.com` | TEXTO + CLAVE (URL) |

---

## 3. macOS

### 3.1 electron-builder

Ya rebrandeado en su mayoría: `mac.extendInfo.CFBundleDisplayName/
Executable/Name` = "Douglas Agent", entitlements (`entitlements.mac.plist`,
`entitlements.mac.inherit.plist`) sin ningún "Hermes". `dmg.title:
"Install Douglas Agent"` ya correcto. **No existe imagen de fondo para el
DMG** (solo `backgroundColor`) — nada que rehacer ahí.

`scripts/notarize.mjs:38` y `notarize-artifact.mjs:37` usan un prefijo de
archivo temporal `hermes-notary-${Date.now()}-${pid}.p8` — identificador
interno de bajo riesgo, nunca visible al usuario, pero cambiable por
prolijidad (TEXTO/interno).

**BUG, no branding:** `apps/desktop/scripts/test-desktop.mjs` (líneas
22-29, 127, 130, 144, 148) sigue buscando `Hermes.app`, el binario
`Contents/MacOS/Hermes`, y una plantilla de nombre de DMG
`Hermes-${version}-${arch}.dmg` — **ya no coincide** con el
`productName`/`artifactName` reales (`Douglas Agent.app`,
`DouglasAgent-${version}-${os}-${arch}.dmg`). Este script de verificación
está roto ahora mismo, no encontraría un build real. Ver sección 6.

### 3.2 Instalador Tauri — mismo archivo que 2.1, comparte config

`tauri.conf.json` es compartido entre plataformas — todo lo listado en
2.1 (`productName`, `identifier`, `title`, descripciones, `publisher`,
`copyright`) aplica igual a macOS. `bundle.macOS` (líneas 58-61) solo trae
`minimumSystemVersion` + `hardenedRuntime` — sin bloque de estilo de DMG
propio de Tauri, nada de branding adicional ahí. Sin Info.plist ni
entitlements propios bajo `src-tauri/` (confirmado, no existen).

`Cargo.toml`: el mismo `[[bin]] name = "Hermes-Setup"` produce el binario
en macOS/Linux también — no es solo cosa de Windows.

### 3.3 `scripts/install.sh`

| Línea(s) | Contenido | Tipo |
|---|---|---|
| 211-220 (`print_banner`) | mismo texto que install.ps1 | TEXTO |
| 48 | `HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"` | RUTA/CLAVE — ver sección 5 |

**No escribe un LaunchAgent directamente** — delega a `hermes gateway
install` (línea 2474), implementado en `hermes_cli/gateway.py`:

- `get_launchd_plist_path()` (2481-2489): escribe
  `~/Library/LaunchAgents/ai.hermes.gateway.plist` — el docstring dice
  explícitamente **"backward compatible"**. **CLAVE de alto riesgo si se
  toca** — ver sección 5.
- `SERVICE_DESCRIPTION = "Hermes Agent Gateway - Messaging Platform
  Integration"` (`gateway.py:1724`) — TEXTO, va dentro del plist generado
  pero es solo la descripción, no el identificador del servicio.

---

## 4. Linux

### 4.1 electron-builder

`build.linux` (líneas 257-266): `maintainer: "Douglas DevSec
<dpdesign27@gmail.com>"` ya correcto. Pero:

```
synopsis: "Agente de creación y publicación de contenido, construido sobre Hermes Agent (MIT)."
```

Esto **probablemente es intencional** — coincide con la regla 7 del
contrato de compatibilidad ("atribución visible… nunca usar la marca
Hermes… en superficies de producto" — pero la atribución MIT en sí SÍ
debe existir en algún lado). Lo marco como decisión, no como bug — ver
sección 5.

No existe plantilla `.desktop` en todo el repo (confirmado, glob vacío) —
el `.desktop` de AppImage/deb se genera automáticamente desde
`productName`/`description`/`executableName`, ya correctos.

`protocols[0]` sigue registrando el esquema `"hermes"` junto a `"douglas"`
(`package.json:173`) — **intencional para compatibilidad**, no tocar sin
decidirlo explícitamente (mismo principio que `hermes`/`douglas` como
comando CLI).

### 4.2 Instalador Tauri

No hay sección `bundle.linux` en `tauri.conf.json` — el target AppImage
hereda `productName`/`identifier`/descripciones/`publisher`/`copyright`
del bloque compartido (sección 2.1), sin nada adicional específico de
Linux.

### 4.3 `scripts/install.sh` — parte Linux

| Línea(s) | Contenido | Tipo |
|---|---|---|
| 46-47 | `REPO_URL_SSH`/`REPO_URL_HTTPS` → `NousResearch/hermes-agent.git` | **CLAVE — mismo punto crítico que 2.3** |
| 9 (comentario) | `curl -fsSL https://hermes-agent.nousresearch.com/install.sh \| bash` | CLAVE (URL de distribución) |
| 415, 424, 447 | `INSTALL_DIR` por defecto `~/.hermes/hermes-agent` | RUTA/CLAVE |
| 181-182, 429 | instalación root Linux `/usr/local/lib/hermes-agent` | RUTA/CLAVE |
| 1725-1758 (via `gateway.py`) | lanzadores `hermes`, `hermes-agent`, `hermes-acp` escritos al PATH | **CLAVE de alto riesgo — mantener, regla 5 del contrato ya lo exige** |
| 2809-2810, 2852-2853 (`gateway.py`) | unidad systemd, mismo `SERVICE_DESCRIPTION` que macOS | TEXTO (descripción) / CLAVE (nombre de unidad, no confirmado el literal exacto — revisar antes de tocar) |

---

## 5. Decisiones que necesito que tomes (no elijo por ti — regla 6 del contrato)

### 5.1 — Crítico: ¿de qué repo clona el instalador?

`install.ps1`/`install.sh`/`install.cmd` clonan
`NousResearch/hermes-agent.git` — el repo original, no tu fork. **Esto no
es solo branding: si no se cambia, un usuario que instale "Douglas Agent"
vía tu instalador termina con el código puro de Hermes, sin ninguno de tus
cambios.** Necesito que confirmes:

- ¿El instalador debe clonar `douglasdevsec/douglas-agent` (tu fork en
  GitHub, el mismo que ya usas como `origin`)?
- ¿Ese repo es público? Si es privado, el instalador necesitará un token o
  no funcionará para usuarios externos.
- ¿Existe ya un dominio/URL de distribución propio (algo como
  `install.douglasdevsec.com` o similar), o seguimos usando GitHub
  directo (`raw.githubusercontent.com/douglasdevsec/douglas-agent/...`)
  hasta que exista uno?

### 5.2 — `hermes-setup.exe` / `Hermes-Setup` → ¿renombrar del todo?

Dado que (confirmado por ti en sesiones anteriores) **todavía no hay
release pública** — nadie tiene un acceso directo o script apuntando al
nombre viejo — el riesgo de renombrar es bajo. Propongo:
`douglas-setup.exe` / `Douglas-Setup` (Cargo.toml `[[bin]]` + `paths.rs`).
¿Confirmas, o prefieres otro nombre?

### 5.3 — Identificador de bundle Tauri (`com.nousresearch.hermes.setup`)

Mismo problema que ya documentado para electron-builder (appId duplicado
si cambia después de que existan instalaciones reales) — pero como el
punto 5.2, **antes de la primera release pública** es el momento de
hacerlo sin costo. Propongo `com.douglasdevsec.douglas-agent.setup`
(paralelo al `com.douglasdevsec.douglas-agent` que ya usa electron-builder).
¿Confirmas?

### 5.4 — Nombre legal en `CompanyName`/`publisher`/`copyright`

`set-exe-identity.mjs`, `tauri.conf.json`, y varios `copyright` strings
van a decir "DouglasDevSec". ¿Ese es el nombre exacto que quieres en los
metadatos legales del ejecutable (Propiedades de Windows, notarización de
macOS), o hay una razón social distinta que deba aparecer ahí? Si en algún
momento firmas el ejecutable con un certificado de code-signing, el nombre
del certificado y el `CompanyName` deberían coincidir o Windows SmartScreen
puede marcarlo como sospechoso.

### 5.5 — Atribución MIT en el `synopsis` de Linux

`synopsis: "…construido sobre Hermes Agent (MIT)."` — esto puede ser la
atribución legal requerida (regla 7: LICENSE/NOTICE + atribución visible),
no un descuido. Propongo mantenerla pero reformularla para que quede claro
que es atribución, no la marca del producto — por ejemplo: *"Agente de
creación y publicación de contenido. Basado en Hermes Agent (MIT) —
atribución completa en el LICENSE."* ¿Te sirve esa redacción, o prefieres
mover la atribución MIT a otro lado (el NOTICE/LICENSE, la pantalla
"Acerca de") y sacarla de aquí?

### 5.6 — Identificadores que la regla 5 del contrato ya exige mantener (confirmo, no pregunto)

Estos **NO se tocan** — ya están cubiertos por "compatibilidad hacia atrás
obligatoria" en `douglas/README.md`:
- `~/.hermes` / `%LOCALAPPDATA%\hermes` como fallback de `HERMES_HOME`.
- `ai.hermes.gateway.plist` (LaunchAgent macOS) — docstring dice
  "backward compatible" explícitamente.
- Comandos `hermes`/`hermes-agent`/`hermes-acp` en el PATH de Linux/macOS.
- Esquema de protocolo `hermes://` junto a `douglas://`.

---

## 6. Bugs reales encontrados (no son branding — decide si los arreglamos en el mismo pase)

1. **`install.ps1:3116-3117`** — busca `win-unpacked\Hermes.exe`, pero el
   build real ahora produce `Douglas Agent.exe`. Es muy probable que esta
   parte del script **ya esté rota** — el instalador no encontraría el
   ejecutable recién compilado. Se arregla solo (cambiar el literal), pero
   vale la pena probarlo de verdad cuando compilemos.
2. **`apps/desktop/scripts/test-desktop.mjs`** — script de verificación de
   macOS roto por el mismo motivo (busca `Hermes.app`/`Hermes-*.dmg`, ya
   no existen con esos nombres). No bloquea Windows, pero si algún día se
   prueba en macOS, fallará hasta que se corrija.

---

## 7. Orden de ejecución propuesto (para cuando digas)

1. Confirmar las 5 decisiones de la sección 5 (en particular 5.1 — es la
   que más cambia el comportamiento real, no solo la cosmética).
2. **Fase TEXTO** (sin riesgo, un solo pase): todos los strings cosméticos
   listados como TEXTO en las secciones 2-4 — Tauri (`tauri.conf.json`,
   frontend completo), `set-exe-identity.mjs`, banners de
   `install.ps1`/`install.sh`/`install.cmd`, `synopsis` de Linux (según
   5.5).
3. **Fase CLAVE/RUTA** (según lo decidido en sección 5): renombrar
   `hermes-setup.exe`/`Hermes-Setup`, el `identifier` de Tauri, y — la más
   importante — las URLs de clonado si confirmas 5.1.
4. **Fase BUG**: corregir `install.ps1`'s `$exeCandidates` y
   `test-desktop.mjs` (aunque este último no se pueda probar sin macOS).
5. Commit agrupado por intención (varios commits, no uno solo — mismo
   patrón que el resto de la Fase 2), documentado en
   `douglas/CORE_PATCHES.md`.
6. **Recién ahí** — compilación real y prueba en Windows, como pediste.

## 8. Plan de verificación cuando compilemos en Windows

- `cd apps/bootstrap-installer && npm run tauri build` (o el comando
  equivalente que use este repo — confirmar el script exacto en
  `package.json` antes de correrlo) para producir el instalador Tauri real.
- Verificar en el `.exe` resultante: clic derecho → Propiedades → Detalles
  → debe decir "Douglas Agent" / "DouglasDevSec", no "Hermes"/"Nous
  Research".
- Correr el instalador de punta a punta en esta máquina (o una VM/usuario
  limpio si es posible) — pantallas de bienvenida, progreso, éxito, todas
  en Douglas.
- Confirmar que clona el repo correcto (según 5.1) y que el `douglas-agent`
  resultante en `%LOCALAPPDATA%\douglas\hermes-agent` (o donde resuelva)
  tiene el código de tu fork, no el de NousResearch puro.
- `npm run pack`/`npm run dist:win` en `apps/desktop/` para el instalador
  NSIS del propio Douglas Agent — mismo chequeo de Propiedades del archivo.
- Confirmar accesos directos de Start Menu/Escritorio con el nombre e
  ícono correctos.
- Desinstalar y confirmar que "Agregar o quitar programas" también dice
  Douglas Agent.

## 9. Lo que no se puede verificar sin hardware macOS/Linux

Igual que el resto de este proyecto (ya documentado en "Verificar en
hardware real" de `douglas/README.md`): el DMG de macOS, el `.app`
resultante, la notarización, el LaunchAgent, y el AppImage/deb/rpm de
Linux solo se pueden revisar por código desde esta máquina Windows — no se
pueden compilar ni probar aquí. Quedan como pendiente para cuando haya
acceso a esas plataformas, igual que el resto de los ítems ya anotados en
esa sección.
