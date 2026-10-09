# CORT

**C**ognitive **O**perating **R**eactive **T**echnology — un asistente personal holográfico, **local-first**, inspirado en Cortana (*Halo*).

No una maqueta: un orbe de shader que respira, una memoria que sobrevive al apagar, un cerebro que puede ser un modelo tuyo o un chat local, y una capa de permisos que hace las cosas en el sistema real. Corre en un portátil de **1,8 GiB de RAM y sin tarjeta gráfica**, porque si corriera en una máquina de 128 GiB no valdría nada como prueba de concepto.

**Prototipo actual: `v0.6.0`** · rama `cort-local-verified` · **179 pruebas en verde** · licencia MIT · creadores **Sandra Lopez** y **Askher Vargas**.

![CORT: reactor holográfico azul/violeta ocupando la pantalla, con el cabezal de estado y la esquina que abre la bandeja](docs/assets/prototipo-v0.6.0.png)

---

## Arquitectura

Tres capas, un protocolo, y todo en la misma máquina. Ningún dato sale del equipo salvo que tú configures un modelo remoto (no es el caso).

```
        Usuario (voz* · teclado · táctil · cámara)
                     │
   ┌─────────────────▼──────────────────┐
   │  apps/web   React 19 · Vite · TS   │  interfaz: reactor GLSL, HUD, chat,
   │  Three.js r185 · post-proceso      │  telemetría, efectos, PWA
   └─────────────────▲──────────────────┘
                     │  WebSocket JSON (ws://127.0.0.1:8765/ws)
   ┌─────────────────┴──────────────────┐
   │  services/core   Python 3.13       │  FastAPI + websockets, sin framework
   │  brain · intents · actions ·       │  de app: un módulo por responsabilidad
   │  memory · status · outfit · avatars│
   └───▲──────────────▲─────────────▲───┘
       │              │             │
   Ollama        SQLite         capa de permisos
   (LLM local)   (memoria)      (wpctl · scrot · xdotool · apps)
                                     │
                               sistema real

   * voz: diseñada y bloqueada por hardware en esta máquina — ver Funciones
```

Un mensaje recorre el sistema así (cada paso está probado, `test_protocol.py`):

1. El cliente manda `{"type":"user_message","text":…}`.
2. `memory/facts.py` extrae hechos declarables («me llamo Sandra» → `El usuario se llama Sandra`) y `memory/store.py` los guarda **antes** de cualquier otra cosa.
3. `intents.py` mira si la frase es una orden local («baja el volumen»). Si lo es, **no se gasta el LLM**.
4. Si es una orden, `actions.py` la ejecuta por la lista cerrada de permisos y **comprueba el resultado en el mundo** (nivel de volumen, archivo en disco, recuento de procesos).
5. Si no, `brain.py` pregunta a Ollama con los recuerdos relevantes metidos como mensaje de sistema.
6. Vienen `assistant_message`, un `effect` (`pulse` si la acción fue, `glitch` si falló) y un `status` con lo que CORT puede afirmar de sí mismo.

## Componentes

