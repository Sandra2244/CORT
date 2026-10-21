# C.O.R.T. — Cognitive Orchestrator / Real-Time

<p align="center">
  <img src="https://img.shields.io/badge/versión-v0.2.0-00bfff?style=for-the-badge&logo=semanticrelease&logoColor=white" alt="versión 0.2.0">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Three.js-orbe%203D-F5871F?style=for-the-badge&logo=threedotjs&logoColor=white" alt="Three.js">
  <img src="https://img.shields.io/badge/Electron-ventana%20HUD-47848F?style=for-the-badge&logo=electron&logoColor=white" alt="Electron">
</p>

<p align="center">
  <a href="https://github.com/Sandra2244/CORT/releases/tag/v0.2.7-demo"><img src="https://img.shields.io/badge/Descargar-v0.2.7--demo-blueviolet?style=flat-square&logo=github&logoColor=white" alt="Descargar Release v0.2.7-demo"></a>
  <a href="https://github.com/Sandra2244/CORT/tree/v0.2-demo"><img src="https://img.shields.io/badge/rama-v0.2--demo-orange?style=flat-square&logo=git&logoColor=white" alt="rama v0.2-demo"></a>
  <img src="https://img.shields.io/badge/Windows-soportado-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/Linux-soportado-FCC624?style=flat-square&logo=linux&logoColor=black" alt="Linux">
  <img src="https://img.shields.io/badge/macOS-soportado-000000?style=flat-square&logo=apple&logoColor=white" alt="macOS">
  <img src="https://img.shields.io/badge/Android-APK-3DDC84?style=flat-square&logo=android&logoColor=black" alt="Android">
  <img src="https://img.shields.io/badge/cerebro-híbrido%20(local%20%2B%20online)-9cf?style=flat-square" alt="cerebro híbrido">
  <img src="https://img.shields.io/badge/100%25-gratuito-2ecc71?style=flat-square" alt="100% gratuito">
  <img src="https://img.shields.io/badge/sin%20nube%20%2B%20sin%20telemetría-privado%20por%20diseño-e91e63?style=flat-square" alt="sin telemetría">
  <img src="https://img.shields.io/badge/licencia-MIT-yellow?style=flat-square" alt="licencia MIT">
</p>

Asistente personal holográfico inspirado en JARVIS (Iron Man) y Cortana (Halo):
un **orbe de partículas 3D** que escucha, responde con voz, abre tus archivos,
reproduce música y ejecuta acciones del sistema. El **cerebro es híbrido**: usa
IA local (Ollama), IA online gratuita (Groq / Gemini) o ambas, y si no hay
ninguna clave sigue siendo útil con comandos propios y modo sin conexión.

![Pantalla real de C.O.R.T.](docs/screenshots/holograma.png)

![C.O.R.T. en el escritorio de Linux](docs/screenshots/escritorio-linux.png)

---

## Qué hace hoy (todo probado en esta rama)

