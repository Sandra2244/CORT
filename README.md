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
| 💻 | **Dos registros, un cerebro** | `brain.py` reconoce si la frase es de programación (`es_programacion`: un nombre de lenguaje o herramienta suelto, o un sustantivo técnico con su verbo) y manda esa pregunta con otra consigna de sistema — código primero, explicación corta, «no lo sé, comprueba X» en vez de inventar, y nada de instalar modelos que no caben en 1,8 GiB — sin cambiar de IA, sin clave nueva y sin coste extra. Con el cerebro de código apagado lo dice: «necesita un cerebro de código… pega una GROQ_API_KEY», y no contesta con el tiempo de la ciudad |
| 🌐 | **Orbe 3D** | Plexus de partículas con desenfoque de cine (bokeh real), estallido → vórtice → portal toroidal al ejecutar una orden, y anillo giratorio sincronizado con el bajo cuando suena música |
| 🪟 | **11 ventanas de vidrio** | `01 Archivos · 02 Entorno · 03 Canal de voz · 04 Notas · 05 Música · 06 Consola · 07 Perfil · 08 Cerebro · 09 Ayuda · 10 Modelos · 11 Optimizar` — arrastrables, minimizables al dock, con contadores en vivo |
| 👥 | **Modelos locales (Ollama)** | **10 · Modelos** enseña 14 modelos con su peso real, su flecha `↓ descargar` y el veredicto para **la RAM de este equipo** (`VA BIEN · JUSTO · NO CABE`): `usar`, `✕ borrar` y botón para encender o apagar Ollama. Descargar **no congela la interfaz**: el modelo pasa a la cola, Ollama se arranca solo si hace falta, la barra marca MB y MB/s reales, y cada descarga tiene su `✕ cancelar` |
| 🧹 | **Optimización del equipo** | **11 · Optimizar** contesta **al instante** con la RAM y quién se la come (con botón para cerrar procesos propios); lo que tarda —contar la caché del disco— se mide en un hilo aparte y se va pintando sola. Barre la caché segura sin tocar documentos, la papelera ni el escritorio |
| ⌨ | **Consola de comandos** | Prompt `cort@nave:~$`, historial con ↑/↓ y **Tab que completa** («repro» → «reproduce») |
| 📂 | **Archivos seguros** | Árbol lateral con doble conteo (carpetas · archivos) que se expande, vista rejilla/lista y botón **Abrir** que lanza la carpeta en el explorador del sistema |
| 🎵 | **Música** | Escanea `~/Música`, reproduce en el panel o abre tu reproductor (VLC) con «reproduce música» |
| 📝 | **Notas, pendientes y memoria** | «apunta …» guarda una nota; «tengo que comprar aceite» guarda una pendiente y «listo 1» la marca como hecha; **08 · Cerebro** muestra el muro de recuerdos enmarcados (notas + conversaciones) |
| 🔊 | **Te lo lee en voz alta** | «lee mis notas» · «lee mis tareas» · «lee el documento recibo» · «lee mis avisos». En el PC lo lee del backend (notas, pendientes y textos de tus carpetas seguras); en el teléfono `CORT-IA-2.4.0.apk` lee el **centro de notificaciones** — WhatsApp, Gmail, Telegram, Signal — con un oído que guarda doce líneas en RAM y se borran solas: nunca se escriben a disco. Desde el 2.4.0 el aviso **además se empuja a la cara** en el momento de llegar (`type:"aviso"`), que es lo que dejan oír las automatizaciones |
| 🎛 | **Su voz, la que elijas** | En **07 · Perfil ▸ Voz** hay tres mandos —**timbre**, **tono** (0,5 grave → 1,5 agudo) y **velocidad** (0,6 → 1,6)— y **se oyen**, porque la cara elige una de cuatro bocas por orden: la `nativa` del APK (Android `TextToSpeech`), el `navegador` (Web Speech, donde sí hay voces), el **`núcleo`** (`POST /api/voice/say` → WAV del motor local `espeak-ng`) y `muda`, que **se anuncia** en lugar de callarse. Medido en el Chromium de Linux: `getVoices()` da **0 voces** incluso con `speechSynthesis` presente, así que el portátil habla por el núcleo — sus 10 timbres se **sondean sintetizando** uno a uno al arrancar (lo que el motor no pronuncia no se ofrece: fuera mbrola y fuera las variantes ignoradas) y el `GET /api/voice` dice motor, binario y motivo si falta algo. Electron lleva `autoplay-policy=no-user-gesture-required` para que el saludo suene sin tocar nada. Guía y autodiagnóstico en dos minutos: [`docs/VOZ-DE-CORT.md`](docs/VOZ-DE-CORT.md), y la sonda con la que se tomó el dato es `scripts/sonda-voz.html` |
| 📊 | **Sensores** | CPU / RAM / disco / batería reales y clima de **la ciudad que tú digas** (Open-Meteo con su geocoder gratis, sin API key, cacheado 20 min por consulta): «¿qué tiempo hace en Gijón?», «el clima de la semana», y en **02 · Entorno** una caja donde escribir la ciudad — la guarda en **07 · Perfil** y el cerebro por voz la respeta |
| ✋ | **Gestos** | MediaPipe ligero: palma despliega/plega ventanas, pinza trae el chat, puño las cierra |
| 💡 | **Lámpara de estado** | Morado escuchando · naranja procesando · verde en línea · gris con el HUD oculto · rojo sin backend |
| 🖥 | **Pantallas** | Además del orbe hay cinco hojas a pantalla completa: **Música** y **MV** (sólo en el teléfono; MV es la del videoclip con su letra sincronizada, donde el orbe no se apaga sino que se hace disco en una esquina), **Charla** (chat normal con tus modelos de Ollama, copiar y seleccionar), **Código** (terminal + cuaderno) y **Equipo** (sólo en el teléfono: los ocho bloques de mando —Voz · Mando · Cerebro · Memoria · Atuendos · Agenda · Oído · Automatiza—). Se cambia con ☰, deslizando el dedo de lado, con `Alt+←/→` o diciéndolo. Ninguna tapa el orbe: cuando no es su pantalla, el lienzo WebGL se apaga |
| 📱 | **APK del teléfono** | **Un solo CORT**, que desde la 2.5.0 sale en **tres envases** de la misma Release —`CORT-IA-2.5.0.apk` (completo: el oído offline dentro y la superficie entera), `CORT-IA-2.5.0-nucleo.apk` (**sin la superficie privilegiada del manifiesto**: cero `BIND_*`, 21 permisos en vez de 28, medidos del binario) y `CORT-IA-2.5.0-nucleo-ligero.apk` (ese mismo núcleo sin el modelo dentro)—, los tres con la misma llave y el mismo `versionCode` **20500**, así que se instalan unos encima de otros sin perder datos; cada archivo lleva escrito su perfil (`com.cort.ia.PERFIL`) y la cara lo lee (`capacidades()`) para negarse con una frase a ofrecer lo que su manifiesto no declaró, y lo compila entero `apps/apk/compilar.sh` en GitHub Actions con el mismo método del original (`aapt2` + **`kotlinc` 1.9.24** + `javac --release 11` + `d8` + `zipalign` + `apksigner`, sin Gradle ni AndroidX), con el anillo de siempre como icono, el rol de asistente, su propio reproductor, el doble toque del auricular, la lectura de avisos, **su oído sin nube**, la **hoja Equipo** con sus ocho bloques y las diez funciones del puente 2.1 + 2.3 (volumen, linterna, alarma, voz, atuendos, burbuja, memoria y agenda, más `oidoEstado` y `oidoPropio`). Los **cerebros de casa** no abren un método nuevo: entran por `mente({que:'ollama',…})`, así que actualizar no cambia el contrato. Desde el **2.4.1** CORT se abre por **seis puertas** —el gesto del asistente (`ACTION_ASSIST`), el botón de voz del auricular (`ACTION_VOICE_COMMAND`), el **doble toque con la cara cerrada**, el **baldosín de la cortina** (`Panel`), los **tres atajos** del icono y las acciones `com.cort.ia.{ESCUCHAR,EQUIPO,CHARLA}`—: [`docs/ABRIR-CORT.md`](docs/ABRIR-CORT.md) |
| 🫛 | **Hoja Equipo: CORT manda sobre el aparato** | `☰ ▸ Equipo` o «abre el equipo», con ocho bloques y sus frases de voz: **Mando** («sube el volumen», «enciende la linterna», «pon una alarma a las 7:30», «abre whatsapp»), **Voz** («voz de siri», «cambia la voz»), **Atuendos** («ponte azul», «atuendo Cortana», «burbuja» —el punto de CORT flotando sobre otra app—), **Memoria** (SQLite del teléfono y «sincroniza con el PC»), **Cerebro** («piensa por qué está lloviendo», con la nube que ajustes tú, **35 patrones locales** que ejecutan la orden sin necesitar red y el apartado de **los cerebros gordos de tu casa**: Ollama del portátil por Wi-Fi, con sus `busca cerebros` · `modelos` · `usa el modelo …` · `descarga el modelo …` · `borra el modelo …`), **Agenda** («¿qué tengo hoy?», «revisa el correo»), **Oído** («activa el oído sin internet», «¿me oyes sin wifi?» — dice su fase real y cuánto sitio queda) y **Automatiza** (las reglas «cuando X, entonces Y», con `▶ probar ahora`). Son las diez funciones del puente 2.1 + 2.3 (`docs/CONTRATO-PUENTE-2.1.md`), y cada bloque dice en su pie si lo que falta es el APK, un permiso o el PC: **no finge haber hecho lo que no hizo** |
| 🎬 | **Pantalla MV: el video con su letra** | Hoja aparte del reproductor, en el teléfono: el videoclip se ve en la propia cara (`<video>` sobre la misma `content://` que suena), debajo va la **letra sincronizada** línea a línea con la activa marcada y **clic para saltar a ese segundo**, y el **orbe se encoge a una esquina girando como un disco** en vez de apagarse. La letra sale de LRCLIB (gratis, sin clave, cacheada); si el servidor está saturado lo dice y hay botón de **rebuscar**. En audio suelto no deja un cuadro negro: avisa y conserva la letra. |
| 🗂 | **Ordena tus archivos sin perder ni uno** | «ordena mis archivos / mis documentos / la música» o el botón **⤢ ordena** de **01 · Archivos**. Primero sale el **plan** (`de → a` con su motivo y el total) y **no se mueve nada** hasta que digas **«confirmar»**; «cancelar» deja la carpeta tal cual. El plan caduca a los quince minutos y lleva un token, así que lo que confirmas es exactamente lo que viste. `backend/app/organiza.py` no tiene ninguna primitiva de borrado: reorganiza y, si el nombre está ocupado, añade ` (2)`. |
| 🎮 | **Modo juego: CORT se aparte mientras juegas** | «modo juego» / «vuelve CORT», el interruptor de las hojas Música y MV, o el botón `CORT · PC`. Con él puesto, CORT **cierra el micrófono**, **no pide el foco audio** al reproducir y deja de hablar por el auricular: nada de robarle el turno a una partida. No necesita permiso de uso de aplicaciones ni lista de instalados — es un interruptor, no un espía. |
| 🔄 | **Que se actualice solo** | «revisa si hay actualizaciones» / «actualízate» contra la última Release de GitHub. En el escritorio baja su instalador o, si pesa más de 100 MB, deja `scripts/actualiza.sh` listo: respalda la instalación anterior en `~/Aplicaciones/CORT.anterior-<fecha>`, instala sin sudo y **no toca `~/.cort`** (claves, notas y recuerdos). En el teléfono Android no deja que una app se reemplace a sí misma: CORT te da el enlace del APK y lo pones tú encima. |
| 🎙 | **El oído no traba el teléfono** | «Oye CORT» cierra el micrófono cuando la app se va a segundo plano, cuando se apaga la pantalla, mientras suena música y mientras la ventana 11 está contando caché, y vuelve solo al pasar todo eso. Si nadie la llama, se españa cada vez más en vez de reabrir el micro cuatrocientas mil veces |
| 🎙 | **Escucha sin internet: el oído propio** | Desde `CORT-IA-2.3.0.apk` el teléfono lleva **dentro** su motor de reconocimiento: Vosk 0.3.47 con el modelo de español `vosk-model-small-es-0.42`. «Oye CORT» y las órdenes por voz funcionan **sin Wi-Fi, sin datos y sin los servicios de voz de Google** —el caso real de un teléfono sin cuenta de Google o con el juego comiéndose el micro. Se enciende y se apaga en **Equipo ▸ 7 · Oído** (o diciéndole «activa el oído sin internet», «¿me oyes sin wifi?»), y ahí se ve su fase de verdad: `preparando` · `extrayendo` · `cargando` · `listo` · `sin-sitio` · `roto`. Si el oído propio no arranca, CORT **cae solo en el reconocedor del sistema** sin que la cara note nada; el desempaque (60 MB) va en un hilo aparte y pide sitio antes de tocar nada |
| 🏠 | **Los cerebros gordos de casa (Ollama por Wi-Fi)** | Desde `CORT-IA-2.4.0.apk` el teléfono **mira al Ollama del portátil sin pasar por internet ni por una factura**: lo busca en la red de casa (`busca cerebros`), lista sus modelos con tamaño y cuantización (`modelos`), **baja uno nuevo desde el teléfono** viendo la barra moverse, lo borra, y lo elige como cerebro (`usa el modelo qwen2.5:1.5b`): desde entonces «piensa …» y las preguntas por voz se contestan con ese modelo del portátil, y la cara lo dice — la respuesta viene marcada `de:"casa"`, no `de:"nube"` (`Mente.java`, línea del proveedor). Cero permisos nuevos: el cliente es `apps/apk/src/com/cort/ia/Ollama.java` y entra por el mismo `mente` de siempre. Ollama **no cabe dentro de un APK** —es un servidor en Go—, así que lo que viaja es su cliente; el cerebro GGUF dentro del teléfono es la ronda 2.4b (`docs/CEREBROS-DE-CASA.md` explica `OLLAMA_HOST=0.0.0.0:11434` en Linux y Windows) |
| ⌨ | **La terminal del teléfono ampliada** | La pantalla **Código** tiene prompt en el celular y atiende **las mismas frases que la voz**: `ayuda` escribe los comandos disponibles, `estado` escupe lo que mide el aparato, y `busca cerebros` · `modelos` · `usa el modelo …` · `descarga el modelo …` · `mis automatizaciones` · `automatiza cuando diga … haz …` se cumplen **sin PC**. Si la línea no es ninguna de ésas, en el **PC** se manda al núcleo (`/api/command`) como siempre y en el **teléfono** se le pregunta al cerebro del aparato (`Mente`: `Cerebro`/`Razon` sin red, o el modelo de casa si lo elegiste), así que la ampliación no le quita nada a la terminal vieja |
| ⚡ | **Automatizaciones «cuando X, entonces Y»** | El modo JARVIS, dentro de la hoja **Equipo ▸ 8 · Automatiza** y por voz: «automatiza cuando diga modo noche haz callar la música». **5 disparadores** —lo que digas o escribas, un aviso que llegue (WhatsApp, Gmail…), pulsar el auricular, la batería/cargador y la hora del día— sobre **8 acciones** —hablar, volumen, linterna, abrir una app, música (callar/siguiente), pensar, apuntar un recuerdo, poner alarma—. Se puede crear todo con botones o diciéndolo, hay **tres reglas de muestra**, cada regla tiene su `▶ probar ahora` y su contador de veces que sonó, se guarda en la propia app (`localStorage`) y **no necesita red**. Cómo funciona y hasta dónde llega, en [`docs/AUTOMATIZAR-CORT.md`](docs/AUTOMATIZAR-CORT.md); el motor es puro (`ui/js/automatiza.js`) y se prueba sin teléfono con `scripts/prueba-automatiza.mjs` (45 comprobaciones con node) |
| 🤖 | **CORT como asistente** | En `CORT-IA-2.5.0.apk` (y en su `‑ligero`, que es el mismo manifiesto). **No en el `nucleo`**: ese envase tira el `VoiceInteractionService` a propósito, para pesar como el `1.1.4` que se instala, y la cara lo dice en vez de fingir. Di «pon CORT como asistente» (o usa el botón `CORT · PC` ▸ «Poner CORT como asistente») y Android abre su cuadro de rol —`RoleManager`, API 29+— para elegir CORT. El gesto del asistente, la pantalla bloqueada y el doble toque del auricular quedan entonces en CORT; el «OK Google» con la pantalla apagada se pierde, porque eso lo decide el servidor de Google. Que CORT **aparezca en esa lista** ya lo conseguía el servicio `Asistente` de 2.4.0, pero la orden que manda Android al elegirse como asistente **no llegaba a abrir el oído**: desde el 2.4.1 el manifiesto declara `ACTION_ASSIST` y `ACTION_VOICE_COMMAND` sobre `MainActivity`, y esas dos acciones encienden la escucha al abrir |
| 🚪 | **Cómo se abre CORT** | Seis puertas, todas medidas en el APK: **mantener el botón de encendido** o el gesto del asistente (rol), **el botón de voz del auricular** pulsado una vez y **doble toque** en el mismo botón (con la cara cerrada: `Reproductor` pausa la música antes de abrir el micro, para que el oído no transcriba la canción), **el baldosín «CORT escucha» en la cortina de ajustes rápidos** —con el teléfono bloqueado usa `unlockAndRun` y abre tras el desbloqueo—, **mantener pulsado el icono** para los tres atajos (Escucha · Equipo · Charla, que saltan directo a esa hoja), y **abrir la app** y hablar. Cada puerta lleva su comprobación en el sector **[12]** de `scripts/prueba-costura.py`. Pasos por marca (Samsung, Xiaomi, Motorola) y qué se comprueba desde el repo: [`docs/ABRIR-CORT.md`](docs/ABRIR-CORT.md) |
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
| **Android (APK del teléfono)** | instala **primero** [`CORT-IA-2.5.0-nucleo.apk`](https://github.com/Sandra2244/CORT/releases/latest) (el envase sin superficie privilegiada: 21 permisos y cero `BIND_*` leídos de su manifiesto binario) si Play Protect te bloquea el de siempre; [`CORT-IA-2.5.0.apk`](https://github.com/Sandra2244/CORT/releases/latest) es el completo, y [`…-nucleo-ligero.apk`](https://github.com/Sandra2244/CORT/releases/latest) el núcleo sin el modelo de 39,8 MB dentro. `bash scripts/instala-apk.sh --nucleo` baja el primero por USB · `bash scripts/instala-apk.sh` | un solo CORT, ahora en dos envases: el anillo de siempre, las once ventanas, su reproductor, sus pantallas, su **oído sin internet** (sólo en el completo), el rol de asistente **con sus vías de arranque ya declaradas** (gesto, botón de voz del auricular, baldosín de la cortina, atajos del icono), los **cerebros de casa por Wi-Fi** y las **automatizaciones**. Los dos se **instalan encima** del `2.0.0` … del `2.4.1` sin desinstalar y sin perder el micrófono concedido, los gustos guardados ni la dirección del PC escrita a mano: misma llave de firma (`fa:ab:ef:46…`, medida en los dos `-firma.txt`) y `versionCode` mayor (**20402** > 20401), y como comparten `versionCode` —el número no baja, luego no es bajada—, el completo y el ligero se pueden poner **el uno encima del otro** como reinstalación sin desinstalar nada; si el instalador de tu marca pusiera una pega con el mismo número de versión, se desinstala una vez y se deja el que quieras seguir usando. Si **vienes de un 1.x** da `INSTALL_FAILED_UPDATE_INCOMPATIBLE` —son dos llaves distintas, medidas—: hay que desinstalar una vez; desde el 2.0.0 la llave ya no cambia. **Ojo al sitio del teléfono, no a la RAM**: el completo pesa **47.390.449 B** (45,2 MB) —mismo número de bytes que el `2.4.1`, pero otro archivo: el `sha256` cambió (`39a5a7d0…82b2e3`) porque el código crece 191 B en crudo y la holgura de alineado lo absorbe— y el ligero **1.621.264 B** (1,5 MB); en el primer arranque el oído del completo desempaca el modelo (60.286.598 B sueltos) en su carpeta privada, y si no cabe CORT dice `sin-sitio`, no escribe nada, y sigue funcionando con el reconocedor del sistema (en el ligero dice `sin-modelo` desde el principio, porque el modelo no viaja dentro). Los pasos del teléfono y la tabla de errores de Android, en [`docs/INSTALAR-APK.md`](docs/INSTALAR-APK.md); cómo se abre CORT por las seis vías y qué tocar en cada marca, en [`docs/ABRIR-CORT.md`](docs/ABRIR-CORT.md); y si el que aparece es un **aviso de Google o Play Protect** («aplicación bloqueada para proteger tu dispositivo», «no reconoce esta aplicación», «puede dañar tu dispositivo», Chrome no deja descargar), la tabla por frase exacta, **la bisección de esta ronda y qué decide cada resultado** está en [`docs/BLOQUEO-PLAY-PROTECT.md`](docs/BLOQUEO-PLAY-PROTECT.md) |
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

| Archivo | Tamaño y superficie **medidos en este portátil** sobre los archivos bajados de `v0.2.29-demo` (2026-10-22) | Para |
|---|---|---|
| `CORT.Setup.0.2.0.exe` | 79.047.129 bytes (75,4 MB) | Windows 10/11 64 bits (instalador NSIS, eliges carpeta) |
| `CORT-0.2.0.AppImage` | 107.793.760 bytes (102,8 MB) | Linux genérico (ejecutable directo) |
| `cort-desktop_0.2.0_amd64.deb` | 74.898.442 bytes (71,4 MB) | Debian / Ubuntu / Mint |
| `CORT-IA-2.5.0.apk` | **47.394.545 bytes** comprimidos sobre 61.923.190 sin comprimir, **49 entradas**, proporción **0,77** — `sha256` `245fd423391f0a4c5b440aa112404bef79aee4de7e4d60c46726135e3a4e20f4`, descargado y hasheado aquí: exacto a su hoja, CRC de las 49 entradas íntegro. **Manifiesto binario leído del `.apk`: 28 permisos y 4 servicios `BIND_*`** (asistente, reconocedor, avisos, baldosín), `perfil declarado: completo`, cuatro `.so` y el modelo dentro | Android 8+: el **COMPLETO** de siempre (`versionCode` 20500). Once ventanas de vidrio, rol de asistente del sistema (`ACTION_ASSIST`, `ACTION_VOICE_COMMAND`), **baldosín en la cortina** (`.Panel`), **tres atajos del icono**, **doble toque de auricular con la cara cerrada**, reproductor propio con gustos y playlists, lectura de avisos, llamadas y agenda, **MV con letra sincronizada**, **organizador de archivos con plan y confirmación**, **modo juego**, la **hoja Equipo**, el cerebro `Razon` (**283 frases** en 33 reglas), el **oído propio sin nube** (Vosk 0.3.47 con el modelo dentro), los **cerebros de casa** por Wi‑Fi (`Ollama.java`), la **terminal ampliada** y las **automatizaciones** «cuando X, entonces Y». Guías: [`docs/ABRIR-CORT.md`](docs/ABRIR-CORT.md), [`docs/CEREBROS-DE-CASA.md`](docs/CEREBROS-DE-CASA.md), [`docs/AUTOMATIZAR-CORT.md`](docs/AUTOMATIZAR-CORT.md) y, si sale un aviso de Google, [`docs/BLOQUEO-PLAY-PROTECT.md`](docs/BLOQUEO-PLAY-PROTECT.md) |
| `CORT-IA-2.5.0-nucleo.apk` | **47.394.545 bytes** comprimidos —los mismos que el completo, y **no es el mismo archivo**: `sha256` `761d9bee5f7976ac899f5cb382921984977d71d28bdf7f30edd6482ade22564c`, 61.919.778 bytes sin comprimir (3.412 menos, exactamente la diferencia de manifiesto)—, 49 entradas, CRC íntegro. **Manifiesto binario: 21 permisos y CERO `BIND_*`**, un solo `<service>` (`.Reproductor`), `perfil declarado: nucleo`; su `AndroidManifest.xml` pesa **12.636 B** frente a los 16.048 B del completo | Android 8+: el **NÚCLEO** — **empieza por éste**. El mismo CORT sin la superficie que delata un escáner: cero rol de asistente, cero listener de notificaciones, cero baldosín, cero `CALL_PHONE`/`READ_CONTACTS`/`READ_CALENDAR`. Cara, orbe, chat, código, cerebro, automatizaciones, reproductor con su doble toque, micro, sensores, gestos y Wi‑Fi con los cerebros de casa **se quedan todos**. La app sabe qué lleva dentro (`capacidades()`) y lo que no está declarado se niega con una frase en vez de con un botón mudo |
| `CORT-IA-2.5.0-nucleo-ligero.apk` | **1.621.264 bytes** (1,5 MB) comprimidos sobre 4.488.815 sin comprimir, **44 entradas**, `sha256` `344f8853034b349a5a0a4a035e728280d9060dcfc7b169cf1fb97a5c75edde30`, descargado y hasheado aquí: **cero** entradas `lib/*.so` y **cero** `assets/motor/`. Su `AndroidManifest.xml` binario es **byte a byte el del núcleo** (los dos, 12.636 B y `sha256` `b61c275d3df963a9…`): la variedad no toca el manifiesto, el perfil no toca el peso | Android 8+: el **NÚCLEO sin el oído offline dentro**. El segundo envase de la bisección: si el núcleo no entra y éste sí, el sospechoso que queda es el modelo de 39.817.833 B y se saca del APK |
| `CORT-IA-2.5.0-firma.txt` · `…-nucleo-firma.txt` · `…-nucleo-ligero-firma.txt` | 3.851 · 3.746 · 4.064 bytes | con qué llave salió cada uno (huella `faabef468f3a…`, **la misma del 2.0.0 en adelante**, así que los tres se instalan encima del CORT que ya tienes y unos encima de otros), si se puede instalar encima, **qué perfil y qué variedad es** cada archivo, y la **auditoría leída del binario**: `sha256`, peso, esquemas v1/v2/v3, ventana del certificado, `resources.arsc` alineado, `minSdk`/`targetSdk`, el **conteo de permisos y `BIND_*` del manifiesto binario**, el `perfil declarado` y el veredicto `INSTALABLE` — con el **pipeline puesto rojo** si un `nucleo` saliera con algún servicio privilegiado dentro |

> Los tamaños del escritorio son los que declara la API pública de Releases de esta
> etiqueta, no una estimación.
>
> **En `v0.2.29-demo` (la 2.5.0) hay TRES APK de Android a propósito, y los tres
> bajados, hasheados y leídos por dentro en este portátil.** La medida que abre la ronda
> es la suya: «los dos fallan, Play Protect sigue bloqueando». Con eso el peso y las `.so`
> quedan **fuera de la lista por medida**, no por teoría —el ligero de la 2.4.2 son
> 1.621.264 B, cero `.so`, cero modelo, y se bloquea igual que el de 47 MB—, y lo único que
> quedaba por mirar era lo que el archivo **declara**. Así que se contó la charca UTF‑16 del
> `AndroidManifest.xml` binario de los tres APK que hay en el mismo disco: `1.1.0` → **13
> permisos y 0 servicios `BIND_*`** (entra); `1.1.4` → **13 y 0** (entra); `2.4.2-ligero` →
> **28 y 4 `BIND_*` en cinco servicios** (bloqueado). Los cuatro gordos
> (`MANAGE_EXTERNAL_STORAGE`, `SYSTEM_ALERT_WINDOW`, `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`,
> `READ_EXTERNAL_STORAGE`) están en **los tres**: nunca fueron la diferencia. Lo que sólo
> tienen los 2.x es la **superficie de integración** — asistente del sistema, reconocedor de
> voz, listener de notificaciones, baldosín, llamar y leer contactos y calendario —, que es
> la firma con la que un escáner sin contexto describe un troyano de accesibilidad.
>
> La Release baja entonces el mismo CORT en tres envases, con la misma llave y el mismo
> `versionCode` **20500**, y medidos aquí: el **completo** (47.394.545 B, manifiesto de
> 28 permisos y 4 `BIND_*`), el **núcleo** (47.394.545 B comprimidos también, pero otro
> archivo: `sha256` distinto, 3.412 B menos sin comprimir, y su manifiesto binario dice
> **21 permisos y CERO `BIND_*`**, un solo servicio) y el **núcleo‑ligero** (1.621.264 B,
> cero `.so`, cero modelo, y su manifiesto es **byte a byte el del núcleo**: 12.636 B y
> `sha256` `b61c275d3df963a9…` en los dos). Las dos variables quedan separadas y cada
> archivo lleva dentro escrito su perfil para que la cara no prometa lo que su manifiesto
> no declaró. **Dos minutos en el teléfono deciden la ronda que viene**: si entra el núcleo
> y no el completo, era la superficie; si sólo entra el núcleo‑ligero, se suma el modelo y
> sale del APK; si no entra ninguno, dentro del archivo no queda nada que cambiar.
> La prueba escrita, los números medidos y qué pulsar según la frase exacta:
> [`docs/BLOQUEO-PLAY-PROTECT.md`](docs/BLOQUEO-PLAY-PROTECT.md).
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
> **Y el `2.4.0` crece lo que crecen sus funciones: +20.552 bytes.** El `-firma.txt`
> de `v0.2.24-demo` y el de `v0.2.25-demo` miden el mismo desglose sobre el APK final,
> así que la comparación es pública: `classes*.dex` pasa de 782.365 a **789.070 B**
> (los 6.705 de `Ollama.java`, con su barrido de red por `NetworkInterface`, y de
> `CortNative.avisoEnLaCara`) y la cara de 370.872 a **387.793 B** (los 16.921 de
> `automatiza.js` y el bloque 8 de la hoja Equipo). El modelo del oído
> (**39.817.833 B**), las cuatro `.so` (**5.868.445 B**) y los recursos (**511.860 B**)
> quedan como estaban: no se metió ni un byte que no haga algo. Las entradas pasan de
> 47 a **48** — la nueva es `assets/ui/js/automatiza.js`, leída dentro del APK ya
> publicado, y su motor trae **5 disparadores y 8 acciones**, contado sobre el archivo
> del Release.
>
> **El `2.4.1` es la ronda más barata de las cinco: +4.160 bytes** (47.386.289 →
> **47.390.449**, medidos en los dos `-firma.txt` publicados). Las cinco puertas nuevas
> no meten ni una librería ni un asset gordo: `classes*.dex` pasa de 789.070 a
> **790.593 B** (+1.523 — `.Panel`, el `MediaSession` de `.Reproductor` respondiendo
> `onMediaButtonEvent`, el router `abreLoQueToque` de `MainActivity` y el evento `atajo`
> de `CortNative`), la cara de 387.793 a **388.238 B** (+445 — `escuchaAtajos` en
> `pantallas.js`) y recursos de 511.860 a **513.563 B** (+1.703 — las tres acciones del
> manifiesto, el servicio del baldosín y `res/xml/atajos.xml`, que mide 531 B comprimido).
> Las entradas pasan de 48 a **49**; la nueva es `res/xml/atajos.xml`, leída dentro del APK
> publicado. El modelo del oído (**39.817.833 B**) y las cuatro `.so` (**5.868.445 B**)
> no se mueven, y los **489 B** que faltan por contar son el bloque de firma v2/v3 del
> contenedor (11.288 → 11.777), no contenido nuevo.
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
| `CORT-IA-2.5.0.apk`, `CORT-IA-2.5.0-nucleo.apk` y `CORT-IA-2.5.0-nucleo-ligero.apk` | Java + **Kotlin 1.9.24** sin Gradle (`aapt2` + `kotlinc` + `javac --release 11` + `d8` + `zipalign` + `apksigner`), con el holograma del repo embebido bajo `https://cort.local` y su puente de voz propio (`CortNative.java`). Lleva el **anillo de siempre** como icono —`compilar.sh` saca los cinco `mipmap-*` y el XML adaptativo del `base/CORT-IA-1.1.0.apk`, no lo dibuja nadie—, el traje de `VoiceInteractionService` para **ser el asistente predeterminado** (las dos primeras funciones viven en las tres regiones que `apps/apk/perfil.py` recorta para el envase `nucleo`: el mismo código, manifiesto distinto), `MediaSession` para el **doble toque del auricular** —y desde el 2.4.1 el de `.Reproductor` responde `onMediaButtonEvent`, así que el doble toque también funciona con la cara cerrada y para la música antes de abrir el micro—, un `TileService` (`.Panel`) para el **baldosín de la cortina**, `ACTION_ASSIST`/`ACTION_VOICE_COMMAND` declarados sobre `MainActivity` para que **el gesto del asistente y el botón de voz del auricular abran el oído**, y `res/xml/atajos.xml` para los **tres atajos del icono**, `Avisos` (`NotificationListenerService`) que **lee en voz alta lo que llega** y desde el 2.4.0 **lo empuja a la cara** (`CortNative.avisoEnLaCara`), **su propio reproductor** (`.Reproductor`, un servicio en primer plano con `foregroundServiceType="mediaPlayback"`: biblioteca leída de `MediaStore`, gustos que se aprenden con 👍/👎, listas guardadas, avance/retroceso y **cuadro a cuadro** en vídeo, todo en segundo plano sin trabar el teléfono), **`Oido.kt`** (Vosk 0.3.47 + JNA + el modelo de español dentro del APK, con el micro abierto en su propio hilo, `extractNativeLibs="true"` para que las `.so` viajen comprimidas, y **un solo `stt-end` por escucha** para que el «Oye CORT» no se rearme doble), el cliente de **Ollama por Wi-Fi** (`Ollama.java`, entra por `mente`, cero permisos nuevos) y la **terminal ampliada** con las reglas «cuando X, entonces Y» (`ui/js/automatiza.js`, en la cara). | `apps/apk/compilar.sh` → la Release |

La vía de **rempaquetar** el binario original (`rempaquetar.sh`) está borrada del
repo y del workflow. Existía porque el proyecto Gradle que generó el `1.1.0`
nunca estuvo en este repo —lo guardado era el binario
(`instaladores/CORT-IA-1.1.0.apk`, SHA-256 `b5fa07fa…`)— y lo único que se le
podía cambiar era la cara. Ese camino daba dos APK que había que saber elegir, y
la dueña lo pidió claro: **todo dentro del que se compila**. Lo que se conserva
del binario es su icono, que es lo que lo hace «el de siempre».

Qué es verdad y qué no, dicho sin adornos:

- **El reproductor, la música, las llamadas, el oído sin nube, la linterna, la
  alarma, los atuendos y las automatizaciones funcionan en el teléfono sin PC**;
  las ventanas 10 · Modelos, 11 · Optimizar y la pantalla **Charla** necesitan el
  backend del portátil, porque piden `/api/*`. Sin PC no inventan una respuesta:
  la cara traduce el `501` del `MainActivity` y lo dice en voz alta. `MainActivity`
  intercepta `/api/*` a propósito.
- **La pantalla Código no abre un shell en Android, y eso sigue siendo verdad.**
  Desde el 2.4.0 la terminal del teléfono atiende **aquí** las órdenes del puente
  (volumen, linterna, alarma, apps, memoria, voz, atuendo, agenda, `busca cerebros`,
  `modelos`, `usa el modelo …`, las reglas) y, si la línea no es una orden, se la
  pregunta al cerebro del aparato. Lo demás se manda al núcleo del portátil
  (`/api/command`) y lo que ves es lo que hizo tu PC. Prometer un terminal que
  «arregla el teléfono» sería mentira.
- **Los cerebros gordos de casa necesitan el portátil encendido.** Ollama no cabe
  dentro de un APK —es un servidor en Go—, así que `Ollama.java` habla con el de tu
  PC por la Wi-Fi: hay que dejarlo escuchando fuera (`OLLAMA_HOST=0.0.0.0:11434`) y
  el equipo delante. Lo que sí piensa sin nada es el cerebro del propio teléfono
  (`Cerebro` con sus 35 patrones que **ejecutan** la orden y `Razon` con las
  cuentas, porcentajes, unidades y fechas).
- **Las reglas «cuando X, entonces Y» se cumplen mientras CORT está en pantalla.**
  El motor vive en la cara, no en un servicio de fondo: con CORT cerrado no hay
  frase que oír ni hora que mirar (lo que sí sigue sonando con la pantalla apagada
  es `.Reproductor`, y `.Avisos` sí lee la barra porque es un `NotificationListenerService`
  del sistema). Es una limitación dicho en seco, no un detalle, y está escrita así en
  [`docs/AUTOMATIZAR-CORT.md`](docs/AUTOMATIZAR-CORT.md); el motorcito de fondo para
  que las reglas funcionen con CORT cerrado es el siguiente paso natural.
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
| `GET /api/weather?lugar=` | Clima actual (Open-Meteo, cacheado 20 min); con `lugar` busca la ciudad y sin él usa la IP |
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
| `ui/js` | Además del HUD: `telefono.js` es la hoja Equipo del celular y su router de voz, `pantallas.js` las hojas a pantalla completa y `automatiza.js` el motor puro de las reglas «cuando X, entonces Y» (sin DOM: se prueba con node) |
| `apps/apk/` | El proyecto Android sin Gradle: Java puro + `compilar.sh` — el único APK que sale (asistente, avisos, reproductor propio, llamadas, oído sin nube, el cliente de **Ollama por Wi-Fi** y las automatizaciones) —, `llave.sh` para la firma estable, `prueba/` con las suites que corrigen contra un Ollama de mentira dentro del JDK y `base/` con el binario viejo sólo para tomar su icono. Lo compila Actions, nunca tu PC |
| `docs/` | `PLAN-CORT.md` (arquitectura y pendientes), `CONTRATO-PUENTE-2.1.md` (qué sabe hacer el puente y qué evento trae cada cosa), `INSTALAR-APK.md`, `BLOQUEO-PLAY-PROTECT.md` (qué pulsar según la frase que sale), `CEREBROS-DE-CASA.md` (Ollama por Wi-Fi paso a paso), `AUTOMATIZAR-CORT.md` (las reglas), `VOZ-DE-CORT.md` (qué boca usa cada equipo y cómo se cambian timbre, tono y velocidad) y los fotogramas de referencia |
| `scripts/` | `run.sh` (Linux/macOS), `run.bat` (Windows), `run-desktop.sh` (Electron), `instalar-linux.sh` (app instalada), `telefono.sh` (Wi-Fi), `instala-apk.sh` y `audita-apk.sh` (descarga y audita el APK publicado), y las comprobaciones: `prueba-lectura.py`, `prueba-costura.py` (los sectores que cosen cara ↔ puente), `prueba-mente.sh` (las suites Java, incluido `Prueba4`), `prueba-oido.sh` y `prueba-automatiza.mjs` (el motor de reglas, con node). Todas en sandbox, sin tocar tus carpetas y sin teléfono |
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
- [x] **F7** Android: **un solo CORT** en la Release — los tres envases de la 2.5.0 (`CORT-IA-2.5.0.apk`, `‑nucleo.apk` y `‑nucleo-ligero.apk`), que compila `apps/apk/compilar.sh` desde cero en Java + Kotlin y sin Gradle. Es el asistente predeterminado (rol por `RoleManager`), escucha el doble toque del auricular (`MediaSession`), lee en voz alta los avisos que llegan (`Avisos.java`, un `NotificationListenerService` que sólo guarda doce líneas en RAM), trae el anillo de siempre como icono (sacado de `base/CORT-IA-1.1.0.apk`) y lleva dentro su propio reproductor (`.Reproductor` + `Musica.java`: biblioteca, gustos, playlists y cuadro a cuadro en vídeo) y el marcador de contactos (`Telefono.java`). La vía de `rempaquetar.sh` está borrada del repo y del workflow: dos APK que había que elegir era trabajo doble y lío para instalar
- [x] **F7a** Voz que lee: «lee mis notas / mis tareas / mis avisos / el documento …» — notas y pendientes en SQLite (`memory.py`), textos de las carpetas seguras (`sensors.leer_texto`) y avisos del teléfono por la barra de notificaciones. Comprobado sin teléfono con `scripts/prueba-lectura.py` y `scripts/prueba-costura.py`
- [x] **F7c** Pantallas aparte del orbe (`ui/js/pantallas.js`): **Charla** (chat con burbujas, modelos de Ollama, copiar y guardar en Notas), **Código** (terminal contra `/api/command` + cuaderno de código), **Música** y **MV** en el teléfono. Se cambia con ☰, deslizando, `Alt+←/→` o por voz, y el orbe se apaga cuando no le toca para no gastar GPU ni batería — con la excepción de **MV**, donde se encoge a una esquina girando como disco.
- [x] **F7e** La ronda 2.1, «todo lo prometido dentro del APK»: nueve clases Java nuevas (`Acciones`, `VozNueva`, `Recuerdos`+`Sincroniza`, `Mente`+`Nube`+`Cerebro`, `Paleta`, `Agenda`, `Flotante`, `ArchivosProvider`) que sacan las **ocho funciones del puente** (`accion`, `ajusteVoz`, `memoria`, `mente`, `atuendo`, `agenda`, `burbuja`, `comparte`), la hoja **Equipo** con sus seis bloques, el **cerebro sin portátil** (la nube que ajustes tú, con la clave sin salir del teléfono, y 35 patrones locales que **ejecutan** la orden que reconocen), la **burbuja flotante**, la **linterna**, la **agenda de sólo lectura** y el **enviar archivo** con el proveedor del APK. Contrato en `docs/CONTRATO-PUENTE-2.1.md`; cosido y comprobado en los cuatro sitios con `scripts/prueba-costura.py` (9 sectores, sin teléfono)
- [x] **F7f** La ronda 2.3, **el oído propio dentro del teléfono**: `apps/apk/src/com/cort/ia/Oido.kt` (Kotlin, primer `.kt` del repo) desempaca `vosk-model-small-es-0.42` en `filesDir/motor` con su marca de versión, abre el micro en su propio hilo y habla con `libvosk.so` por JNA. **Sin `SpeechService` ni `StorageService`** de Vosk: el primero se come un `RuntimeException` del buffer y tumba el proceso, y el segundo pide `res/raw` con `AssetFileDescriptor`, que los assets comprimidos de `aapt2` no dan. `CortNative.java` lo engancha en un solo cuello de botella (`arrancarEscucha()` prueba el oído y, si no, cae en el `SpeechRecognizer` de Google), así que el bucle «Oye CORT», los frenos, el modo juego y la insignia del auricular siguen intactos; la hoja **Equipo** estrena el bloque **7 · Oído** con su fase en español, su interruptor y sus preguntas por voz. El pipeline gana `kotlinc` 1.9.24 (con su caché), la caché del motor, y una prueba que **carga el modelo de verdad** (`scripts/prueba-oido.sh`, seis comprobaciones) antes de compilar: ahí salió que `cancela()` mandaba un segundo `stt-end`. Peso medido: **47.365.737 B** (45,2 MB), de los que 39.817.833 son el modelo y 5.868.445 las cuatro `.so`; `.dex` 782.365 B, cara 370.872 B. Firma la misma `fa:ab:ef:46…` de siempre, así que se instala encima del `2.2.0` sin perder datos.
- [x] **F7g** La ronda 2.3.1, **que se pueda instalar**: la dueña reportó que Google / Play Protect le bloqueaba el APK. Se bajó el `CORT-IA-2.3.0.apk` publicado y se leyó byte a byte: sale con **v1+v2+v3**, certificado vigente hasta 2056, `resources.arsc` sin comprimir y alineado, CRC íntegro — o sea, **el APK no estaba roto**; era el aviso que Play Protect da a cualquier app auto-firmada fuera de Play, que no se quita desde el repo. Lo que sí se hizo: pedir los **tres esquemas con bandera explícita** (con `minSdk 26` la v1 viene desactivada por defecto y la v3 sólo se activa sola con `minSdk >= 28`; ya no dependemos del default del runner), y publicar en cada `-firma.txt` la **auditoría de instalabilidad** que hace `scripts/audita-apk.sh` sobre el APK final — `sha256`, peso, esquemas, ventana del certificado, `resources.arsc`, `.so`, `minSdk`/`targetSdk` y que no esté marcado como depurable — con **el pipeline poniéndose rojo** si algo de eso falla. Además: `scripts/instala-apk.sh` ahora **compara el sha256** del archivo descargado contra la hoja, traduce los errores de certificado y de Play Protect, y la guía nueva [`docs/BLOQUEO-PLAY-PROTECT.md`](docs/BLOQUEO-PLAY-PROTECT.md) dice **qué pulsar según la frase exacta** que sale en pantalla (incluido el aviso de que el certificado empieza el 2026-10-21 11:19 GMT: con el reloj del teléfono atrasado, Android lo ve «aún no válido»). Medido en la Release `v0.2.24-demo`: `CORT-IA-2.3.1.apk` **47.365.737 B**, `versionCode` 20301, `sha256` `68dce453…8ebb5` — el mismo archivo bajado en el portátil hashea exacto —, misma llave `fa:ab:ef:46…` y `-firma.txt` de 3.427 B.
- [x] **F7h** La ronda 2.4, **el cerebro de casa y el modo JARVIS** (lo que la dueña pidió: «que CORT sí pueda instalar modelos locales de Ollama, que la terminal se amplíe en el teléfono y funcione con esos cerebros, y la automatización como JARVIS o Cortana»). Tres cosas, todas dentro del APK de siempre: (1) **`Ollama.java`**, el cliente del servidor de tu PC por Wi-Fi —descubre, lista con tamaño y cuantización, **baja un modelo desde el teléfono** con su barra, lo borra, lo fija como cerebro—; el servidor **no cabe en un APK** (es Go y pide un ordenador), así que viaja su cliente, entra por el `mente` de siempre y **no pide ningún permiso nuevo**. Se probó sin teléfono ni internet con `apps/apk/prueba/Prueba4.java`: un Ollama de mentira montado dentro del propio JDK (`jdk.httpserver`), **36 comprobaciones** del diálogo HTTP, y ya va en el pipeline (`scripts/prueba-mente.sh`). (2) **La terminal ampliada del teléfono**: `terminalTelefono(orden, escribe)` en `ui/js/telefono.js`, montada delante del `/api/command` en la pantalla Código, de modo que `ayuda`, `estado`, `busca cerebros`, `modelos`, `usa el modelo …`, `descarga el modelo …` y las reglas se cumplen escribiendo **sin portátil**, y lo que no es orden del puente se pregunta al cerebro del aparato con `espejo` para que la respuesta vuelva a la misma terminal. (3) **Las automatizaciones**: `ui/js/automatiza.js`, motor puro (sin DOM, sin `localStorage` al importar) con **5 disparadores** —frase, aviso, auricular, batería/cargador, hora—, **8 acciones** —habla, volumen, linterna, abrir, música, piensa, recuerdo, alarma—, freno de un minuto por regla, cooldown diario en `hora`, persistencia en `cort.autos.v1`, bloque **8 · Automatiza** en la hoja Equipo, creación **por voz** («automatiza cuando diga modo noche haz callar la música»), tres reglas de muestra, `▶ probar ahora` y contador de veces que sonó. Para que el disparador de avisos funcione hace falta que Java los empuje: `Avisos` → `MainActivity.front().puente().avisoEnLaCara()` → evento `type:"aviso"` (cero permisos nuevos, y si no hay pantalla abierta no hace nada). Probado con `scripts/prueba-automatiza.mjs` (**45 comprobaciones** con node: acentos, substrings, frenos, `-1` de batería no tragado, una sola vez al día, almacén corrupto, motor sin almacén) y con el sector **[11]** de `scripts/prueba-costura.py`, que comprueba que cada acción declarada tenga su `case` ejecutor, que cada señal exista de verdad en el puente y que ningún `eq-aut-*` quede sin dueño. Guía: [`docs/CEREBROS-DE-CASA.md`](docs/CEREBROS-DE-CASA.md) y [`docs/AUTOMATIZAR-CORT.md`](docs/AUTOMATIZAR-CORT.md). Firma la misma `fa:ab:ef:46…`, `versionCode` 20400 → se instala encima del 2.3.1 sin perder datos. Medido en la Release `v0.2.25-demo` (2026-10-22): `CORT-IA-2.4.0.apk` **47.386.289 B**, `sha256` `ee5eb11f…d8b57a` — el archivo bajado en el portátil hashea exacto —, 48 entradas, `-firma.txt` de 3.493 B con el veredicto `INSTALABLE` (v1+v2+v3, `resources.arsc` sin comprimir y alineado, no depurable) y el run **en verde con los tres pasos de prueba**: las 4 suites Java del JDK (`Prueba4` incluidas), las 45 de node y el oído con Vosk de verdad. **Falta (2.4b): el cerebro GGUF dentro del teléfono** —tarea #79—, que necesita cruzar-compiler llama.cpp con el NDK dentro del pipeline.
- [x] **F7i** La ronda 2.4.1, **que se abra por todos lados y que la oiga el auricular** (lo que la dueña pidió: «que se pueda instalar sin problemas, que lo detecte como aplicación de Asistente para colocarla como predeterminada en vez de Google, y que funcione con los audífonos con los mismos botones, sensores de doble toque, el hablar por audífonos, CORT ejecute las acciones, etc., que inicie de otras formas»). Cinco vías nuevas + un arreglo de honestidad, todas dentro del mismo APK y con la misma llave: (1) **el asistente de verdad despierta a CORT** — el `VoiceInteractionService` de 2.4.0 la ponía en la lista del rol, pero la orden que manda Android **no llegaba**: el manifiesto declara ahora `ACTION_ASSIST` y `ACTION_VOICE_COMMAND` sobre `MainActivity`, y `abreLoQueToque` enciende el oído cuando llega una de esas dos (o `com.cort.ia.ESCUCHAR`). (2) **Baldosín en la cortina de ajustes rápidos**: `apps/apk/src/com/cort/ia/Panel.java`, un `TileService` (`BIND_QUICK_SETTINGS_TILE`, icono monócromo `ic_btn_speak_now`) que abre CORT escuchando; con el teléfono bloqueado usa `unlockAndRun` y abre después del desbloqueo, y si el fabricante no deja, cae en `startActivityAndCollapse` y por último en `startActivity` — un baldosín mudo es mejor que un asistente que revienta. (3) **Tres atajos al mantener pulsado el icono** (`res/xml/atajos.xml` + `res/values/etiquetas.xml`): Escucha · Equipo · Charla, que saltan directo a su hoja; los etiquetas tienen que ser `@string/…` o el `ShortcutPackage` del sistema tira el atajo. (4) **El doble toque del auricular funciona con la cara cerrada**: `.Reproductor` tenía `MediaSession` pero no respondía `onMediaButtonEvent`, así que se queda `MainActivity` y su sesión ya no existía cuando CORT no estaba delante; ahora el reproductor detecta el doble toque (`MainActivity.teclaDe`, reutilizada), **pausa la música antes de abrir el micro** para que el oído no transcriba la canción, y reutiliza la misma ventana de 500 ms. La voz de CORT ya salía por el auricular: va por el stream multimedia, medido con `isMusicActive()` en `CortNative.musicPlaying()`. (5) **Acciones propias** `com.cort.ia.{ESCUCHAR,EQUIPO,CHARLA}`, comprobables sin tocar la pantalla con `adb shell am start -a com.cort.ia.EQUIPO`. Para que la cara cambiara de hoja desde Java hizo falta un evento nuevo en el puente: `type:"atajo"` → `escuchaAtajos()` en `ui/js/pantallas.js`, que valida el id contra las hojas **visibles** antes de saltar y si no existe lo dice en la terminal en vez de fingir. Costura nueva: **sector [12]** de `scripts/prueba-costura.py`, que comprueba que cada acción declarada tenga su constante, que el baldosín tenga su permiso, que las tres etiquetas sean `@string/`, que el `hojaDe` del router apunte a hojas reales de la cara, y que nadie escriba `unlockAndRun(candidato)` (recibe un `Runnable`, no un `PendingIntent`). **Publicado verde en `v0.2.27-demo`** (2026-10-22) tras fallar una vez en `v0.2.26-demo` justo por esa firma: `Panel.java:73: error: incompatible types: PendingIntent cannot be converted to Runnable`, cazado por el pipeline y arreglado hacia adelante, sin reutilizar la etiqueta. Medido en la Release: `CORT-IA-2.4.1.apk` **47.390.449 B** (48.→49 entradas, +4.160 sobre el 2.4.0), `sha256` `ed5761f3e9964fd8…0908a6df` — el archivo bajado en el portátil hashea exacto y las 49 CRC pasan —, `versionCode` **20401**, llave `fa:ab:ef:46…` **sin cambiar**, `-firma.txt` de 3.493 B con veredicto `INSTALABLE` (v1+v2+v3, `resources.arsc` sin comprimir y alineado, no depurable). Antes de etiquetar: `prueba-costura.py` en verde con sus doce sectores, 45/45 de node, las 4 suites Java del JDK, y el parseo de los `.java` nuevos con `java -m jdk.compiler/com.sun.tools.javac.Main`. Guía de las seis puertas, qué tocar en Samsung/Xiaomi/Motorola y **qué se comprueba desde el repo y qué no**: [`docs/ABRIR-CORT.md`](docs/ABRIR-CORT.md). **Falta, dicho en vez de fingido**: la palabra de activación con la pantalla apagada sigue siendo del DSP del sistema (no se puede tener sin el rol y sin el permiso de escucha permanente que ella no quiere), el enrutado Bluetooth SCO del micrófono no está hecho, y el aviso de Play Protect al instalar un APK firmado por una llave propia **no se quita desde el repo** — se aguanta con los pulsos de [`docs/BLOQUEO-PLAY-PROTECT.md`](docs/BLOQUEO-PLAY-PROTECT.md).
- [x] **F7j** La ronda 2.4.2, **cazar el bloqueo de Play Protect por bisección** (lo que la dueña trajo: «dice todo el tiempo «aplicación bloqueada para proteger tu dispositivo» … pero el apk original 1.1.1 sí, o el 1.1.4 que ese tú lo hiciste y puedo instalarlo … la idea es desarrollar, agregar cosas, ir probando, por eso me gustaría que se pueda actualizar, instalar un paquete encima de otra cosa»). Primero se **midió** en vez de repetir el «es por ser auto-firmado»: el `CORT-IA-1.1.4.apk` que a ella le se instala tiene los **mismos permisos gordos** leídos de su `AndroidManifest.xml` binario (`MANAGE_EXTERNAL_STORAGE`, `SYSTEM_ALERT_WINDOW`, `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`), está firmado con una llave propia distinta (`EB:D6:25:04…`) y **no lleva ni una `.so`** (1.756.727 B); el 2.x bloqueado lleva cuatro `.so` y 39,8 MB de modelo (47.390.449 B). Caen entonces las dos explicaciones cómodas y queda como único sospechoso el **bulto nativo**, así que el pipeline compila ahora **dos envases del mismo CORT**: `APK_SIN_OIDO=1` en `apps/apk/compilar.sh` quita `assets/motor`, las `lib/*.so` y las clases de Vosk/JNA del `d8`, y deja el resto idéntico —medido: los `AndroidManifest.xml` de los dos APK son **los mismos byte a byte**, 15.860 B, `sha256` `8a2a74c2f077e5c5…`—, con misma llave y mismo `versionCode` **20402** para que se instalen el uno encima del otro sin perder datos. Para que el envase ligero no se caiga al abrir el micrófono, `CortNative.java` tiene `sinOidoPropio`: si `Oido` no se puede construir, `oidoEstado()` responde `sin-modelo` y la escucha vuelve al reconocedor del sistema (`ui/js/telefono.js` traduce la fase en la hoja Equipo ▸ 7); `scripts/audita-apk.sh` ya no canta faltas por no haber `.so` sino que declara la variedad, y cada `-firma.txt` dice cuál es. **Publicado verde en `v0.2.28-demo`** (run 39827866865, 2026-10-22): completo **47.390.449 B** / 49 entradas / `sha256` `39a5a7d0…82b2e3`, ligero **1.621.264 B** / 44 entradas / `sha256` `aac4aa25…8d9d5043`, los dos bajados y hasheados en este portátil y exactos a su hoja, CRC íntegros, y en el ligero **cero** entradas `lib/` y **cero** `assets/motor/` leídas dentro del `.apk`. Costura nueva: **sector [13]** de `scripts/prueba-costura.py` (179 `ok`, 5 comprobaciones de la ronda). **Falta, dicho en vez de fingido**: el veredicto de Google sólo existe en su teléfono, así que la bisección la cierra ella en dos minutos —si entra el ligero y no el completo, la ronda que viene saca el modelo del APK y lo descarga la primera vez que se pide el oído; si no entra ninguno de los dos, está marcado el par `com.cort.ia` + llave y no hay nada que compilar, hay que cambiar de paquete o pasar por Play. El `1.1.4` **no** es una sugerencia de bajada: le faltan las rondas 2.1 a 2.4.
- [x] **F7k** La ronda 2.5, **el NÚCLEO: la superficie del manifiesto como variable**. La dueña probó los dos envases de `v0.2.28-demo` y trajo el dato: «los dos fallan, Play Protect sigue bloqueando». Con eso el peso y las `.so` quedan **descartados por medida**, no por teoría: el ligero son 1.621.264 B, cero `.so`, cero modelo, y se bloquea igual que el de 47 MB. Se volvió a medir la charca UTF‑16 del `AndroidManifest.xml` **binario** de los tres APK que están en el mismo disco (el método vive ahora dentro de `scripts/audita-apk.sh`, así que el pipeline lo repite en cada Release): `CORT-IA-1.1.0` → **13 permisos / 0 servicios `BIND_*`** y se instala; `CORT-IA-1.1.4` → **13 / 0** y se instala; `CORT-IA-2.4.2-ligero` → **28 / 4 `BIND_*` repartidos en cinco servicios** y se bloquea. Los cuatro gordos que todos señalaban (`MANAGE_EXTERNAL_STORAGE`, `SYSTEM_ALERT_WINDOW`, `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`, `READ_EXTERNAL_STORAGE`) están en **los tres** archivos: nunca fueron la diferencia. Lo único que tienen los 2.x y no tiene lo que entra es la **superficie de integración** — `BIND_VOICE_INTERACTION` (ser el asistente del sistema), `BIND_SPEECH_RECOGNIZER`, `BIND_NOTIFICATION_LISTENER_SERVICE` (leer todas las notificaciones), `BIND_QUICK_SETTINGS_TILE`, `ACTION_ASSIST`/`ACTION_VOICE_COMMAND`, `CALL_PHONE`/`READ_CONTACTS`/`READ_CALENDAR` —, que es literalmente la firma con la que un clasificador sin contexto describe un troyano de accesibilidad. Así que `apps/apk/perfil.py` recorta el manifiesto por **regiones marcadas** (`<!-- PERFIL-DESDE:tag -->` / `PERFIL-HASTA`) y el pipeline compila **tres envases** del mismo CORT, con la misma llave `fa:ab:ef:46…` y el mismo `versionCode` **20500** para que se instalen unos encima de otros sin perder datos: `completo`, **`nucleo`** (de 24 a **21** `<uses-permission>`, de 6 a **1** `<service>`, de 12 a **0** cadenas privilegiadas) y `nucleo-ligero`. La prueba dura está en el **sector [14]** de `scripts/prueba-costura.py`, que ejecuta `perfil.py` y compara: el `completo` sale **byte a byte igual** al manifiesto publicado hoy —fuera las seis líneas de marcador, dentro **una sola** línea nueva, el `<meta-data android:name="com.cort.ia.PERFIL">`—, ningún marcador sobrevive en la salida de ningún perfil, y recortar sobre un fichero que ya lleva la etiqueta **reescribe** el valor en vez de respetar el anterior (la trampa real que haría que un `nucleo` generado desde `manifest-completo.xml` saliera diciendo `completo`). Y el recorte no deja puertas mudas: `CortNative.capacidades()` lee el perfil del archivo instalado, `window.CORTcapaz(puerta)` goberna avisos / asistente / llamadas / agenda / contactos en la cara, la hoja Equipo canta `envase nucleo`, y lo que se fue contesta con una frase honesta en vez de con un botón que no hace nada (el reproductor, su `MediaSession` y el doble toque del auricular **sí** siguen en el núcleo: `.Reproductor` es el único servicio que queda). `scripts/audita-apk.sh` lee el binario de cada APK antes de subirlo y **pone el run rojo** si un `nucleo` sale con algún `BIND_*` dentro. **Falta, dicho en vez de fingido:** el veredicto de Google sólo existe en su teléfono, y la prueba son dos minutos instalando **primero** `CORT-IA-2.5.0-nucleo.apk` — si entra y el `completo` no, era la superficie y se decide con ella qué se queda; si sólo entra el `nucleo-ligero`, el modelo de 40 MB entra en la lista de sospechosos y se saca del APK; si no entra ninguno de los tres, dentro del archivo no queda nada que cambiar y la vía es `adb` o reportar falsa alarma desde el propio cuadro: [`docs/BLOQUEO-PLAY-PROTECT.md`](docs/BLOQUEO-PLAY-PROTECT.md). La llave de firma **no** se movió a propósito: cambiarla obliga a desinstalar y se lleva el perfil, la clave de Groq apuntada en el teléfono y las notas.
- [x] **F7l** El cerebro JARVIS del portátil, **dos cosas que faltaban para que CORT hable de lo de fuera y de código**. (1) **Clima de la ciudad que se nombre**, sin clave y sin cuenta: `backend/app/sensors.py` pide las coordenadas al geocoder gratuito de Open-Meteo (`geocoding-api.open-meteo.com/v1/search`, medido en vivo el 2026-10-22: `Madrid` devolvió `results[0]` = 40.4165 / -3.70256, país `España`, zona `Europe/Madrid`) y luego `current` + `daily` en **una** llamada; la caché pasó de un hueco único a **uno por consulta** (`WEATHER_CACHE` ahora es `dict[str, dict]`), porque antes «Madrid» y luego «Sevilla» se pisaban la respuesta y la ventana de Entorno, que refresca cada 10 min, se comía el clima de la ciudad anterior. La ranura `auto` **sólo** se escribe desde el camino de la IP: si se escribiera también al preguntar por una ciudad, el panel de entorno leería Madrid creyendo que es su ubicación. Se arregló además un despejado que era mentira: `next((v for k, v in cielos.items() if cod >= k), "variable")` ganaba siempre con el `0`, así que ahora hay tabla WMO exacta (`CIELO_WMO`) y un código raro se llama `cielo sin clasificar (código N)`. `brain.local_command` saca el topónimo con `sitio_nombrado` («el tiempo en Gijón ahora mismo» → `Gijón`; «el clima de la semana» → nada; `Nueva York`, `Las Palmas` y `La Paz` se quedan enteras) y, si no nombra ninguno, usa la ciudad guardada en **07 · Perfil** (`ciudad`, clave libre de la memoria) y si no, la IP. Si el nombre no está en el mapa, CORT **repite el nombre entre comillas** en vez de dar el tiempo de otra ciudad ni decir «no hay internet». En la cara: **02 · Entorno** muestra ciudad, viento, máx/mín y probabilidad de lluvia, y tiene una caja donde escribir otra ciudad (Enter) que se guarda en el Perfil; `GET /api/weather?lugar=` es la puerta nueva. (2) **Registro de programación**: `es_programacion` mira un nombre de lenguaje o herramienta suelto (`python`, `kotlin`, `aapt2`, `docker`…) o un sustantivo técnico con su verbo (`explícame este bucle`), `think()` decide `modo` y se lo baja a `_ollama_chat` / `_groq_chat` / `_gemini_chat`, que usan `CODER_PROMPT` en vez de la consigna de siempre y más salida en Groq (1400 tokens en lugar de 700). No es otra IA ni otra clave: es la misma con otra hoja de instrucciones, escrita para ella — aprendiendo, en español, en un portátil de 2 núcleos y 1,8 GiB, con su stack real (JS plano + FastAPI + Electron + APK sin Gradle) — y con prohibido inventarse una API. Cuando no hay ningún cerebro, la frase de código **no** se contesta con el termómetro: `think` salta el mando local y `_offline_reply` dice qué falta. **Prueba nueva y en verde:** `scripts/prueba-clima.py` — 42 comprobaciones, **sin red** (`sensors.weather` sustituido por un gemelo con los campos exactos medidos en Open-Meteo y base de memoria en `mktemp`), y va montada en el pipeline como paso «Probar el clima y el registro de código» del trabajo `apk`, con anotación en rojo si falla. Costura, lectura, organiza y automatizaciones re-ejecutadas: **195 `ok` / EXIT 0**, `prueba-lectura.py` EXIT 0, `prueba-organiza.py` EXIT 0 y 45/45 en el motor de automatizaciones. Salida real de hoy: «¿qué tiempo hace en Gijón?» → `En Gijón, España: 17 °C, llovizna débil, sensación 14 °C, viento 10 km/h, humedad 55 %. Hoy entre 12 y 18 °C, con un 75 % de probabilidad de lluvia.` **Falta, dicho en vez de fingido:** el clima por ciudad vive en el **backend**, así que en el teléfono obedece cuando está conectado al PC por Wi‑Fi; que el APK lo pregunte por su cuenta a Open-Meteo (regla nueva en `habilidades.py` + una llamada en `Nube.java`, que ya sabe hacer HTTP) es la ronda siguiente. Y `es_programacion` es un detector de palabras, no un clasificador: una pregunta de código escrita en inglés y sin nombrar ningún lenguaje se queda con el registro de siempre — se contesta igual, con otra consigna.
- [x] **F7m** Los **mandos de voz del portátil ya no son decorativos**: timbre, tono y velocidad se eligen y se oyen. Empezó como «añadir un listener de `voiceschanged`» y terminó en una **medida** (`scripts/sonda-voz.html`, abierta en el Chromium de esta casa): `speechSynthesis` existe, `SpeechRecognition` existe, y **`getVoices()` devuelve 0 voces** —en la apertura, al disparar `voiceschanged` y a los 400/1200/3000 ms, todas las veces 0. Eso es lo que pasaba: en Linux el Web Speech no tiene con qué hablar, así que los tres deslizadores de **07 · Perfil** movían una cosa que no existía y CORT se quedaba muda sin decir nada. Windows y macOS (SAPI / AVFoundation) y el teléfono (`TextToSpeech`) siguen con su voz de siempre. La cara elige ahora **una de cuatro bocas** por orden: `nativa` (el puente del APK) → `navegador` (Web Speech **sólo si tiene voces**) → **`núcleo`** (`POST /api/voice/say` → WAV → `<audio>`) → `muda`, y `muda` se **anuncia** (`h.onError('sin-boca')` + línea en la terminal) en vez de callarse. El núcleo nuevo es `backend/app/voz.py`, que habla con el `/usr/bin/espeak-ng` ya instalado en el portátil — sin descargar nada ni meter un motor de 40 MB: medido, una frase de prueba son **0,106 s y 61 KB** de WAV. Los tres mandos están **cableados de verdad**: tono 0,5…1,5 → `-p` (0,5 → **26**, 1 → **50**, 1,5 → **74**), velocidad 0,6…1,6 → `-s` palabras por minuto (1 → **175**, tope **450**), y el timbre sólo se manda si **esa voz existe en ese equipo**. La lista no se copia de ninguna docena: se **sondea sintetizando** cada candidata (`es`, `es-419`, `es-mx` y sus variantes `+f2 +f4 +m3 +m5`), se queda con las que producen audio y cuyo audio **difiere** del de la base, y se cachea bajo un cerrojo (`voz.estado()`, `voz.remeder()`). En `--voices` aparece mbrola pero falla al sintetizar (exit 1, «Please install necessary MBROLA voice»), así que **no se ofrece**, y una variante que el motor ignore tampoco. Coste del sondeo medido: **0,81 s para 10 timbres**. En la cara: el desplegable se rellena con lo que devolvió el sondeo (**11 opciones**: la automática + 10 timbres, con `[M]`/`[F]` y el nombre en español), la nota debajo dice literalmente *«Habla el motor de este equipo por el núcleo (10 timbres comprobados uno a uno)»*, y mover un deslizador **aplica** (`aplicaVoz()` en el `input`, no al guardar). Electron necesita el interruptor `autoplay-policy=no-user-gesture-required` para que el WAV suene sin tocar nada, porque el saludo llega antes del primer gesto. El arreglo del desplegable destapó, y la prueba lo cazó, **un bug real**: `tonos_a_pitch` recortaba contra la *amplitud* (49) en vez de contra el tope del motor (99), así que **1,0 y 1,5 daban el mismo 49** — el deslizador de tono sólo funcionaba en media carrera. Corregido con `PITCH_TOPE = 99` y firmados los valores de arriba. **Pruebas nuevas y en verde:** `scripts/prueba-voz.py` — **56 comprobaciones**: los mandos y sus topes, `limpio()`, el camino sin espeak (`sin-motor` con motivo), el texto real de `--voices` analizado (fuera mbrola, fuera el francés, 10 timbres, «variante ignorada fuera», motor sin español → 0 timbres), el **argv exacto** que se le pasa al motor (`-v es+f4` · `-p 41` · `-s 210` · el texto al final · ni `;` ni `|` ni `&` · una voz desconocida sale **sin** `-v` y con `"voz": ""`), los fallos con nombre (`no-suena` con el mensaje del propio motor, `no-responde` si se cuelga), que no queden ficheros `cort-voz-*` en `/tmp`, y el motor **de verdad** si está (audio > 3000 B; el listón existe porque una prueba falsa de papel daba 2.027 B y pasaba). Montada en el pipeline como paso «Probar la boca del escritorio (sin sonido, sin red)», con `::error::` en rojo si falla. Costura: **209 `ok`** — el sector **[16] F7m** fija que la suite esté llamada de verdad en el workflow, que las dos rutas y las cuatro bocas existan, que el `POST` lleve los cuatro campos del modelo, que el cuerpo del teléfono siga siendo la misma llamada de **5 argumentos** (`N.speak(texto, id, voz, tono, velocidad)`) y que el `revokeObjectURL` y el `autoplay-policy` no se borren; la comprobación de cableado se reescribió a `python3 scripts/prueba-clima.py` / `python3 scripts/prueba-voz.py` literales tras **comprobar por mutación** que con sólo el nombre de la suite en un comentario pasaba en falso. Salida real de hoy, del navegador de la casa contra `:8010`: `GET /api/voice` → `motor espeak-ng`, y «Probar voz» → `POST /api/voice/say` **200**, **74.254 B** de `audio/wav` con `x-cort-voz: es+f4`, `x-cort-pitch: 41`, `x-cort-wpm: 193`, y en la terminal `boca de voz: núcleo (espeak-ng, 10 timbres)`. **Falta, dicho en vez de fingido:** espeak-ng es inteligible, no bonito — la voz de calidad (`piper`) es un modelo de varios MB y no se mete en el portátil de 1,8 GiB sin decidirlo con ella; y decir «más grave», «más rápido», «voz de mujer» **por frase** todavía no está (esta ronda es que el deslizador funcione). Y el veredicto de Play Protect sobre los tres envases de `v0.2.29-demo` sigue siendo de su teléfono: nada de esta ronda lo toca — ni la llave de firma, ni el `versionCode`, ni el manifiesto.
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