| Componente | Archivo(s) | Qué hace |
|---|---|---|
| **Servidor y protocolo** | `services/core/cort_core/server.py` | FastAPI + WebSocket. Reparte los siete marcos que salen del core (y escucha los dos que entran: `user_message` y `list_avatars`), sirve los archivos de atuendo por `GET /avatars/{nombre}`, arma el prompt con memoria y decide si el turno pasa por el modelo o por un atajo local. Toda llamada al sistema va en `await` sobre `asyncio.create_subprocess_exec`: un `subprocess.run` bloqueante pararía el bucle que atiende a los demás clientes |
| **Cerebro (LLM)** | `cort_core/brain.py` | Cadena de sustitución (`CORT_LLM_CHAIN`): usa el primer modelo que responda. Pide `/api/tags` y **descarta por tamaño** lo que no cabe en RAM (`CORT_LLM_MAX_MODEL_MIB`, 700 MiB) — cargar el de 2,6 GB congeló la máquina. Distingue «Ollama no está» de «la cadena no respondió». Sin modelo, modo eco |
| **Memoria persistente** | `cort_core/memory/{store,facts}.py` | SQLite con búsqueda por raíces de 4 letras (no embeddings: esos piden ~1,5 GiB). `remember · recall · context_for · prune · name_of_user · count`. `prune` protege la fila del nombre, de la que depende el saludo. `context_for` rescata **por contenido, no por fecha** |
| **Intenciones** | `cort_core/intents.py` | Patrones locales para órdenes de sistema. Devuelve una acción estructurada y **no ejecuta nada** — separar las dos cosas es lo que hace auditable el permiso |
| **Capa de permisos** | `cort_core/actions.py` | Convierte esa acción en un comando real **de una lista cerrada**, con argv fijo, verificación del resultado y apagador global. Es la frontera entre «CORT entendió» y «CORT lo hizo» |
| **Telemetría** | `cort_core/status.py` | Lee tres cosas y nada más: cuántos recuerdos hay, qué modelo habló la última vez y si los permisos están encendidos. Si un valor no se puede medir manda `null`, no un adorno |
| **Atuendo** | `cort_core/outfit.py` | El color del holograma según hora y temperatura, igual que el de Cortana |
| **Atuendos en disco** | `cort_core/avatars.py` | El catálogo de archivos que la usuaria pone en `CORT_AVATAR_DIR`: lista, sirve y **no se fía de ninguna ruta ajena**. Tres guardas, en este orden: nombre contra una expresión cerrada, `resolve()` + `relative_to()` sobre la raíz (no `startswith`, que se cuela con `/raiz-otra`), y extensión dentro de un mapa cerrado. Fuera de esa carpeta responde 404 —no 403, para no revelar que algo existe— |
| **Clima** | `cort_core/weather.py` | Open-Meteo sin clave de API: resuelve la ciudad una vez, refresca cada 15 min y **sirve caché**, nunca una petición dentro del bucle del WebSocket. Si el servicio falla devuelve la última foto y deja de afirmarla pasados tres TTL. Sin `CORT_CITY` no sale ningún paquete de la máquina |
| **Configuración** | `cort_core/env.py` | El lector de `.env`: un solo parser para el core y el lanzador, para que no puedan discrepar en qué puerto están. Una variable exportada gana; `CORT_DOTENV=0` anula el archivo (lo usan las pruebas) |
| **Reactor holográfico** | `apps/web/src/scene/{Core,Particles,Scene}.tsx` | Un solo quad con shader de coordenadas polares (anillo erosionado por fbm, polvo, barrido radar) + Bloom, aberración cromática, ruido y viñeta. **18 fps sin GPU**, y los mismos a 200 % de tamaño |
| **Estado y conexión** | `apps/web/src/cort/{connection,palette}.ts` | Dos capas deliberadamente separadas: un *snapshot* inmutable para React (`useSyncExternalStore`) y un objeto mutable que la escena persigue con `lerp`. Por eso cambiar de atuendo **respira** en vez de parpadear, y por eso el orbe **crece** en vez de saltar. Un solo archivo define todo el color |
| **Interfaz** | `apps/web/src/ui/{Hud,Telemetry,Effects,Bandeja,Avatar}.tsx` | Chat con reloj, clima medido en el cabezal, control de tamaño del reactor, **bandeja que se guarda en la esquina**, panel de «lo que CORT sabe de sí mismo», capa de efectos de un solo disparo y **proyección del cuerpo con atuendo**. Escritos **sin** `zustand`, `drei` ni `framer-motion`: cada dependencia es RAM que esta máquina no tiene |
| **Gestos de cámara** | `apps/web/src/cort/defocus.ts` | Desenfocar con los dedos delante de la webcam encoge el orbe y enfocar lo devuelve. Sin modelos ni dependencias: 64×48 píxeles a 5 muestras por segundo, gris BT.601 y **varianza del Laplaciano** — el criterio con el que cualquier cámara decide si ya enfocó. La cámara la abre un botón de la usuaria y apagarla detiene las pistas del stream |
| **Capa instalable** | `apps/web/public/manifest.webmanifest`, `public/icons/` | `display: standalone`, tema `#02040c` y cuatro iconos generados con código propio a partir de `palette.ts`. **Sin service worker a propósito**: cachear una interfaz que depende del core daría un CORT que parece vivo sin estarlo |
| **Lanzador** | `scripts/cort.py` + `CORT.desktop` + `cort.bat` | La única puerta soportada para encenderlo todo: banner de marca y **siete barras de estado** (core · interfaz · ollama · memoria · **audio** · **cámara** · red). Sin dependencias, ANSI con la estándar. `--demo` manda la memoria a `/tmp`; `--lan` es lo único que saca CORT de `127.0.0.1` |
| **Pruebas** | `services/core/tests/` | 179, con la biblioteca estándar. El Ollama y el clima se fingen con `httpx.MockTransport`, el ejecutor de acciones con un `runner` inyectable y los atuendos con un directorio de mentira en `tempfile`: **la suite no le mueve el audio, no le escribe la memoria a nadie, no le lee su carpeta de modelos y no hace una sola petición a internet** |

## Protocolo WebSocket

`ws://127.0.0.1:8765/ws`, JSON plano: **nueve tipos**, dos entrantes y siete salientes. Los tipos nuevos se escriben aquí y en `docs/ARCHITECTURE.md` **antes** de programarlos (regla 5 de `AGENTS.md`).