| | Función | Detalle |
|---|---|---|
| 🗣 | **Voz y oído** | Micrófono y voz con la Web Speech API (gratis, sin instalar nada) + palabra de activación «Oye CORT» opcional |
| 🧠 | **Cerebro híbrido** | Enrutador `local → Groq → Gemini → modo supervivencia`; ventana **07 · Perfil** para pegar claves (se muestran en máscara) y botón que **prueba cada proveedor** con latencia en ms |
| 🌐 | **Orbe 3D** | Plexus de partículas con desenfoque de cine (bokeh real), estallido → vórtice → portal toroidal al ejecutar una orden, y anillo giratorio sincronizado con el bajo cuando suena música |
| 🪟 | **11 ventanas de vidrio** | `01 Archivos · 02 Entorno · 03 Canal de voz · 04 Notas · 05 Música · 06 Consola · 07 Perfil · 08 Cerebro · 09 Ayuda · 10 Modelos · 11 Optimizar` — arrastrables, minimizables al dock, con contadores en vivo |
| 👥 | **Modelos locales (Ollama)** | **10 · Modelos** enseña 14 modelos con su peso real, su flecha `↓ descargar` y el veredicto para **la RAM de este equipo** (`VA BIEN · JUSTO · NO CABE`): barra de progreso al 1 %, `usar`, `✕ borrar` y botón para encender o apagar Ollama |
| 🧹 | **Optimización del equipo** | **11 · Optimizar** mide la RAM en vivo, quién se la come (con botón para cerrar procesos propios), cuánta caché sobra y barre la segura — sin tocar documentos, la papelera ni el escritorio |
| ⌨ | **Consola de comandos** | Prompt `cort@nave:~$`, historial con ↑/↓ y **Tab que completa** («repro» → «reproduce») |
| 📂 | **Archivos seguros** | Árbol lateral con doble conteo (carpetas · archivos) que se expande, vista rejilla/lista y botón **Abrir** que lanza la carpeta en el explorador del sistema |
| 🎵 | **Música** | Escanea `~/Música`, reproduce en el panel o abre tu reproductor (VLC) con «reproduce música» |
| 📝 | **Notas, pendientes y memoria** | «apunta …» guarda una nota; «tengo que comprar aceite» guarda una pendiente y «listo 1» la marca como hecha; **08 · Cerebro** muestra el muro de recuerdos enmarcados (notas + conversaciones) |
| 🔊 | **Te lo lee en voz alta** | «lee mis notas» · «lee mis tareas» · «lee el documento recibo» · «lee mis avisos». En el PC lo lee del backend (notas, pendientes y textos de tus carpetas seguras); en el teléfono `CORT-IA-1.2.2-asistente.apk` lee el **centro de notificaciones** — WhatsApp, Gmail, Telegram, Signal — con un oído que guarda doce líneas en RAM y se borran solas: nunca se escriben a disco |
| 📊 | **Sensores** | CPU / RAM / disco / batería reales y clima actual (Open-Meteo, cacheado, sin API key) |
| ✋ | **Gestos** | MediaPipe ligero: palma despliega/plega ventanas, pinza trae el chat, puño las cierra |
| 💡 | **Lámpara de estado** | Morado escuchando · naranja procesando · verde en línea · gris con el HUD oculto · rojo sin backend |
| 📱 | **APK del teléfono** | dos en la Release: el cuerpo original con la interfaz de hoy dentro, y el escrito aquí con asistente del sistema, doble toque de auriculares y lectura de avisos (`apps/apk/`) |
| 📡 | **Modo teléfono** | `bash scripts/telefono.sh` enlaza la Wi-Fi y el celular abre el holograma actual en `http://IP-del-PC:8000` |
| ⏻ | **Arranque BIOS** | Secuencia de encendido que comprueba en vivo cada subsistema y el puerto donde vive el núcleo |

Atajo de teclado: **Esc** oculta o devuelve todas las ventanas (deja solo el orbe).

---

## Arquitectura

```
┌───────────────── Interfaz (ui/) ─────────────────────────────────────────┐
│  Three.js: orbe de partículas + portal     11 ventanas de vidrio + dock  │
│  Web Speech: micrófono y voz                 MediaPipe: gestos (opt-in)  │
│  Auto-descubre el núcleo: localhost:8000 → 8080 → puente Android         │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │  HTTP 127.0.0.1:8000  (un solo puerto)
┌──────────────────────────┴───────────────────────────────────────────────┐
│  Backend Python · FastAPI (backend/app/)                                 │
│  main.py ─ API + reparte la interfaz con CORT_SERVE_UI=1                 │
│  actions.py ─ «abre / lanza / reproduce / apunta» → acciones del sistema │
│  brain.py ─ enrutador híbrido: local → Groq → Gemini → supervivencia     │
│  models.py ─ catálogo de Ollama, veredicto de RAM y descargas en hilo    │
│  optimize.py ─ RAM en vivo, procesos pesados y caché borrable (seguro)   │
│  config_store.py ─ ajustes y claves (archivo JSON, se leen al vuelo)     │
│  sensors.py ─ archivos seguros + apertura con visor del sistema + clima  │
│  memory.py ─ SQLite (notas, conversaciones, preferencias)                │
└──────────────────────────────────────────────────────────────────────────┘
```

**Un solo proceso, un solo puerto.** Con `CORT_SERVE_UI=1` el backend reparte
también el holograma, así que `http://localhost:8000` es a la vez la interfaz y
la API: nada que configurar y ningún puerto expuesto a internet.

---

## Instalación

### 1 · Requisitos

- **Python 3.10 o más nuevo**
- **Chrome o Edge** (por el micrófono y la voz del sistema)
- Nada más: las dependencias se instalan solas en un `venv` del proyecto.

