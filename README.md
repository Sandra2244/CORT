# C.O.R.T. — Cognitive Orchestrator / Real-Time

<p align="center">
  <img src="https://img.shields.io/badge/versión-v0.2.0-00bfff?style=for-the-badge&logo=semanticrelease&logoColor=white" alt="versión 0.2.0">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Three.js-orbe%203D-F5871F?style=for-the-badge&logo=threedotjs&logoColor=white" alt="Three.js">
  <img src="https://img.shields.io/badge/Electron-ventana%20HUD-47848F?style=for-the-badge&logo=electron&logoColor=white" alt="Electron">
</p>

<p align="center">
  <a href="https://github.com/Sandra2244/CORT/releases/latest"><img src="https://img.shields.io/badge/Descargar-última%20Release-blueviolet?style=flat-square&logo=github&logoColor=white" alt="Descargar la última Release"></a>
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
| 👥 | **Modelos locales (Ollama)** | **10 · Modelos** enseña 14 modelos con su peso real, su flecha `↓ descargar` y el veredicto para **la RAM de este equipo** (`VA BIEN · JUSTO · NO CABE`): `usar`, `✕ borrar` y botón para encender o apagar Ollama. Descargar **no congela la interfaz**: el modelo pasa a la cola, Ollama se arranca solo si hace falta, la barra marca MB y MB/s reales, y cada descarga tiene su `✕ cancelar` |
| 🧹 | **Optimización del equipo** | **11 · Optimizar** contesta **al instante** con la RAM y quién se la come (con botón para cerrar procesos propios); lo que tarda —contar la caché del disco— se mide en un hilo aparte y se va pintando sola. Barre la caché segura sin tocar documentos, la papelera ni el escritorio |
| ⌨ | **Consola de comandos** | Prompt `cort@nave:~$`, historial con ↑/↓ y **Tab que completa** («repro» → «reproduce») |
| 📂 | **Archivos seguros** | Árbol lateral con doble conteo (carpetas · archivos) que se expande, vista rejilla/lista y botón **Abrir** que lanza la carpeta en el explorador del sistema |
| 🎵 | **Música** | Escanea `~/Música`, reproduce en el panel o abre tu reproductor (VLC) con «reproduce música» |
| 📝 | **Notas, pendientes y memoria** | «apunta …» guarda una nota; «tengo que comprar aceite» guarda una pendiente y «listo 1» la marca como hecha; **08 · Cerebro** muestra el muro de recuerdos enmarcados (notas + conversaciones) |
| 🔊 | **Te lo lee en voz alta** | «lee mis notas» · «lee mis tareas» · «lee el documento recibo» · «lee mis avisos». En el PC lo lee del backend (notas, pendientes y textos de tus carpetas seguras); en el teléfono `CORT-IA-2.3.1.apk` lee el **centro de notificaciones** — WhatsApp, Gmail, Telegram, Signal — con un oído que guarda doce líneas en RAM y se borran solas: nunca se escriben a disco |
| 📊 | **Sensores** | CPU / RAM / disco / batería reales y clima actual (Open-Meteo, cacheado, sin API key) |
| ✋ | **Gestos** | MediaPipe ligero: palma despliega/plega ventanas, pinza trae el chat, puño las cierra |
| 💡 | **Lámpara de estado** | Morado escuchando · naranja procesando · verde en línea · gris con el HUD oculto · rojo sin backend |
| 🖥 | **Pantallas** | Además del orbe hay cinco hojas a pantalla completa: **Música** y **MV** (sólo en el teléfono; MV es la del videoclip con su letra sincronizada, donde el orbe no se apaga sino que se hace disco en una esquina), **Charla** (chat normal con tus modelos de Ollama, copiar y seleccionar), **Código** (terminal + cuaderno) y **Equipo** (sólo en el teléfono: los siete bloques de mando —Voz · Mando · Cerebro · Memoria · Atuendos · Agenda · Oído—). Se cambia con ☰, deslizando el dedo de lado, con `Alt+←/→` o diciéndolo. Ninguna tapa el orbe: cuando no es su pantalla, el lienzo WebGL se apaga |
| 📱 | **APK del teléfono** | **Uno solo** en la Release: `CORT-IA-2.3.1.apk` (`versionCode` 20301), el que compila `apps/apk/compilar.sh` en GitHub Actions con el mismo método del original (`aapt2` + **`kotlinc` 1.9.24** + `javac --release 11` + `d8` + `zipalign` + `apksigner`, sin Gradle ni AndroidX), con el anillo de siempre como icono, el rol de asistente, su propio reproductor, el doble toque del auricular, la lectura de avisos, **su oído sin nube** y la **hoja Equipo** con las ocho funciones del puente 2.1 (volumen, linterna, alarma, voz, atuendos, burbuja, memoria y agenda) más las dos del oído (`oidoEstado`, `oidoPropio`) |
| 🫛 | **Hoja Equipo: CORT manda sobre el aparato** | `☰ ▸ Equipo` o «abre el equipo», con siete bloques y sus frases de voz: **Mando** («sube el volumen», «enciende la linterna», «pon una alarma a las 7:30», «abre whatsapp»), **Voz** («voz de siri», «cambia la voz»), **Atuendos** («ponte azul», «atuendo Cortana», «burbuja» —el punto de CORT flotando sobre otra app—), **Memoria** (SQLite del teléfono y «sincroniza con el PC»), **Cerebro** («piensa por qué está lloviendo», con la nube que ajustes tú y **35 patrones locales** que ejecutan la orden sin necesitar red), **Agenda** («¿qué tengo hoy?», «revisa el correo») y **Oído** («activa el oído sin internet», «¿me oyes sin wifi?» — dice su fase real y cuánto sitio queda). Son las ocho funciones del puente 2.1 (`docs/CONTRATO-PUENTE-2.1.md`) más las dos del oído (`oidoEstado` y `oidoPropio`, en `apps/apk/src/com/cort/ia/CortNative.java`), y cada bloque dice en su pie si lo que falta es el APK, un permiso o el PC: **no finge haber hecho lo que no hizo** |
| 🎬 | **Pantalla MV: el video con su letra** | Hoja aparte del reproductor, en el teléfono: el videoclip se ve en la propia cara (`<video>` sobre la misma `content://` que suena), debajo va la **letra sincronizada** línea a línea con la activa marcada y **clic para saltar a ese segundo**, y el **orbe se encoge a una esquina girando como un disco** en vez de apagarse. La letra sale de LRCLIB (gratis, sin clave, cacheada); si el servidor está saturado lo dice y hay botón de **rebuscar**. En audio suelto no deja un cuadro negro: avisa y conserva la letra. |
| 🗂 | **Ordena tus archivos sin perder ni uno** | «ordena mis archivos / mis documentos / la música» o el botón **⤢ ordena** de **01 · Archivos**. Primero sale el **plan** (`de → a` con su motivo y el total) y **no se mueve nada** hasta que digas **«confirmar»**; «cancelar» deja la carpeta tal cual. El plan caduca a los quince minutos y lleva un token, así que lo que confirmas es exactamente lo que viste. `backend/app/organiza.py` no tiene ninguna primitiva de borrado: reorganiza y, si el nombre está ocupado, añade ` (2)`. |
| 🎮 | **Modo juego: CORT se aparte mientras juegas** | «modo juego» / «vuelve CORT», el interruptor de las hojas Música y MV, o el botón `CORT · PC`. Con él puesto, CORT **cierra el micrófono**, **no pide el foco audio** al reproducir y deja de hablar por el auricular: nada de robarle el turno a una partida. No necesita permiso de uso de aplicaciones ni lista de instalados — es un interruptor, no un espía. |
| 🔄 | **Que se actualice solo** | «revisa si hay actualizaciones» / «actualízate» contra la última Release de GitHub. En el escritorio baja su instalador o, si pesa más de 100 MB, deja `scripts/actualiza.sh` listo: respalda la instalación anterior en `~/Aplicaciones/CORT.anterior-<fecha>`, instala sin sudo y **no toca `~/.cort`** (claves, notas y recuerdos). En el teléfono Android no deja que una app se reemplace a sí misma: CORT te da el enlace del APK y lo pones tú encima. |
| 🎙 | **El oído no traba el teléfono** | «Oye CORT» cierra el micrófono cuando la app se va a segundo plano, cuando se apaga la pantalla, mientras suena música y mientras la ventana 11 está contando caché, y vuelve solo al pasar todo eso. Si nadie la llama, se españa cada vez más en vez de reabrir el micro cuatrocientas mil veces |
| 🎙 | **Escucha sin internet: el oído propio** | Desde `CORT-IA-2.3.0.apk` el teléfono lleva **dentro** su motor de reconocimiento: Vosk 0.3.47 con el modelo de español `vosk-model-small-es-0.42`. «Oye CORT» y las órdenes por voz funcionan **sin Wi-Fi, sin datos y sin los servicios de voz de Google** —el caso real de un teléfono sin cuenta de Google o con el juego comiéndose el micro. Se enciende y se apaga en **Equipo ▸ 7 · Oído** (o diciéndole «activa el oído sin internet», «¿me oyes sin wifi?»), y ahí se ve su fase de verdad: `preparando` · `extrayendo` · `cargando` · `listo` · `sin-sitio` · `roto`. Si el oído propio no arranca, CORT **cae solo en el reconocedor del sistema** sin que la cara note nada; el desempaque (60 MB) va en un hilo aparte y pide sitio antes de tocar nada |
| 🤖 | **CORT como asistente** | En `CORT-IA-2.3.1.apk`: di «pon CORT como asistente» (o usa el botón `CORT · PC` ▸ «Poner CORT como asistente») y Android abre su cuadro de rol —`RoleManager`, API 29+— para elegir CORT. El gesto del asistente, la pantalla bloqueada y el doble toque del auricular quedan entonces en CORT; el «OK Google» con la pantalla apagada se pierde, porque eso lo decide el servidor de Google |
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
| **Android (APK del teléfono)** | instala [`CORT-IA-2.3.1.apk`](https://github.com/Sandra2244/CORT/releases/latest) · `bash scripts/instala-apk.sh` | un solo APK: el anillo de siempre, las once ventanas, su reproductor, sus pantallas, su **oído sin internet** y el rol de asistente. Se **instala encima** del `2.0.0`, del `2.1.0`, del `2.2.0` y del `2.3.0` sin desinstalar y sin perder el micrófono concedido, los gustos guardados ni la dirección del PC escrita a mano: misma llave de firma (`fa:ab:ef:46…`, medida en su `-firma.txt` y verificada además con `keytool`) y `versionCode` mayor (20301). Si **vienes de un 1.x** da `INSTALL_FAILED_UPDATE_INCOMPATIBLE` —son dos llaves distintas, medidas—: hay que desinstalar una vez; desde el 2.0.0 la llave ya no cambia. **Ojo al sitio del teléfono, no a la RAM**: el archivo son 45,2 MB, pero en el primer arranque el oído desempaca el modelo (60.286.598 B sueltos) en su carpeta privada; si no cabe, CORT dice `sin-sitio`, no escribe nada, y sigue funcionando con el reconocedor del sistema. Los pasos del teléfono y la tabla de errores de Android, en [`docs/INSTALAR-APK.md`](docs/INSTALAR-APK.md); y si el que aparece es un **aviso de Google o Play Protect** («no reconoce esta aplicación», «puede dañar tu dispositivo», Chrome no deja descargar), la tabla por frase exacta y qué pulsar está en [`docs/BLOQUEO-PLAY-PROTECT.md`](docs/BLOQUEO-PLAY-PROTECT.md) |
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

[La última Release](https://github.com/Sandra2244/CORT/releases/latest) tiene los
instaladores generados por GitHub Actions (nunca se compilan en tu PC, que para
eso hace falta un equipo sobrado):

| Archivo | Tamaño (medido en la API pública de Releases de `v0.2.24-demo`, el 2026-10-21) | Para |
|---|---|---|
| `CORT.Setup.0.2.0.exe` | 79.029.460 bytes (75,4 MB) | Windows 10/11 64 bits (instalador NSIS, eliges carpeta) |
| `CORT-0.2.0.AppImage` | 107.773.228 bytes (102,8 MB) | Linux genérico (ejecutable directo) |
| `cort-desktop_0.2.0_amd64.deb` | 75.016.478 bytes (71,6 MB) | Debian / Ubuntu / Mint |
| `CORT-IA-2.3.1.apk` | **47.365.737 bytes** (45,2 MB) comprimidos sobre 61.841.077 sin comprimir, 47 entradas, proporción **0,77** — `sha256` `68dce45384573744e43b9a7f04c368715a8dfb3419f1fc2f4ee231b13488ebb5`, comprobado bajando el archivo y leyéndolo en el portátil — las cifras están dentro del `-firma.txt` que sube el propio run, desglosadas por bloque | Android 8+: **el único APK** (`versionCode` 20301). El anillo de siempre como icono, once ventanas de vidrio, rol de asistente del sistema, reproductor propio con gustos y playlists, lectura de avisos, llamadas, **MV con letra sincronizada**, **organizador de archivos con plan y confirmación**, **modo juego**, **auto-actualización por voz**, la **hoja Equipo** (mando, voz, atuendos, memoria, cerebro sin PC, agenda y **oído**), el **cerebro ancho** de 2.2.0 (cuentas, porcentajes, unidades y fechas sin portátil ni nube: `Razon`, **283 frases** en 33 reglas) y el **oído propio sin nube** de 2.3.0 (Vosk 0.3.47 con su modelo de español dentro del APK: «Oye CORT» funciona sin internet y sin los servicios de voz de Google). El **2.3.1** no añade funciones: firma con los tres esquemas a la fuerza y publica la **auditoría de instalabilidad**, porque Play Protect lo bloqueaba al instalar — guía de qué pulsar en [`docs/BLOQUEO-PLAY-PROTECT.md`](docs/BLOQUEO-PLAY-PROTECT.md) |
| `CORT-IA-2.3.1-firma.txt` | 3.427 bytes | con qué llave salió (huella SHA-256 `faabef468f3a…`), si se instala encima, el peso medido **y su desglose** por bloque (`.dex`, `.so`, modelo, cara, recursos) y, desde el 2.3.1, la **auditoría leída del APK final**: `sha256`, esquemas v1/v2/v3, ventana de validez del certificado, `resources.arsc` sin comprimir y alineado, `minSdk`/`targetSdk` y que no esté marcado como depurable — prueba pública |

> Los tamaños del escritorio son los que declara la API pública de Releases el
> 2026-10-21, no una estimación.
>
> **Y sobre «el APK no pesa lo que debería y lo comprimiste demasiado»: se bajaron
> los dos APK y se midieron entrada por entrada.** El `CORT-IA-1.1.0.apk` original
> ocupa 1.815.389 bytes de archivo sobre 4.538.254 de entradas sin comprimir
> (proporción **0,40**, 45 entradas); el `CORT-IA-2.1.0.apk` publicado en
> `v0.2.15-demo`, 978.056 sobre 2.349.202 (**0,42**, 42 entradas). Apretado está
> igual —incluso un pelo menos apretado—, así que la diferencia **no es compresión**.
> Es que el `1.1.0` estaba escrito en Kotlin y arrastraba su tiempo de ejecución:
> sus cuatro `classes*.dex` más los `kotlin/*.kotlin_builtins` suman **919.207 bytes
> comprimidos**, por los **90.943** del `classes.dex` único de este Java puro. Ahí
> están los ~828 KB de diferencia, y es el precio de mantener el método de siempre
> (`aapt2` + `javac` + `d8`, sin Gradle, sin AndroidX, sin Kotlin).
>
> **Y el `2.2.0` publicado en `v0.2.18-demo` se volvió a bajar y medir**: 998.536
> bytes sobre 2.397.186 sin comprimir, **42 entradas y proporción 0,42** — las
> mismas cifras que declara su `-firma.txt`, así que la prueba es pública. Crece
> **20.480 bytes** (un 2,1 %) respecto al `2.1.0`, y el crecimiento está donde tiene
> que estar: `classes.dex` pasa de 90.943 a **108.295 bytes comprimidos** (las tres
> clases nuevas, `Razon` con sus cuentas y fechas, `Aparato` con el entorno y
> `Sentidos` con el `SensorManager`), y `assets/habilidades.json` de 35 patrones a
> **33 reglas con 283 frases** (12.100 bytes sin comprimir). Aquí **no se quitó
> ninguna función**: el archivo más pequeño de los dos sigue siendo este.
>
> **Y el `2.3.0` pesa lo que pesa porque ahora hay que oírlo sin nube — desglosado,
> no de memoria.** El `-firma.txt` del propio run mide cada bloque dentro del APK
> final: `classes*.dex` **782.365 B** (Java + Kotlin 1.9.24 con el puente del oído),
> las cuatro `.so` **5.868.445 B** comprimidos sobre 17.433.208 en crudo (`libvosk.so`
> y `libjnidispatch.so`, uno por cada arquitectura de teléfono: `arm64-v8a` y
> `armeabi-v7a`), la cara **370.872 B** y los recursos **511.747 B**. Todo eso suma
> unos **7,6 MB**. Los **39.817.833 B** que faltan son el modelo de español
> `vosk-model-small-es-0.42`, que viaja **sin comprimir** (ya es un ZIP; comprimirlo
> otra vez no lo reduce y sí cuesta batería en el primer arranque). De ahí la
> proporción **0,77**, mucho más alta que el `0,42` del `2.2.0`: no es que esté peor
> apretado, es que el bulto es un archivo que ya venía apretado. La alternativa era
> seguir dependiendo del reconocedor de Google —que en un teléfono sin sus servicios
> no está, y que es justo la queja que motivó la ronda—, así que el peso es el precio
> de escuchar sin internet. Lo que sí se quitó es relleno: **no hay `.so` de `x86` ni
> `x86_64`**, que en su teléfono nunca se ejecutarían.
>
> Lo que **no** falta es contenido. Comparando las listas de entradas de ambos APK:
> los **11 archivos de `assets/ui/`** del original están los once en el nuestro, y
> además `assets/habilidades.json` (35 patrones en el `2.1.0` medido; **33 reglas y
> 283 frases** desde el `2.2.0`), `pantallas.js` y `telefono.js`. La
> cara sin comprimir pesa **1.622.292 bytes** frente a los 1.408.297 del `1.1.0`:
> **214 KB más de interfaz dentro del mismo archivo más pequeño**. Las tres salidas
> de `res/xml` del original (`backup_rules`, `data_extraction_rules`,
> `network_security_config`) siguen estando, renombradas en español
> (`respaldo`, `extraccion`, `seguridad_red`) y con dos nuevas (`archivos` para el
> `content://` de «envíame ese archivo» y `asistente` para el rol). Los PNG del
> anillo, **píxel a píxel idénticos** a los del `1.1.0` (difieren sólo porque
> `aapt2` los recompresiona): es el logo de siempre, no uno parecido.
>
> El peso del APK lo publica ahora cada run dentro de su `-firma.txt` (`compilar.sh`
> lo mide con `stat` y `zipfile`); en este README no se estima ninguno.

> Los instaladores de escritorio abren el mismo backend de Python: siguen
> necesitando Python 3.10+ en el equipo, y la primera vez puede tardar unos
> segundos en arrancar mientras crea su entorno.

### 6 · CORT en el teléfono

Hay **un solo APK**, y es el que se compila aquí de principio a fin:

| APK | Qué es | Dónde está |
|---|---|---|
| `CORT-IA-2.3.1.apk` | Java + **Kotlin 1.9.24** sin Gradle (`aapt2` + `kotlinc` + `javac --release 11` + `d8` + `zipalign` + `apksigner`), con el holograma del repo embebido bajo `https://cort.local` y su puente de voz propio (`CortNative.java`). Lleva el **anillo de siempre** como icono —`compilar.sh` saca los cinco `mipmap-*` y el XML adaptativo del `base/CORT-IA-1.1.0.apk`, no lo dibuja nadie—, el traje de `VoiceInteractionService` para **ser el asistente predeterminado**, `MediaSession` para el **doble toque del auricular**, `Avisos` (`NotificationListenerService`) que **lee en voz alta lo que llega**, **su propio reproductor** (`.Reproductor`, un servicio en primer plano con `foregroundServiceType="mediaPlayback"`: biblioteca leída de `MediaStore`, gustos que se aprenden con 👍/👎, listas guardadas, avance/retroceso y **cuadro a cuadro** en vídeo, todo en segundo plano sin trabar el teléfono) y, estrenando versión, **`Oido.kt`**: Vosk 0.3.47 + JNA + el modelo de español dentro del APK, con el micro abierto en su propio hilo, `extractNativeLibs="true"` para que las `.so` viajen comprimidas, y **un solo `stt-end` por escucha** para que el «Oye CORT» no se rearme doble. | `apps/apk/compilar.sh` → la Release |

La vía de **rempaquetar** el binario original (`rempaquetar.sh`) está borrada del
repo y del workflow. Existía porque el proyecto Gradle que generó el `1.1.0`
nunca estuvo en este repo —lo guardado era el binario
(`instaladores/CORT-IA-1.1.0.apk`, SHA-256 `b5fa07fa…`)— y lo único que se le
podía cambiar era la cara. Ese camino daba dos APK que había que saber elegir, y
la dueña lo pidió claro: **todo dentro del que se compila**. Lo que se conserva
del binario es su icono, que es lo que lo hace «el de siempre».

Qué es verdad y qué no, dicho sin adornos:

- **El reproductor, la música y las llamadas funcionan en el teléfono sin PC**;
  las ventanas 10 · Modelos, 11 · Optimizar, la pantalla **Charla** y la
  pantalla **Código** necesitan el backend del portátil, porque piden `/api/*`.
  Sin PC no inventan una respuesta: la cara traduce el `501` del `MainActivity`
  y lo dice en voz alta. `MainActivity` intercepta `/api/*` a propósito.
- **La pantalla Código ejecuta en el PC, no en el teléfono.** Android no permite
  abrir un shell desde una app normal; por eso ese terminal manda la orden al
  núcleo (`/api/command`) y lo que ves es lo que hizo tu portátil. Prometer un
  terminal que «arregla el teléfono» sería mentira.
- **Leer los avisos pide un interruptor a mano, una vez.** Abre el menú (el botón
  `☰`) y toca «Dar el permiso de los avisos», o ve a Ajustes ▸ Notificaciones ▸
  Acceso de notificación y activa CORT. Sin él CORT no ve la barra.
- **La pantalla MV enseña la letra aunque la imagen no abra.** El vídeo se pide con
  la misma `content://` que reproduce el servicio, y la cara tiene
  `setAllowContentAccess(true)`: donde el WebView no pueda decodificar ese vídeo,
  la hoja **no se queda en negro eterno** — a los cuatro segundos lo dice con
  palabras y la canción sigue sonando, porque el audio lo pone `.Reproductor`, no la
  página. La letra no depende del vídeo: `/api/letras` la trae de LRCLIB (gratis,
  sin clave), y si el servidor está saturado la cara lo avisa y deja el botón
  **rebuscar la letra**.
- **El modo juego es un interruptor, no un espía.** «modo juego» / «vuelve CORT»,
  el botón de las hojas Música/MV o el menú `CORT · PC`. Con él puesto CORT cierra
  el micrófono, no pide el foco audio y calla la voz por el auricular. **No** se le
  ha dado permiso de uso de aplicaciones (`PACKAGE_USAGE_STATS`) ni de listar lo
  instalado: la detección automática de la partida quedó fuera porque la dueña no
  quiso ese permiso, y así está en el manifiesto.
- **Con CORT como asistente se pierde el «OK Google» con la pantalla apagada**,
  porque eso lo decide el servidor de Google, y Android sólo permite un asistente.
- **Contestar llamadas por ti, buzón de voz, leer SMS y gestionar el correo no
  están en este APK.** Contestar exige el rol `ROLE_CALLING` y un `InCallService`
  (quedarse con la pantalla de llamada del sistema), y para SMS/WhatsApp no hay
  API: se diría «lo hago» y no es cierto. Aquí CORT **ve con quién hablas y marca
  el número** (`Telefono.java`, con permiso de contactos y de llamar concedido a
  mano); lo demás está anotado como pendiente en `docs/PLAN-CORT.md`.
- **Actualizar el APK: el `2.1.0` ya se instala encima del `2.0.0`, sin desinstalar
  y sin perder datos.** Hasta `v0.2.8-demo` cada run firmaba con una llave desechable
  distinta, y para Android una firma distinta es otra aplicación; al desinstalar se
  va lo concedido a mano (micrófono, avisos, contactos, dirección del PC) y lo que
  CORT apuntó **en el teléfono**: tus gustos musicales y tus listas viven en las
  preferencias de la app. Lo que no se pierde es el cerebro: las notas, los
  recuerdos y las pendientes están en el PC (`~/.cort/`, o `%APPDATA%\CORT\` en
  Windows), y las claves de Groq/Gemini también.
  `apps/apk/llave.sh` intentó arreglarlo con la caché de Actions y **está medido
  en `v0.2.10-demo`: no basta** — `actions/cache` guarda cada llave en el
  *ref* que la creó, una etiqueta nueva es otro ref, y la huella de esta Release no
  coincide con la de `v0.2.9-demo` (`645fee97…`). El arreglo es el secreto del repo,
  y **ya está puesto** (2026-10-21, medido en Settings ▸ Secrets and variables ▸
  Actions): `CORT_APK_KEYSTORE_B64` y `CORT_APK_KEYSTORE_PASS`, fabricados en el
  portátil con `bash scripts/llave-nueva.sh`. `llave.sh` los mira **primero**, así
  que desde entonces la llave es siempre la misma, y **está comprobado en la
  propia Release**: el `CORT-IA-2.0.0-firma.txt` de `v0.2.13-demo` declara
  `certificate SHA-256 digest: faabef468f3ae04fdfab9659d6a051c453d6ded7b965468c9c3b85caffa31977`
  y la línea «actualizar instalando encima: sí». Como ESA Release ya firmó con la
  llave fija, el `2.1.0` (`versionCode` 20100 > 20000, mismo paquete `com.cort.ia`,
  misma firma) **se pone encima**: sólo hace falta desinstalar una vez si el teléfono
  todavía guarda un APK de antes de `v0.2.13-demo`. Comprobación pública siempre: la
  huella SHA-256 del certificado sale en el `-firma.txt` de cada APK y como anotación
  del check-run; dos Releases seguidas con la misma huella = se instala encima. La
  llave nunca se sube al repo (está en `.gitignore`, y el repo es público).
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
git tag -a v0.2.13-demo -m "CORT" && git push origin v0.2.13-demo   # ← dispara la compilación
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
| `GET /api/models/progreso` | Avance de cada descarga en curso: MB, MB/s y porcentaje reales, sumando las capas del modelo |
| `POST /api/models/pull · /rm · /use · /ollama` | Bajar (va **a la cola**, la interfaz no se espera), borrar o elegir modelo y encender/apagar Ollama |
| `POST /api/models/cancel` | Corta una descarga o la quita de la fila |
| `GET /api/optimize` | RAM, procesos pesados, caché borrable y consejos para este equipo (**11**). Contesta **al instante** con lo que ya está medido y dice `midiendo: true` mientras la caché del disco se cuenta en un hilo aparte |
| `POST /api/optimize/clean · /kill` | Barrar caché por nivel (`seguro`, `todo`, `papelera`) o cerrar un proceso propio |
| `GET /api/letras?artista=&titulo=&duracion=` | La letra de LRCLIB (sin clave): `sincronizada` con marcas `[mm:ss.xx]` o `plana`, y `reintenta: true` si el servidor está saturado. Se cachea en memoria 40 canciones |
| `POST /api/organizar` · `/api/organizar/aplicar` | Primero el **plan** (`entradas` con `de`/`a`/`motivo` + `token` de 15 minutos), después los hechos. `aplicar` sin el token del plan que viste **no mueve nada**, y `organiza.py` no conoce ninguna primitiva de borrado |
| `GET /api/update` · `POST /api/update/aplicar` | Qué CORT está instalado frente a la última Release de GitHub, y la reparación del escritorio: baja el instalador o, si pesa más de 100 MB, deja `pendiente: true` con los pasos (`bash scripts/actualiza.sh`) en vez de congelar el portátil |

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
| `apps/apk/` | El proyecto Android sin Gradle: Java puro + `compilar.sh` — el único APK que sale (asistente, avisos, reproductor propio y llamadas) —, `llave.sh` para la firma estable y `base/` con el binario viejo sólo para tomar su icono. Lo compila Actions, nunca tu PC |
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
- [x] **F7** Android: **un solo APK** en la Release — `CORT-IA-2.3.1.apk`, que compila `apps/apk/compilar.sh` desde cero en Java + Kotlin y sin Gradle. Es el asistente predeterminado (rol por `RoleManager`), escucha el doble toque del auricular (`MediaSession`), lee en voz alta los avisos que llegan (`Avisos.java`, un `NotificationListenerService` que sólo guarda doce líneas en RAM), trae el anillo de siempre como icono (sacado de `base/CORT-IA-1.1.0.apk`) y lleva dentro su propio reproductor (`.Reproductor` + `Musica.java`: biblioteca, gustos, playlists y cuadro a cuadro en vídeo) y el marcador de contactos (`Telefono.java`). La vía de `rempaquetar.sh` está borrada del repo y del workflow: dos APK que había que elegir era trabajo doble y lío para instalar
- [x] **F7a** Voz que lee: «lee mis notas / mis tareas / mis avisos / el documento …» — notas y pendientes en SQLite (`memory.py`), textos de las carpetas seguras (`sensors.leer_texto`) y avisos del teléfono por la barra de notificaciones. Comprobado sin teléfono con `scripts/prueba-lectura.py` y `scripts/prueba-costura.py`
- [x] **F7c** Pantallas aparte del orbe (`ui/js/pantallas.js`): **Charla** (chat con burbujas, modelos de Ollama, copiar y guardar en Notas), **Código** (terminal contra `/api/command` + cuaderno de código), **Música** y **MV** en el teléfono. Se cambia con ☰, deslizando, `Alt+←/→` o por voz, y el orbe se apaga cuando no le toca para no gastar GPU ni batería — con la excepción de **MV**, donde se encoge a una esquina girando como disco.
- [x] **F7e** La ronda 2.1, «todo lo prometido dentro del APK»: nueve clases Java nuevas (`Acciones`, `VozNueva`, `Recuerdos`+`Sincroniza`, `Mente`+`Nube`+`Cerebro`, `Paleta`, `Agenda`, `Flotante`, `ArchivosProvider`) que sacan las **ocho funciones del puente** (`accion`, `ajusteVoz`, `memoria`, `mente`, `atuendo`, `agenda`, `burbuja`, `comparte`), la hoja **Equipo** con sus seis bloques, el **cerebro sin portátil** (la nube que ajustes tú, con la clave sin salir del teléfono, y 35 patrones locales que **ejecutan** la orden que reconocen), la **burbuja flotante**, la **linterna**, la **agenda de sólo lectura** y el **enviar archivo** con el proveedor del APK. Contrato en `docs/CONTRATO-PUENTE-2.1.md`; cosido y comprobado en los cuatro sitios con `scripts/prueba-costura.py` (9 sectores, sin teléfono)
- [x] **F7f** La ronda 2.3, **el oído propio dentro del teléfono**: `apps/apk/src/com/cort/ia/Oido.kt` (Kotlin, primer `.kt` del repo) desempaca `vosk-model-small-es-0.42` en `filesDir/motor` con su marca de versión, abre el micro en su propio hilo y habla con `libvosk.so` por JNA. **Sin `SpeechService` ni `StorageService`** de Vosk: el primero se come un `RuntimeException` del buffer y tumba el proceso, y el segundo pide `res/raw` con `AssetFileDescriptor`, que los assets comprimidos de `aapt2` no dan. `CortNative.java` lo engancha en un solo cuello de botella (`arrancarEscucha()` prueba el oído y, si no, cae en el `SpeechRecognizer` de Google), así que el bucle «Oye CORT», los frenos, el modo juego y la insignia del auricular siguen intactos; la hoja **Equipo** estrena el bloque **7 · Oído** con su fase en español, su interruptor y sus preguntas por voz. El pipeline gana `kotlinc` 1.9.24 (con su caché), la caché del motor, y una prueba que **carga el modelo de verdad** (`scripts/prueba-oido.sh`, seis comprobaciones) antes de compilar: ahí salió que `cancela()` mandaba un segundo `stt-end`. Peso medido: **47.365.737 B** (45,2 MB), de los que 39.817.833 son el modelo y 5.868.445 las cuatro `.so`; `.dex` 782.365 B, cara 370.872 B. Firma la misma `fa:ab:ef:46…` de siempre, así que se instala encima del `2.2.0` sin perder datos.
- [x] **F7g** La ronda 2.3.1, **que se pueda instalar**: la dueña reportó que Google / Play Protect le bloqueaba el APK. Se bajó el `CORT-IA-2.3.0.apk` publicado y se leyó byte a byte: sale con **v1+v2+v3**, certificado vigente hasta 2056, `resources.arsc` sin comprimir y alineado, CRC íntegro — o sea, **el APK no estaba roto**; era el aviso que Play Protect da a cualquier app auto-firmada fuera de Play, que no se quita desde el repo. Lo que sí se hizo: pedir los **tres esquemas con bandera explícita** (con `minSdk 26` la v1 viene desactivada por defecto y la v3 sólo se activa sola con `minSdk >= 28`; ya no dependemos del default del runner), y publicar en cada `-firma.txt` la **auditoría de instalabilidad** que hace `scripts/audita-apk.sh` sobre el APK final — `sha256`, peso, esquemas, ventana del certificado, `resources.arsc`, `.so`, `minSdk`/`targetSdk` y que no esté marcado como depurable — con **el pipeline poniéndose rojo** si algo de eso falla. Además: `scripts/instala-apk.sh` ahora **compara el sha256** del archivo descargado contra la hoja, traduce los errores de certificado y de Play Protect, y la guía nueva [`docs/BLOQUEO-PLAY-PROTECT.md`](docs/BLOQUEO-PLAY-PROTECT.md) dice **qué pulsar según la frase exacta** que sale en pantalla (incluido el aviso de que el certificado empieza el 2026-10-21 11:19 GMT: con el reloj del teléfono atrasado, Android lo ve «aún no válido»). Medido en la Release `v0.2.24-demo`: `CORT-IA-2.3.1.apk` **47.365.737 B**, `versionCode` 20301, `sha256` `68dce453…8ebb5` — el mismo archivo bajado en el portátil hashea exacto —, misma llave `fa:ab:ef:46…` y `-firma.txt` de 3.427 B.
- [x] **F7d** La ronda «todo en uno» que pidió la dueña: el APK con el **modo juego** (cierra el micro y suelta el foco audio; sin permisos de uso de aplicaciones), la hoja **MV** con **letra sincronizada** de LRCLIB, el **organizador de archivos** con plan y confirmación (`backend/app/organiza.py`, sin borrar nada), la **auto-actualización por voz** contra GitHub (`backend/app/actualiza.py` + `scripts/actualiza.sh`, con respaldo y sin sudo) y la **llave de firma definitiva** ya como secreto del repo. Comprobado sin teléfono con `scripts/prueba-costura.py` (7 sectores) y `scripts/prueba-organiza.py`.
- [ ] F7b Contestar llamadas por ti y buzón de voz: pide el rol `ROLE_CALLING` con su `InCallService` (Android no deja otra cosa); leer SMS o el contenido de WhatsApp no tiene API, así que no se finge
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