| Tipo | Dirección | Lleva | Quién lo pinta |
|---|---|---|---|
| `user_message` | cliente → core | `text` | — |
| `list_avatars` | cliente → core | — (lo dispara abrir el selector de atuendos) | — |
| `state` | core → cliente | `outfit`, `mood`, `thinking`, y `city` + `temp_c` **solo si el clima está medido** | reactor y HUD |
| `greeting` | core → cliente | `text`, `mood` | el chat, **sólo si el registro está vacío** (viaja separado de `assistant_message` porque el core lo manda en cada reconexión) |
| `assistant_message` | core → cliente | `text`, `mood` | el chat |
| `intent` | core → cliente | `action`, `delta`/`app` | trazabilidad de la orden |
| `effect` | core → cliente | `kind` ∈ `glitch · pulse · scan · shake · flash` | capa de efectos (no se guarda: es puntuación, no estado) |
| `status` | core → cliente | `memories`, `keep`, `brain`, `ollama`, `actions` | panel de telemetría |
| `avatars` | core → cliente | `items`: `nombre`, `mime`, `bytes` (lista vacía si no hay `CORT_AVATAR_DIR`) | mosaico táctil de atuendos. Los bytes no van por aquí: se cargan con `<img>` desde `GET /avatars/{nombre}` |

## Seguridad y permisos

Lo que hace a esto una capa de permisos y no un `subprocess` suelto:

1. **Lista cerrada.** Sólo hay cuatro mandos: `volume`, `media`, `screenshot`, `launch`. Todo lo demás responde «no está en la lista permitida» con un `glitch`, en vez de fingir un «entendido».
2. **argv fijo.** No existe `shell=True`, y ni el texto del usuario ni la salida del modelo entran en los argumentos: sólo un entero que sale de *nuestra* tabla de patrones y claves de una constante.
3. **El LLM no tiene herramientas.** `brain.py` devuelve texto y ese texto se pinta. No hay camino del modelo al shell.
4. **Se puede apagar sin tocar código:** `CORT_SYSTEM_ACTIONS=0`.
5. **El resultado se comprueba, no se supone:** el nivel se lee antes y después, la captura se mira en disco, la app se cuenta con `pgrep`. Un `returncode` 0 no es una prueba.
6. **Datos personales fuera de git.** La base vive en `services/core/data/` (ignorada), `.env` está ignorado, y las claves no se suben nunca. Para enseñar CORT a otra persona existe `--demo`.

## Funciones

El inventario completo, con estado y viabilidad por sistema operativo, está en [`docs/FUNCTIONS.md`](docs/FUNCTIONS.md). Resumen medido hoy:

| Grupo | Funciones | Hechas | En curso | Pendientes |
|---|---|---|---|---|
| Núcleo (chat, memoria, intents, clima, configuración, atuendos en disco…) | 12 | 7 | 0 | 5 |
| Voz y audio (wake word, STT, TTS, volumen, reproductor…) | 13 | 1 | 2 | 10 |
| Avatar y HUD (partículas, VRM, atuendo, tamaño, bandeja, cuerpo proyectado, overlay, efectos, móvil) | 17 | 7 | 3 | 7 |
| Gestos y visión (desenfoque con cámara, MediaPipe, rostro, descripción de cámara) | 13 | 1 | 0 | 12 |
| Control de dispositivos (apps, brillo, captura, notificaciones…) | 7 | 1 | 1 | 5 |
| Sensores y contexto (cámara en el arranque, temperatura, red, MQTT, preferencias) | 10 | 1 | 0 | 9 |
| **Total** | **72** | **18** | **6** | **48** |

Las cifras las cuenta `docs/FUNCTIONS.md`, que es el inventario largo con la evidencia de cada fila, **expandiendo los rangos** (la fila «37-44» son ocho funciones, no una).

Lo que **todavía no está**, dicho en vez de simulado: **voz** y **cuerpo 3D (VRM)**. Los dos motivos son de hardware y están medidos en esta máquina — sin micrófono ni salida de audio real, sink en *Dummy Output*, 2 núcleos a 1,46 GHz, ~286 MiB libres con el reactor pintando a 17-26 fps —, no son «falta de código». El gesto de cámara **sí** está y funciona; lo que no se ha podido probar aquí es el dedo humano delante del objetivo. Ver [`docs/PLATFORM.md`](docs/PLATFORM.md).

## Qué hace hoy, y cómo se sabe

Cada fila de esta tabla se ejecutó en la máquina de desarrollo; nada está deducido de leer el código.