### 2 · Obtener el código

```bash
git clone -b v0.2-demo https://github.com/Sandra2244/CORT.git
```

o descarga el ZIP de esta rama (`Code ▸ Download ZIP`) y descomprime.

### 3 · Arrancar

| Sistema | Comando | Se abre en |
|---|---|---|
| **Linux / macOS** | `bash scripts/run.sh` | `http://localhost:8000` (lo abre solo) |
| **Windows** | doble clic en `scripts\run.bat` | `http://localhost:8000` |
| **Ventana holográfica (Electron)** | `bash scripts/run-desktop.sh` | ventana sin marco, modo cabina |
| **Linux, instalado como app** | `bash scripts/instalar-linux.sh` | icono en `~/Escritorio/CORT.desktop` (extrae el AppImage sin sudo) |
| **Android (APK del teléfono)** | instala [`CORT-IA-1.1.3.apk`](https://github.com/Sandra2244/CORT/releases/latest) | tu CORT de siempre (mismo icono, misma cara) con las once ventanas nuevas dentro |
| **Teléfono en la misma Wi-Fi** | `bash scripts/telefono.sh` | `http://IP-de-tu-PC:8000` desde el navegador del celular |

> ¿El puerto 8000 está ocupado? `CORT_PORT=8090 bash scripts/run.sh`
> (en Windows: `set CORT_PORT=8090` antes de `scripts\run.bat`). La interfaz
> encuentra sola el puerto nuevo.

### 4 · Activar el cerebro conversacional (opcional)

Sin claves, CORT ya responde con comandos locales, clima, archivos, música y
memoria. Para conversación libre elige una de estas dos vías:

- **Desde la propia interfaz** (recomendado): abre **07 · Perfil**, pega la
  clave en `Groq` o `Gemini` y pulsa **Guardar**. Pulsa **Probar cerebro** para
  ver cuál responde más rápido. Las claves se quedan en tu equipo.
  - Groq (gratis, muy rápido): <https://console.groq.com/keys>
  - Gemini (gratis): <https://aistudio.google.com/apikey>
- **Por archivo**: copia `backend/.env.example` a `backend/.env` y rellena
  `GROQ_API_KEY` / `GEMINI_API_KEY`.

**IA local** (solo equipos con 8 GB+ de RAM): instala [Ollama](https://ollama.com),
ejecuta `ollama pull qwen2.5:3b` y CORT lo detecta solo. En equipos modestos
deja `CORT_MODE=online` o `auto`; **no** instales Ollama si tu PC tiene poca RAM.

El modo se fuerza con `CORT_MODE` (`.env`) o desde **Perfil**: `auto`, `local`,
`online`, `offline`.

### 5 · Descargas ya compiladas

La [Release v0.2.7-demo](https://github.com/Sandra2244/CORT/releases/tag/v0.2.7-demo)
tiene los instaladores generados por GitHub Actions (nunca se compilan en tu PC,
que para eso hace falta un equipo sobrado):

| Archivo | Para | Peso |
|---|---|---|
| `CORT.Setup.0.2.0.exe` | Windows 10/11 64 bits (instalador NSIS, eliges carpeta) | 79,0 MB |
| `CORT-0.2.0.AppImage` | Linux genérico (ejecutable directo) | 107,5 MB |
| `cort-desktop_0.2.0_amd64.deb` | Debian / Ubuntu / Mint | 74,7 MB |
| `CORT-IA-1.1.3.apk` | Android 8+ (ocho o más): **el APK original con la interfaz actual dentro** | ~1,75 MB (el peso real sale en la Release) |
| `CORT-IA-1.2.2-asistente.apk` | Android 8+: el escrito desde aquí — asistente predeterminado, doble toque del auricular y lee tus avisos en voz alta | ~370 KB |
| `CORT-IA-1.1.3-firma.txt` · `CORT-IA-1.2.2-firma.txt` | con qué llave salió cada uno y qué lleva dentro (prueba pública) | texto |

> El instalador de escritorio abre el mismo backend de Python: sigue necesitando
> Python 3.10+ en el equipo, y la primera vez puede tardar unos segundos en
> arrancar mientras crea su entorno.

### 6 · CORT en el teléfono

En el repo hay **dos** cosas que producen APK, y hacen cosas distintas:

| APK | Qué es | Dónde está |
|---|---|---|
| `CORT-IA-1.1.3.apk` | **El tuyo de siempre, actualizado.** El cuerpo es el binario original `CORT-IA-1.1.0` (`com.cort.ia`, Kotlin, cuatro `classes.dex`, su icono de anillo adaptativo, `ListenService`, permisos de archivos/audio/almacenamiento) y lo único que se le cambia es la interfaz que lleva dentro: `assets/ui/` se sustituye por `ui/` de este commit. Después se realinea (`zipalign`) y se refirma (`apksigner`), porque tocar un entry rompe la firma vieja. **No puede leer los avisos del teléfono**: ese puente lo trae sólo el de abajo, y la cara se disculpa con una frase en vez de romperse. | `apps/apk/rempaquetar.sh` → la Release |
| `CORT-IA-1.2.2-asistente.apk` | **El experimental escrito desde cero aquí**: Java puro sin Gradle (`apps/apk/compilar.sh`), con el holograma del repo embebido bajo `https://cort.local`, puente de voz propio (`CortNative.java`), traje de `VoiceInteractionService` para **ser el asistente predeterminado**, `MediaSession` para el **doble toque del auricular** y el servicio `Avisos` (`NotificationListenerService`) que **lee en voz alta lo que llega por WhatsApp, Gmail, Telegram o Signal**. Pesa ~370 KB porque es otra app: no lleva el Kotlin de archivos/apps/almacenamiento del original. | `apps/apk/compilar.sh` → la Release |

Por qué el del teléfono se rempaqueta y no se recompila: **el proyecto Gradle que
generó el 1.1.0 no está en este repo** — lo que se guardó siempre fue el binario
(`instaladores/CORT-IA-1.1.0.apk`, 1.815.389 bytes, comprobado byte a byte contra
la copia del Escritorio: mismo SHA-256 `b5fa07fa…`). Sin ese proyecto no hay forma
de recompilar su Kotlin en Actions; con el binario sí se le puede cambiar la cara,
que es lo que importa cuando lo que mejora es la interfaz.

Lo que se verificó antes de meter la mano (diff real entre los `assets/ui/` del
binario y `ui/` del repo): `android-bridge.js`, `voice.js`, `orb.js`,
`gestures.js`, `windows.js` y `vendor/three.module.js` son **idénticos byte a
byte**; sólo difieren `hud.js`, `index.html`, `hud.css` e `icons.js` (las ventanas
10 · Modelos y 11 · Optimizar). Y la superficie del puente nativo que la cara
llama **en el teléfono** sigue siendo la de siempre (`CortNative.listen`,
`stopListening`, `bgStatus`, `setBackground`, `keepAwake`), así que el Kotlin de
dentro entiende el JavaScript nuevo. El método nuevo —`CortNative.avisos()`—
**no existe en ese Kotlin**: por eso la cara comprueba
`typeof N.avisos !== 'function'` antes de llamarlo y, si no está, lo dice con
una frase en vez de reventar con un `TypeError`. La versión que aparece en
Ajustes ▸ Aplicaciones seguirá siendo **1.1.0**: el `versionName` vive en el
manifiesto binario y reescribirlo sin el proyecto original no se puede hacer aquí.

Lo que el del teléfono **no** trae, dicho sin adornos:

- **No puede ser el asistente predeterminado, ni escuchar el doble toque del
  auricular, ni leer tus avisos en voz alta.** Las tres cosas exigen tocar su
  `AndroidManifest` (añadir `BIND_VOICE_INTERACTION`, `res/xml/asistente.xml` y
  el servicio de `BIND_NOTIFICATION_LISTENER_SERVICE`) y su código Java, y en un
  binario compilado por fuera no se puede editar. Viven en el APK experimental
  de la tabla de arriba, que desde `v0.2.8-demo` **también se publica en la
  Release** para que se pueda bajar con un clic sin entrar a los artefactos del
  run.
- **Leer los avisos pide un interruptor a mano, una vez.** En
  `CORT-IA-1.2.2-asistente.apk` abre el menú (el botón `☰`) y toca «Dar el
  permiso de los avisos», o ve a Ajustes ▸ Notificaciones ▸ Acceso de
  notificación y activa CORT. Es el mismo interruptor que usan las apps de
  recordatorios: sin él CORT no ve la barra, y el menú te lo recuerda escribiendo
  «pendiente». Lo que sí ve sin permiso: tus notas, tus pendientes y tus
  documentos, porque eso lo contesta el backend del PC cuando estás conectado
  por Wi-Fi.
- Las ventanas 10 · Modelos y 11 · Optimizar necesitan el backend del portátil:
  sin PC muestran el aviso de «sin PC» en vez de datos, porque piden `/api/*`.
  Lo mismo pasa con «lee mis notas» o «lee mis tareas» a pelo: la cara traduce
  el 501 del teléfono y lo dice en voz alta en lugar de quedarse callada.
- **Hasta `v0.2.8-demo` había que desinstalar cada vez que se actualizaba el APK**,
  porque cada run firmaba con una llave desechable distinta, y para Android una
  firma distinta es otra aplicación. Al desinstalar se iba todo lo concedido a
  mano: el micrófono, el doble toque, el permiso de los avisos y la dirección del
  PC. Desde esta ronda la llave **es siempre la misma** (`apps/apk/llave.sh`):
  manda el secreto `CORT_APK_KEYSTORE_B64` si algún día existe; si no, el pipeline
  reutiliza la llave que guardó en su caché de Actions (`apps/apk/keystore`, paso
  «Cachear la llave de firma»), y la primera vez que no hay ninguna la genera y la
  deja ahí. **Ésta es la última actualización que pide desinstalar.** Comprobación
  pública: la huella SHA-256 del certificado sale en el `-firma.txt` de cada APK y
  como anotación del check-run; dos Releases seguidas con la misma huella = la
  llave se mantuvo. La llave nunca se sube al repo (está en `.gitignore`, y el
  repo es público).
- **Tus claves de Groq/Gemini tampoco se pierden ya al actualizar el
  instalador.** `cort_config.json` y `cort_memory.db` (las notas, los recuerdos y
  las pendientes) vivían dentro de `backend/`, o sea dentro de la carpeta que el
  `.exe`, el AppImage o el `.deb` sustituyen. Ahora viven en la carpeta personal —
  `~/.cort/` en Linux y macOS, `%APPDATA%\CORT\` en Windows, o donde diga
  `CORT_HOME` — y la primera arrancada copia ahí lo que hubiera antes (copia, no
  movimiento: el archivo viejo se queda por si algo se tuerce). **07 · Perfil**
  muestra la ruta, para que se vea con los ojos. Lo comprobado aquí:
  `scripts/prueba-datos.py`, en un `mktemp`, sin tocar tus archivos reales.
- Nada de esto está probado con un dedo encima: en esta máquina no hay teléfono.
  Lo que sí comprueba el pipeline es que el APK rempaquetado conserva los cuatro
  `classes.dex` y los 17 archivos de `mipmap`, que `zipalign` pasa y que
  `apksigner verify` acepta la firma.
- **El `CORT-IA-1.1.1.apk` de la Release anterior (1.752.631 bytes) se comparó
  entrada por entrada contra el 1.1.0 original**, descargando los dos: entran tres archivos
  de firma (`META-INF/CORT.SF`, `.RSA`, `MANIFEST.MF`), sale uno
  (`app-metadata.properties`) y **ninguna otra entrada cambia de contenido** —
  los cuatro `classes.dex`, los siete `kotlin/*`, los 17 `mipmap` y
  `resources.arsc` son byte a byte los del APK de siempre. Los 11 archivos de
  `assets/ui/` que entran son byte a byte el `ui/` del commit. O sea: cuerpo
  original intacto, cara actualizada, icono original intacto.

El **modo teléfono sin instalar nada** sigue disponible para ver la cara actual
en el navegador del celular: `bash scripts/telefono.sh` (igual que `run.sh`, pero
enlazado a la red) y abres `http://IP-de-tu-PC:8000`. Comprado en tu equipo: la
página y `/api/models` responden por la red local (200 OK). Su límite es el
micrófono: por `http` no habla ni escucha; para eso está el APK.

Para regenerarlos con código nuevo, sube una etiqueta (el sufijo `-demo` es para
no chocar con las `v0.x` que ya usa el historial de la app de Android):

```bash
git tag -a v0.2.7-demo -m "CORT" && git push origin v0.2.7-demo   # ← dispara la compilación
```

También a mano: **Actions ▸ Construir instaladores CORT ▸ Run workflow**.

---

## API (localhost, sin autenticación porque no sale de tu equipo)

| Método y ruta | Para qué |
|---|---|
| `POST /api/chat` | `{message}` → `{reply, source}`: respuesta del cerebro |
| `POST /api/command` | `{message}` → `{reply, source, done[]}`: además **ejecuta** (abrir, lanzar, reproducir, anotar) |
| `GET /api/status` | Estado del cerebro híbrido, sistema, batería y versión |
| `GET /api/port` | En qué puerto vive este núcleo (para la auto-detección) |
| `GET · POST /api/config` | Leer/guardar cerebro y voz; las claves llegan **en máscara** |
| `GET /api/brain/test` | Prueba cada proveedor: `ok`, modelo, latencia en ms y error legible |
| `POST /api/open` | `{path}` → abre archivo o carpeta con su visor del sistema |
| `GET /api/files` · `/api/tree` | Explorador de raíces seguras y árbol con conteos |
| `GET /api/memories` | Muro de recuerdos (notas + conversaciones) |
| `GET /api/weather` | Clima actual (Open-Meteo, cacheado 20 min) |
| `GET /api/history` · `POST /api/profile` | Historial reciente y preferencias |
| `GET /api/support` | Datos de contacto y soporte que muestra la ventana **09** |
| `GET /api/models` | Catálogo de Ollama con peso real, veredicto de RAM y lo ya descargado (**10**) |
| `GET /api/models/progreso` | Avance al 1 % de cada descarga en curso |
| `POST /api/models/pull · /rm · /use · /ollama` | Bajar, borrar o elegir modelo y encender/apagar Ollama |
| `GET /api/optimize` | RAM, procesos pesados, caché borrable y consejos para este equipo (**11**) |
| `POST /api/optimize/clean · /kill` | Barrar caché por nivel (`seguro`, `todo`, `papelera`) o cerrar un proceso propio |

## Seguridad y privacidad

- Backend y Ollama **solo escuchan en `localhost`**; ningún puerto se expone a internet.
- Archivos: lista blanca de **raíces personales** (Documentos, Escritorio,
  Descargas, Imágenes, Música, Videos) con bloqueo de salidas por `..`.
- **Tus claves y tus notas no viven dentro del programa** sino en tu carpeta
  personal (`~/.cort`, `%APPDATA%\CORT`, o donde diga `CORT_HOME`), así que
  actualizar o reinstalar el instalador no las borra. `GET /api/config` devuelve
  una máscara (`gsk_abcde…35`), nunca la clave entera, y 07 · Perfil enseña la
  ruta donde está guardada.
- Los avisos que CORT lee en el teléfono (WhatsApp, Gmail, Telegram) **no se
  guardan**: doce líneas en RAM del proceso, se van solas y «olvida los avisos»
  las tira. La llave con la que se firma el APK tampoco está en el repo: está en
  la caché privada de Actions (el repo es público).
- **Nunca ejecuta programas por la ruta de archivos**: las extensiones de
  programa están vetadas y hay un tope de tamaño (400 MB).
- Los lanzadores usan una lista blanca estricta (`LAUNCH_ALLOWLIST`); en el
  equipo de prueba la orden «abre terminal» fue rechazada y «abre youtube» funcionó.
- Sin cuentas, sin telemetría y sin llamadas a servicios propios: lo único que
  sale del equipo es la petición a la IA que tú elijas (o ninguna, en modo offline).

## Estructura

| Ruta | Qué es |
|------|--------|
| `backend/app/main.py` | API FastAPI y servidor de la interfaz |
| `backend/app/brain.py` | Cerebro híbrido, enrutador y prueba de proveedores |
| `backend/app/actions.py` | Ejecutor de acciones del sistema (frases → hechos) |
| `backend/app/local_commands.py` | Comandos instantáneos sin IA (hora, batería, CPU…) |
| `backend/app/config_store.py` | Ajustes y claves en `backend/cort_config.json` |
| `backend/app/sensors.py` | Raíces seguras, apertura con visor y clima |
| `backend/app/memory.py` | Memoria persistente SQLite |
| `backend/app/models.py` | Catálogo de Ollama, veredicto de RAM y descargas en segundo plano |
| `backend/app/optimize.py` | RAM, procesos y cachés: lista blanca de rutas y lista negra de procesos |
| `ui/index.html` · `ui/css` · `ui/js` | Holograma: orbe Three.js + HUD + voz + gestos |
| `ui/vendor/` | Three.js incluido: la interfaz funciona sin internet |
| `desktop/main.cjs` | Ventana Electron (modo cabina / modo vidrio) |
| `apps/apk/` | El proyecto Android sin Gradle: Java puro + `compilar.sh` (el asistente con avisos) y `rempaquetar.sh` (el cuerpo original con la cara nueva) — los compila Actions, nunca tu PC |
| `docs/` | Plan de arquitectura, fotogramas de referencia y capturas |
| `scripts/` | `run.sh` (Linux/macOS), `run.bat` (Windows), `run-desktop.sh` (Electron), `instalar-linux.sh` (app instalada), `telefono.sh` (Wi-Fi), `prueba-lectura.py` y `prueba-costura.py` (las dos comprobaciones de esta ronda, en sandbox, sin tocar tus carpetas) |
| `.github/workflows/build.yml` | CI que compila los instaladores y publica la Release |

## Hoja de ruta

- [x] **F1** Backend híbrido + memoria SQLite + comandos locales
- [x] **F2** Orbe Three.js conectado al backend, chat y reloj
- [x] **F3** Paneles HUD, secuencia de arranque, sensores, ventanas de vidrio
- [x] **F4** Gestos con MediaPipe en modo ligero (código listo; falta probar con cámara física)
- [x] **F5** Ejecutor de acciones, música, notas, perfil con pruebas de cerebro,
      ventana de ayuda y soporte (wake word incluida; Piper TTS queda opcional
      porque Web Speech ya da voz gratis)
- [x] **F6** Escritorio Electron + instaladores por CI (.exe / .AppImage / .deb)
- [x] **F7** Android: dos APK en la Release. `CORT-IA-1.1.3.apk` — el cuerpo original de la dueña con la interfaz actual metida en `assets/ui/` (`apps/apk/rempaquetar.sh`, firmado por CI). Y `CORT-IA-1.2.2-asistente.apk` — `apps/apk/compilar.sh` compila desde cero, en Java y sin Gradle, el APK que **sí** puede ser el asistente predeterminado, escuchar el doble toque del auricular y leer en voz alta los avisos que llegan (`Avisos.java`, un `NotificationListenerService` que sólo guarda doce líneas en RAM)
- [x] **F7a** Voz que lee: «lee mis notas / mis tareas / mis avisos / el documento …» — notas y pendientes en SQLite (`memory.py`), textos de las carpetas seguras (`sensors.leer_texto`) y avisos del teléfono por la barra de notificaciones. Comprobado sin teléfono con `scripts/prueba-lectura.py` y `scripts/prueba-costura.py`
- [ ] F7b Meter en el repo el proyecto Gradle que generó el 1.1.0 para poder recompilar el cuerpo de verdad (asistente + auriculares + su cara, en un solo APK)
- [ ] F8 Idiomas adicionales y temas visuales

Todo el software usado es gratuito.

---

## 💬 Soporte, colaboración y contacto

¿Eres programador y quieres sumar una función, un idioma o un cerebro nuevo?
¿O simplemente quieres saber cómo funciona? Escríbenos con el asunto **«CORT»**
y te contamos por dónde seguir.

| Rol | Persona | Correo |
|---|---|---|
| 👩‍ Creadora del proyecto | Sandra | [sandrasofialopezgomez3@gmail.com](mailto:sandrasofialopezgomez3@gmail.com) |
| 🤝 Colaborador | Carlos | [carlosa3325@gmail.com](mailto:carlosa3325@gmail.com) |

**Apoyar el proyecto (opcional).** C.O.R.T. es personal, abierto y sin fines de
lucro: no hay nada que vender. Si aun así quieres invitar un café o cubrir el
coste de una GPU para probar modelos locales, escríbenos a cualquiera de los dos
correos y te decimos cómo — sin compromisos y sin intermediarios.

Los errores y las ideas también bienvenidos por
[Issues](https://github.com/Sandra2244/CORT/issues).

## Licencia

[MIT](LICENSE) — úsalo, cópialo y modifícalo con citar el origen.