| | Qué ocurre | Cómo está verificado |
|---|---|---|
| 🔮 | **Reactor holográfico**: anillo de plasma en GLSL, polvo de 4000 puntos, bloom, aberración cromática, líneas de barrido. Paleta azul/violeta Cortana, cinco atuendos | Capturas reales a `localhost:5173`; **18 fps sin GPU** |
| 💬 | **Chat por WebSocket** contra un core Python/FastAPI | Cliente real + 8 pruebas de protocolo |
| 🧠 | **Memoria persistente** (SQLite). Se mata el proceso, al levantarlo saluda: *"Hola de nuevo, Sandra"*. Y al armar el prompt **rescata por contenido, no por fecha**: con 303 recuerdos de prueba los tres datos del usuario van delante, no los seis más recientes | Probado matando y reiniciando el proceso; 28 pruebas de memoria, una cronometrada en 2,42 ms |
| 🗣️ | **Cerebro local con Ollama** y **cadena de sustitución**: responde el primer modelo que funcione, y los que no caben en RAM se descartan antes de intentarlos | 10 pruebas con un Ollama de mentira; medición real del LLM |
| ⚡ | **Acciones reales en el sistema** a través de la capa de permisos: cambia el volumen con `wpctl` y **lee el nivel antes y después**; hace una **captura de pantalla** con `scrot` y **comprueba el archivo**; **abre aplicaciones** de una lista cerrada y lo confirma contando el proceso nuevo | Verificado por WebSocket contra PipeWire, contra disco (PNG real de 1366×768) y contra `pgrep`: `xfce4-terminal` pasó de 0 a 1 procesos con CORT diciendo «Abriendo la terminal», y a la segunda «La terminal ya estaba en marcha» |
| ✨ | **Efectos de un solo disparo**: onda al ejecutarse algo, desgarro al fallar | `MutationObserver` en el navegador |
| 📊 | **Panel de telemetría**: cuántos recuerdos hay y hasta dónde llegan, qué modelo contestó, si las acciones están encendidas. Con el apagador puesto el panel dice «apagadas» en vez de fingir. Y **reloj** en el cabezal del HUD | `test_status` (9) y `test_protocol` (8), y cliente real: `{"memories":1,"keep":200,"brain":null,"ollama":false,"actions":false}`. El reloj, medido: `00:25:04 → 00:25:07` en 2,1 s |
| 🖥️ | **Arranque de doble clic**: `CORT.desktop` en Linux, `cort.bat` en Windows, terminal con banner y **siete barras** (core · interfaz · ollama · memoria · **audio** · **cámara** · red) | Lanzado de verdad: `dist` y `vite dev`, `--quiet` y salida redirigida. La barra de audio, ejecutada hoy: `0 salida(s): ninguna real (Dummy Output) · 0 entrada(s)`. La de red, con `--lan` y las dos direcciones escuchando en `0.0.0.0`. **Sin verificar el doble clic en el escritorio XFCE** (lo maneja a mano Sandra) |
| 🎨 | **Atuendo por hora y temperatura real**: el reactor elige color según el cielo de la ciudad, y **se puede agrandar de un arrastre** (50 % a 200 %) | `pick_outfit` con las tres temperaturas de corte probadas; el tamaño, medido en el navegador: 18 fps a 100 % y los mismos 18 a 200 % |
| 🌦️ | **Clima por Open-Meteo** (sin clave): la ciudad del `.env` se resuelve una vez, se refresca cada 15 min y se sirve de caché para no bloquear el WebSocket. Sin `CORT_CITY` no sale ningún paquete | 9 pruebas con HTTP simulado + una medición real: `Bogotá → 17,7 °C, código 3` |
| 🤳 | **Gesto de cámara**: desenfocar con los dedos delante de la webcam encoge el orbe; enfocar lo devuelve a su tamaño. La cámara la abre un botón y apagarla detiene las pistas | Medido en el navegador con un stream real de imagen nítida y desenfocada: **100 % → 51 % al desenfocar, de vuelta al 100 %, 17 fps con el análisis activo** (18 sin él). Con dedos humanos: sin verificar (el navegador de pruebas negó el permiso) |
| 🧍 | **Cuerpo proyectado con atuendo**: al elegir un archivo de su carpeta el reactor se apaga y aparece CORT en azul/morado semitransparente; al volver al reactor **la conexión no se toca** | Servido y probado en el navegador con sus propios PNG: catálogo por WebSocket, miniaturas cargadas desde `:8765`, y el cabezal diciendo «CORT en línea» con el avatar puesto. **26 fps** con un halo (22 con dos, 29 sin halo — por eso uno). El VRM 3D: listado pero **sin proyectar** |
| 📥 | **La pantalla es el reactor**: la bandeja (registro, telemetría, controles) está guardada y se abre desde la esquina, con el dedo o con el ratón; los mensajes que llegan con ella cerrada se cuentan en el propio tirador | Probado en el navegador: `abierto ↔ cerrado`, `aria-hidden`, `opacity` 1→0, aviso contando el saludo. En un móvil físico: **sin verificar** |
| 📱 | **Interfaz preparada para táctil y para instalarse** (pulsaciones de 44-48 px, sin auto-zoom, `safe-area`, `manifest.webmanifest` con `display: standalone` e iconos), y **`--lan` para abrirla desde otro aparato** | El manifiesto, servido y medido: `200 application/manifest+json`, JSON válido y consola sin avisos. `--lan` probado en la red: `0.0.0.0:8780` dio `200` y un WebSocket contra la IP de red saludó y respondió. Lo del móvil físico: **sin verificar** |

## Plataforma: PC, móvil y por qué no C++/Java

CORT **ya es multiplataforma por arquitectura**, no por lenguaje: un core Python que habla por WebSocket + una interfaz web. El mismo código corre en Linux, Windows, macOS y en el navegador de un Android; cambiar de sistema operativo toca la capa de mandos (`actions.py`), no el lenguaje.

Electron, Capacitor, C++ y Java están **evaluados con números de esta máquina** en [`docs/PLATFORM.md`](docs/PLATFORM.md): un Chromium extra sobre 263 MB libres, y un `javac` que no existe. La pila es Python + React + Ollama y no cambia por una sugerencia externa (regla 13 de `AGENTS.md`); para alterarla hay que traer una medición nueva, no una opinión.

## Hardware: por qué el prototipo se ve así y no de otra forma

Medido, no supuesto:

- **2 núcleos a 1,46 GHz · 1,8 GiB de RAM · sin GPU.** El reactor va a **18 fps**. El LLM genera a **~1,3 tokens/s**: un turno normal cuesta 15-60 s.
- **Nada de más de ~700 MiB entra en la cadena de modelos.** Cargar uno de 2,6 GB **congeló la máquina**.
- **Sin salida de audio usable y sin micrófono**: el único chip es HDMI y el puerto está `not available`, así que el sink es *Dummy Output*, y `arecord -l` no encuentra ninguna entrada de **audio**. **La cámara sí existe y sí funciona**: `Chicony USB Camera` en `/dev/video0` y `/dev/video1`, accesibles para esta usuaria (grupo `video`), y ya se usa en el gesto de desenfoque. Por eso la voz es Fase 2 y no "un modelo más": aquí no se puede oír ni escuchar.
- Consecuencia de método: **se mide antes de prometer**. Cualquier fila nueva de esta tabla entra con su evidencia o dice «sin verificar».

## Estructura del repositorio

```
CORT/
├── services/core/
│   ├── cort_core/            # el cerebro: server · brain · intents · actions · avatars · status · outfit · weather · env
│   │   └── memory/           # store.py (SQLite) + facts.py (extracción de hechos)
│   ├── tests/                # 179 pruebas, biblioteca estándar
│   ├── data/                 # memory.db — fuera de git: son datos personales
│   └── requirements.txt
├── apps/web/                 # React 19 + Vite + Three.js (src/cort · scene · ui · public/)
├── scripts/                  # cort.py (lanzador) · install-desktop.sh
├── docs/                     # STATUS · ARCHITECTURE · ROADMAP · FUNCTIONS · PLATFORM · VISION
├── upstream/                 # referencias de terceros: solo lectura, con licencia
├── CORT.desktop · cort.bat   # doble clic en Linux y Windows
├── Makefile · AGENTS.md · CREDITS.md · LICENSE
```

## Instalación

**Instrucciones de cero a CORT encendido**, en orden. Cada requisito y cada salida de las de abajo están ejecutados en esta máquina (Debian 13, 2 núcleos, 1,8 GiB); lo que no se pudo ejecutar aquí va marcado **sin verificar**.

### Paso 0 · Qué tiene que estar instalado antes de empezar

| Requisito | Para qué hace falta | Cómo se comprueba | Medido aquí |
|---|---|---|---|
| **Python ≥ 3.11** | el core (FastAPI + SQLite) | `python3 -V` | 3.13.5 |
| **Node ≥ 20 y npm** | construir la interfaz (`apps/web`) | `node -v` · `npm -v` | v20.19.2 · 9.2.0 |
| **GNU make** | un solo sitio donde viven las recetas | `make -v` | 4.4.1 |
| **git** | bajar el repositorio | `git --version` | opcional: también vale descargar el ZIP |
| **Ollama** *(opcional)* | que conteste un modelo local | `ollama -v` | **sin Ollama CORT sigue funcionando** en modo eco |
| **Cámara web** *(opcional)* | el gesto de desenfoque que agranda y encoge el orbe | la abre un botón del HUD pidiendo permiso al navegador | `Chicony USB Camera` en `/dev/video0` y `/dev/video1`, accesibles para esta usuaria (grupo `video`) |

En Debian y Ubuntu el módulo `venv` no viene con el intérprete: viene en un paquete aparte, y su ausencia es el fallo más común en esta máquina.

```bash
sudo apt update && sudo apt install -y python3-venv
# sin esto, `make setup` se cae con "No module named venv"
```

En Windows: Python desde python.org marcando *«Add python.exe to PATH»*, y Node desde nodejs.org. `make` no hace falta —el paso 2 trae su equivalente comando a comando—.

### Paso 1 · Bajar el proyecto

```bash
git clone https://github.com/Sandra2244/CORT.git
cd CORT
```

### Paso 2 · Instalar

```bash
make install
```

Es el atajo de tres pasos que se pueden dar por separado si algo se rompe a mitad:

| Comando | Qué hace realmente | Dónde acaba |
|---|---|---|
| `make setup` | crea el entorno aislado `.venv`, instala `fastapi`, `uvicorn[standard]` y `httpx`, y **copia `.env.example` a `.env`** si no existía | `.venv/` y `services/core/` |
| `make web-deps` | `npm install` | `apps/web/node_modules/` |
| `make web-build` | comprueba tipos con `tsc --noEmit` y genera la interfaz final con Vite | `apps/web/dist/` — 6,03 s de build medidos aquí |

**Sin `make`** (Windows, o donde no esté instalado):

```bat
py -m venv .venv
.venv\Scripts\python -m pip install -r services\core\requirements.txt
copy .env.example .env
cd apps\web && npm install && npm run build && cd ..\..
```

Nada de esto toca el sistema: no hay `sudo`, no se instala ningún servicio ni se añade nada al arranque. Todo se queda dentro de la carpeta del proyecto, y borrar la carpeta borra CORT.

### Paso 3 · Comprobar que está todo

```bash
make doctor
```

Mira, no instala. Salida real de esta máquina (se ha sustituido la ruta personal por `…`):

```text
python3   Python 3.13.5
node      v20.19.2
npm       9.2.0
venv      ok (…/CORT/.venv/bin/python)
.env      ok
node_modules ok
dist      ok (el lanzador lo sirve)
ollama    instalado (arranca con: ollama serve)
audio     1 sink(s) activo(s)
```

Cualquier línea que diga `FALTA` lleva al lado el comando que la arregla.

### Paso 4 · Encender

```bash
make launch
```

Levanta el core, sirve la interfaz y abre el navegador. La terminal pinta seis barras de estado —siete con `--lan`, que añade la de red—:

```text
 ● core         ws://127.0.0.1:8765/ws
 ● interfaz     http://127.0.0.1:8780   (dist)
 ● ollama       apagado — CORT responde en modo eco
 ● memoria      0 recuerdos en cort-demo.db  (demo)
 ● audio        0 salida(s): ninguna real (Dummy Output) · 0 entrada(s) — sin esto no hay voz que verificar
 ● camara       2 cámara(s): video0, video1 · la abre el navegador desde la página, con permiso tuyo
```

**`Ctrl+C` cierra las dos cosas** —el lanzador mata al hijo antes de salir, no deja procesos sueltos—.

Otros tres arranques útiles:

```bash
make dev      # solo el core, sin interfaz: http://127.0.0.1:8765 (WebSocket en /ws)
make demo     # como launch, pero la memoria se va a /tmp: no escribe recuerdos de nadie
make web      # interfaz en modo desarrollo con recarga en caliente (~120 MB más de RAM)
```

### Paso 5 · Configurar (opcional, pero Ollama vive aquí)

Todo se ajusta en **`.env`**, que se lee solo al arrancar —el core y el lanzador lo hacen con el mismo parser, para que no puedan discrepar en qué puerto están—. Una variable exportada en la terminal gana sobre la del archivo, y `CORT_DOTENV=0` anula el archivo entero (es lo que usan las pruebas). Las variables están explicadas en [`.env.example`](.env.example); las cinco que importan el primer día:

| Variable | Qué cambia |
|---|---|
| `CORT_LLM_CHAIN` | qué modelos puede usar CORT, en orden de intento: habla el primero que responda |
| `CORT_CITY` | la ciudad del clima. **Vacío = no sale ni una petición a internet** |
| `CORT_SYSTEM_ACTIONS` | `0` apaga la capa de permisos: sigue hablando, pero no toca el sistema |
| `CORT_MEMORY_DB` | otra ruta para `memory.db`, para experimentar sin escribir encima de la memoria real |
| `CORT_AVATAR_DIR` | la carpeta de atuendos que ve el mosaico táctil. **Sin esta variable el selector sale vacío y el reactor no se apaga nunca**: los modelos VRM y las imágenes no van en el repositorio porque pesan 16-21 MB cada uno, tienen licencia de terceros y son datos personales |

Para que conteste un modelo local en vez del modo eco:

```bash
ollama serve                     # no arranca solo
ollama pull qwen2.5:0.5b         # 379 MiB: el único que cabe sin congelar esta máquina
```

y en `.env`, `CORT_LLM_CHAIN=qwen2.5:0.5b`. **Un modelo de más de ~700 MiB ni se intenta**: el guard de RAM lo descarta antes de cargarlo, porque uno de 2,6 GB congeló esta máquina (medido).

Para vestir a CORT con sus propios archivos (PNG, JPG, WebP o VRM):

```bash
# en .env, y reiniciar
CORT_AVATAR_DIR=/ruta/a/su/carpeta/de/atuendos
```

El core **no adivina ninguna carpeta**: sin la variable, el mosaico de atuendos sale vacío y lo dice en pantalla en vez de mostrar figuras inventadas. Los archivos nunca se suben a git —por eso existe la variable— y sólo se sirve lo que esté *dentro* de esa carpeta: una ruta que intente salirse responde 404, igual que una extensión que no esté en la lista cerrada (probado en `tests/test_avatars.py`: 15 pruebas con un directorio de mentira en `tempfile`).

### Paso 6 · El doble clic, para no volver a abrir una terminal

- **Linux (XFCE, GNOME, KDE):** `./scripts/install-desktop.sh` escribe `CORT.desktop` en la raíz del proyecto con la ruta absoluta de *esta* máquina —por eso ese archivo está en `.gitignore`: en un repo público no va la carpeta personal de nadie— y lo instala en el menú de aplicaciones. Con `--desktop` añade además el icono al Escritorio, ya marcado como confiable. Después de eso: doble clic y CORT abre solo.
- **Windows:** `cort.bat`, doble clic. Busca el `.venv` y si no está lo avisa en la ventana en vez de cerrarse sin decir nada. **Sin verificar en Windows real**: la máquina de pruebas sólo tiene Linux.

### Paso 7 · CORT en el teléfono

Portátil y móvil, en **la misma red Wi-Fi**.

```bash
python3 scripts/cort.py --lan
```

La barra de **red** —la séptima, sólo con `--lan`— imprime la dirección que hay que escribir en el móvil, por ejemplo `http://192.168.100.xxx:8780`, porque adivinar la propia IP no es un paso razonable. Sin `--lan` todo escucha sólo en `127.0.0.1`, y así queda por defecto: **el core no tiene contraseña ni HTTPS**, así que publicarlo es decisión explícita de quien lo arranca y dura lo que dura ese proceso.

Verificado en esta red: con `--lan` el core y la interfaz quedaron escuchando en `0.0.0.0`, la página contestó `200` desde la IP de red y un WebSocket abierto contra esa IP saludó y respondió. **Sin verificar en un móvil físico**: hace falta el teléfono delante.

Lo que esto ya trae para el teléfono: interfaz táctil (pulsaciones de 44-48 px, sin auto-zoom, `safe-area`) y manifiesto para instalarla como aplicación. Lo que no arregla: **la cámara y el micrófono desde una pestaña exigen un origen seguro**, y por `http://192.168.x.x:8780` el navegador los bloquea —el botón de gesto lo dice en el propio aviso, no se queda mudo—. La voz está además bloqueada por hardware en este portátil con o sin teléfono. HTTPS en la LAN es la única salida real y sigue siendo una decisión pendiente (ver «Cómo colaborar»).

### Paso 8 · Comprobar que nada se rompió

```bash
make test      # 179 pruebas, ~59 s en esta máquina
```

Son de la biblioteca estándar de Python, no tocan la memoria real (`CORT_DOTENV=0`) ni le mueven el volumen a nadie.

### Si algo no arranca

| Síntoma | Qué está pasando | Solución |
|---|---|---|
| `No module named venv` | falta el paquete de Debian, no Python | `sudo apt install python3-venv` |
| `make: no se encontró la orden` | en Windows no hay `make` | los comandos del paso 2 «Sin `make`», o `cort.bat` ya instalado |
| `No está el venv. Crea primero las dependencias` | el lanzador no encuentra `.venv` | `make setup` (o `py -m venv .venv` en Windows) |
| Página en blanco al abrir la interfaz | `dist` no está construido y el lanzador cayó a `dev` | `make web-build`, o `make web` y abrir `http://localhost:5173` |
| «Sin conexión con el core» en el cabezal | el core no está o el puerto no es 8765 | `make launch` (no `make dev`, que no sirve interfaz); si cambiaste `CORT_PORT`, el navegador necesita el mismo puerto |
| `El core murió al arrancar (código 1)` | el puerto está ocupado por otro CORT | `pkill -f cort_core.server` y volver a arrancar |
| El móvil no abre la dirección | `--lan` no usado, otra red Wi-Fi, o el cortafuegos | arrancar con `--lan`; `sudo ufw status` si hay cortafuegos |
| La barra de audio dice `ninguna real (Dummy Output)` | el portátil no tiene salida de audio conectada | conectar altavoz o auriculares; sin eso la voz no es verificable, y CORT no finge oírla |
| El botón de la cámara se queda en rojo | dos causas distintas y el aviso las separa: origen no seguro o permiso denegado | por `http://` en la LAN el navegador **no da** la cámara (no es un bug de CORT): pruébala en `127.0.0.1`. Si el aviso dice «permiso denegado», concederlo desde el icono de la barra de dirección |
| La barra de cámara dice `sin /dev/video*` | la sonda del lanzador es Linux (`wpctl` tiene su equivalente; `/dev/video*` no existe en Windows ni macOS) | en Linux, añadir la usuaria al grupo `video` y volver a entrar; en otro SO la barra se pinta honestamente ausente |
| El mosaico de atuendos sale vacío | no hay `CORT_AVATAR_DIR`, o la carpeta no existe | escribir la ruta en `.env` y reiniciar; el selector lo dice en pantalla en vez de mostrar figuras inventadas |
| Tarda muchísimo en responder | Ollama cargando el modelo en una máquina de 2 núcleos | normal: ~1,3 tokens/s medidos. `make demo` con el apagador de acciones para probar sin esperar |


## Cómo colaborar

1. **Lee en este orden:** [`AGENTS.md`](AGENTS.md) (las 13 reglas) → [`docs/STATUS.md`](docs/STATUS.md) (fuente de verdad operativa: qué funciona *de verdad*) → [`docs/ROADMAP.md`](docs/ROADMAP.md) (nueve fases con su criterio de "listo").
2. **Una fase a la vez**, sin adelantar. Cada cierre lleva su prueba y actualiza `docs/STATUS.md` y, si cambia la cara pública, `README.md` en el **mismo commit** (regla 12).
3. **Prueba primero, código después, `make test` al final.** Nada se da por hecho por estar escrito en un chat.
4. **No se afirma sin ejecutar.** Si no puedes comprobarlo, escribe literalmente **"sin verificar"**.
5. Las decisiones de plataforma (escritorio, móvil, voz, lenguaje) están en [`docs/PLATFORM.md`](docs/PLATFORM.md): para cambiar una hay que traer un número de esta máquina.
6. Se trabaja sobre la rama **`cort-local-verified`**. `main` es historia de terceros y no se toca.

Tareas abiertas que no requieren hardware nuevo (orden sugerido, de más barata a más cara):

- **Cuerpo 3D (VRM)**: los archivos ya se listan y se sirven con ruta segura; falta el **cargador** (`@pixiv/three-vrm` o similar) y medirlo aquí — 2 núcleos, sin GPU, ~286 MiB libres con el reactor pintando. Es el siguiente ticket grande y no se simula.
- **Una figura por atuendo**: sus sprites son láminas multipo se (1280×720 con seis posturas), así que la proyección se ve como varias figuras pequeñas. Segregar una postura por archivo —o recortar la lámina— es trabajo de assets, no de código.
- **HTTPS en la LAN**: mientras no lo haya, ni la cámara ni el micrófono del navegador se activan desde el teléfono, y el botón de gesto lo dice en vez de fallar en silencio. Es una decisión de seguridad de Sandra, no un ticket de código.
- **Clima en el teléfono**: `--lan` ya funciona; falta abrir la interfaz desde un móvil físico y mirar si el reactor táctil se deja arrastrar con el pulgar, y si el gesto de desenfoque se comporta con la cámara trasera.
- **Memoria**: `remember()` deduplica sensible a mayúsculas — «Me llamo X» y «me llamo X» crean dos filas. Está anotado como deuda en `docs/STATUS.md`.
- **Acciones**: instalar `playerctl` convierte la función 18 (reproductor) en algo verificable con un «después» comprobable.
- **Voz (Fase 2)**: bloqueada hasta tener altavoz o auriculares **y** micrófono. El código existe en el roadmap y no se simula.

## Documentación

| Documento | Para qué |
|---|---|
| [`docs/STATUS.md`](docs/STATUS.md) | **Fuente de verdad operativa**: qué funciona de verdad, qué se intentó y falló, qué deuda hay |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Capas, protocolo, capa de permisos, módulos de `apps/web` — con el por qué de cada decisión |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Nueve fases, cada una con su criterio de "listo" |
| [`docs/FUNCTIONS.md`](docs/FUNCTIONS.md) | Las 72 funciones con estado y viabilidad por sistema operativo |
| [`docs/PLATFORM.md`](docs/PLATFORM.md) | Electron, Capacitor, PWA, C++/Java y voz: qué se puede hacer aquí y con qué número |
| [`docs/VISION.md`](docs/VISION.md) | Qué se traduce de Cortana a algo real |
| [`docs/DEVELOPMENT-GUIDE.md`](docs/DEVELOPMENT-GUIDE.md) | Método de trabajo |
| [`docs/AI-COPILOT-GUIDE.md`](docs/AI-COPILOT-GUIDE.md) | Cómo repartir cuota entre copilotos |
| [`AGENTS.md`](AGENTS.md) | Las reglas que cualquier agente de código debe leer antes de tocar nada |

## Créditos

**Creadores:** **Sandra Lopez** y **Askher Vargas**.

CORT se construye encima de trabajo ajeno, con licencia y atribución:

| Origen | Licencia | Qué se aprovechó |
|---|---|---|
| [adewaskar/JARVIS](https://github.com/adewaskar/jarvis) | **MIT** | Código copiado y adaptado: el reactor GLSL, las partículas, el post-proceso y la capa de efectos. Detalle de los cambios en [`apps/web/CREDITS.md`](apps/web/CREDITS.md) |
| [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) | **Apache-2.0** | Ideas y estructura de servicios |
| Guía de inicio de @Xvirus (Proyecto Jarvis) | — | Evaluada pieza por pieza contra esta máquina en `docs/PLATFORM.md` |
| Rama `scaffold/fastapi-ollama-frontend` de este mismo repo | propia | La memoria SQLite, reescrita (ruta inyectable, deduplicación, búsqueda por raíces) |
| [jaredrhod/fullstack-agent](https://github.com/jaredrhod/fullstack-agent) | **AGPL-3.0** | **Ningún código**: leer ideas sí, copiar no. Enlazar AGPL arrastraría a CORT a AGPL |
| [Halo](https://www.xbox.com/es-ES/games/halo) / Microsoft | — | Cortana es inspiración estética y de concepto. CORT es un proyecto independiente y no está afiliado |

## Licencia

MIT — © 2026 **Sandra Lopez** y **Askher Vargas**. Ver [`LICENSE`](LICENSE) y [`CREDITS.md`](CREDITS.md).
