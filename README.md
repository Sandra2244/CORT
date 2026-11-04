# CORT — Cognitiva · Omnipresente · Rapsodia · Terminal

Asistente local, privado y con voz, que corre en una laptop modesta con Linux y se
abre también en el teléfono. Nada de CORT sale del equipo: el puente es un proceso
Python en `127.0.0.1`, la interfaz es una página servida por ese mismo proceso y las
respuestas se deciden con reglas locales y con los sensores y mandos reales del equipo.

**Autoría y derechos: Askher Vargas y Sandra Lopez (2026).** Soporte y permisos:
`Sandrasofialopezgomez3@gmail.com` · `Carlosa3325@gmail.com`.

Licencia de atribución con no monetización (ver `LICENSE` y `AVISO_LEGAL.md`): se
puede usar, estudiar y modificar libremente, pero **no se puede vender ni monetizar
sin dar la autoría y sin escribir antes a esos correos**.

Referencias de estilo, no dueñas de CORT: la maqueta de JARVIS de TechEnClair sirvió
de andamio de plantilla y se rediseñó; la estética holográfica de Cortana (Halo) es
sólo inspiración visual. Ver `cort-web/PROCEDENCIA.md`.

---

## Qué hace, con lo que se pudo medir

| Función | Estado | Cómo se verificó |
|---|---|---|
| Puente local con protocolo JSON sobre WebSocket | real | `cort-bridge/cort_server.py`, un solo escritor por conexión |
| Hablar en voz alta | real | espeak-ng (factor 0,14 ms de CPU por s de audio) y Piper es_ES (1,90 / 2,55) |
| Escuchar (STT local) | real con WAV | Vosk `vosk-model-small-es-0.42`: transcribe 3,9 s de audio en 7,0 s |
| Micrófono en la Classmate | **no hay hardware** | `pactl list short sources` sólo muestra `auto_null.monitor` |
| Altavoz en la Classmate | **no hay hardware** | sólo `auto_null`; con un sink nulo temporal el audio salió (RMS 2521) |
| Abrir/cerrar aplicaciones, ventanas, volumen, brillo, captura, notificaciones | real | 12 acciones en `cort-bridge/cort_acciones.py`, probadas en el equipo |
| Cerebro con Ollama | real pero limitado | 6 modelos en disco; el más ligero pide ~511 MB y hay 227–266 MB libres |
| Reglas locales (hora, fecha, clima, temperatura, estado del equipo) | real | `/proc`, open-meteo y sensores del kernel |
| Auditoría de seguridad | real, informa y no borra | arranque, procesos, archivos y permisos |
| Vida diaria: lista de compras, notas, recordatorios, temporizadores, «léeme la selección» | real | `cort-bridge/cort_vida.py`; 0,34 s de frase a respuesta y temporizador de 5,00 s disparado a los 5,52 s |
| Núcleo con reja: frase → plan JSON → validar → ejecutar → verificar | real | `cort-bridge/cort_intenciones.py`; 18/18 en `prueba_intenciones.py` y 6+12 en `prueba_nucleo.py`, siempre en arena (`CORT_HOME=/tmp`) |
| Bajar y probar modelos Ollama desde la pantalla | real | panel `#cort-cerebro`: pesos medidos en disco, RAM estimada, `descargar` con progreso y `probar el cerebro` con latencia medida |
| Sonda automática del cerebro | real, disparada por la RAM | `auto_sonda()` mide el modelo en cuanto hay RAM libre y escribe `mediciones/medicion-cerebro.json`; 11/11 en `prueba_sonda.py` con Ollama falso |
| Palabra de despertar («cort») | real la lógica, pendiente de micro | `filtro_wake()` 11/11 en `prueba_wake.py`; ventana de 8 s y variantes acústicas cubiertas |
| Canal de actualización desde el repo | real | `cort-bridge/cort_actualiza.py`; 7/7 en `prueba_actualiza.py`. Avisa y da el comando, **no se autoinstala** |
| Escáner de capacidades (el equipo se adapta solo) | real medido | `cort-bridge/cort_perfil.py`; 14/14 en `prueba_perfil.py`. En esta laptop: nivel 0, `AVX no`, 397 ms de ida y vuelta por WebSocket y la interfaz bajando a 30 fps con las scanlines apagadas |
| Gestos con cámara → mover ventanas | real medido | `cort-bridge/cort_vision.py`; 12/12 en `prueba_vision.py` y 7/7 en `cort_vision.py selftest`. Webcam real: YUY2 320×240 a **15 cuadros/s**, **1,9–4,6 ms** de cálculo por cuadro, worker de 33,7 MB y **ninguna imagen guardada**. Una persona sentada quieta dispara **0 gestos** (era 8 cada 8 s antes de cerrar el umbral de movimiento) |
| Mapa propio (Leaflet + OSM) | **aparcado (F6)** | recortable por acuerdo; no se finge un mapa |
| Carisma, memoria escrita y autocorrección | real medido | `cort-bridge/cort_memoria.py`; 23/23 en `prueba_memoria.py` y 16/16 en su `selftest`. Ciclo memoria→prompt→revisión en **1,56–3,21 ms por frase**; constitución de **786 caracteres** dentro del `system`; **0 entrenamientos de pesos** (sin AVX y con ~200 MB libres no cabe) — CORT aprende escribiendo, y lo que guarda se ve en `memoria.json` con su camino completo |
| ¿Habría que escribir partes en C o Rust? | decidido con medida | `mediciones/s5-medida.sh`: un ayudante C de X11 (16 KB, compila en **826 ms**) gana **8–12 ms por orden** a `wmctrl`, que es ~2 % del trayecto de una orden. Rust **sí está instalado** (`rustc 1.98.1`) y su bucle corre 8 veces más rápido que Python, pero **tarda 33,5 s en compilar** tres líneas en esta laptop. No entra ninguno en el release; Java/Kotlin sólo en el APK |
| PWA instalable (el teléfono) | real medido | service worker `activated` y `cort-v1` con las 9 piezas del programa; `CORT_BIND`/`CORT_TLS` para HTTPS en LAN |
| Panel de APK nativo | en fase | se compila en GitHub Actions, no en esta máquina |

Cada mensaje del puente lleva `origen`: `"real"` o `"no disponible"`. Si algo no se
puede, CORT lo dice con el motivo y con el número que falta — no simula.

---

## Arquitectura

```
cort-bridge/            proceso único, dos puertos
  cort_server.py        8766 HTTP (interfaz) + 8765 WebSocket (protocolo JSON)
  cort_intenciones.py   la reja del núcleo: verbos y raíces permitidos, confirmación humana
  cort_voz.py           voz de salida (espeak-ng / Piper) y escucha (Vosk)
  cort_acciones.py      manos en Linux: wmctrl, pactl, xdotool, scrot, xclip, apt, dpkg
  cort_archivos.py      mover/copiar/renombrar con verificación después
  cort_vida.py          compras, notas, pendientes, temporizadores, selección leída
  cort_actualiza.py     lee las etiquetas del repo y avisa; no descarga ni cambia nada
  cort_perfil.py        escanea el equipo (CPU/AVX, RAM, GPU, cámara, temperatura) y decide
                        el nivel de cerebro y qué se apaga para que lo demás quepa
  cort_vision.py        la mirada: lee la webcam cuadro a cuadro, saca piel+movimiento y
                        traduce cuatro gestos en órdenes de ventana (nada se guarda)
  cort_memoria.py       la persona: constitución, memoria escrita en disco, autocorrección
                        antes de hablar e iniciativa al conectar (nunca reentrena pesos)
  cort_state.json       preferencias personales (ignoradas por git; CORT_STATE elige la ruta)
cort-web/
  index.html            la interfaz (rediseñada sobre la plantilla)
  cort/cort-mock.js     enlace con el puente; lo que no hay puente se simula y se dice
  cort/cort-orbe.js     capa de partículas del orbe (medida, no decorada)
  cort/cort-ui.js       idioma español, avisos honestos, testigo de voz, bandeja de tirador,
                        panel del cerebro y aviso de versión
  cort/cort-style.css   recorte HUD, paneles y testigos
scripts/                pruebas: prueba_intenciones · prueba_nucleo · prueba_sonda ·
                        prueba_wake · prueba_actualiza · prueba_perfil · prueba_vida ·
                        prueba_voz · prueba_acciones · prueba_vision · prueba_memoria ·
                        arranca_con_sonda.sh
PLAN_NUCLEO.md          las cinco capas del núcleo y lo medido fase por fase (F9…S4)
PLAN_FASES.md           las fases F1–F8 con lo cerrado y lo pendiente
INFORME_FUNCIONES.md    censo de las 34 órdenes de lectura de la plantilla
```

El núcleo son cinco capas y ninguna puede saltarse a la siguiente:

```
oído (Vosk / bandeja escrita)
  → compilador (Ollama con format:"json", temperature:0, num_ctx:2048)
    → reja (lista blanca de verbos y raíces; si duda, pide confirmación humana)
      → ejecutor (argumentos, nunca shell)
        → verificador (mide el resultado y lo cuenta con origen real o "no disponible")
```

La regla que sostiene todo: **el modelo nunca toca el disco, la red ni el teléfono.**
Propone un JSON; decide la reja.

Un navegador habla con el puente por `ws://127.0.0.1:8765/ws`. El puente nunca usa
`shell=True`: ejecuta listas de argumentos y compara lo que le piden contra lo que
existe en el equipo (ventanas abiertas, entradas `.desktop`).

---

## Instalación en Linux (MX Linux / XFCE, probado en una Classmate con 2 núcleos y 1851 MB)

1. Copiar el repo y entrar en él:

   ```bash
   cd CORT
   ```

2. Crear el entorno con las dependencias de voz y del puente:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install aiohttp vosk piper-tts
   ```

3. Bajar los modelos (fuera del repo, en `~/.local/share/cort`):

   ```bash
   mkdir -p ~/.local/share/cort/voz ~/.local/share/cort/modelos
   # voz natural (opcional; espeak-ng ya viene con el sistema y es el motor por defecto)
   curl -sL -o ~/.local/share/cort/voz/es_ES-mls_10246-low.onnx \
     https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls/low/es_ES-mls_10246-low.onnx
   curl -sL -o ~/.local/share/cort/voz/es_ES-mls_10246-low.onnx.json \
     https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls/low/es_ES-mls_10246-low.onnx.json
   # escuchar (Vosk, 58 MB)
   curl -sL -o /tmp/vosk-es.zip https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
   unzip -q /tmp/vosk-es.zip -d ~/.local/share/cort/modelos/
   mv ~/.local/share/cort/modelos/vosk-model-small-es-0.42 ~/.local/share/cort/modelos/vosk-es
   ```

4. Arrancar:

   ```bash
   .venv/bin/python -u cort-bridge/cort_server.py
   ```

   Abrir <http://127.0.0.1:8766/index.html>.

5. Comprobar qué ve el equipo, sin tocar nada:

   ```bash
   .venv/bin/python cort-bridge/cort_voz.py estado
   .venv/bin/python cort-bridge/cort_acciones.py estado
   ```

6. Cerebro local (opcional, y sólo cuando la máquina respire):

   Ollama se instala desde su página oficial, **descargando el instalador y leyéndolo
   antes de ejecutarlo** (no se corre `curl … | sh` a ciegas). En MX Linux vale el
   paquete `.deb` para amd64 de esa página, o el tarball: se descomprime en
   `/usr/local/bin` y se arranca con `ollama serve`.

   Con el puente corriendo, abrir el panel **◉** de la interfaz: lista los modelos que
   hay en disco con su peso medido y cuánta RAM pedirían, deja **descargar** los que
   faltan y **probar el cerebro** con una frase. Si la cuenta no cabe, no lo carga y
   dice la cifra en vez de congelar el equipo.

### Qué guarda CORT de ti, dónde, y cómo borrarlo

Todo son archivos de texto en `~/.local/share/cort/` (`CORT_DATOS`). Se pueden abrir con
cualquier editor y borrar sin desinstalar nada:

| Archivo | Qué hay dentro | Cómo se llena |
|---|---|---|
| `memoria.json` | `preferencias` (nombre, ciudad, tono, gustos), `hechos` (lo que pediste recordar), `correcciones` (lo que no quieres que diga), `avisos` (cuándo habló por última vez por su cuenta) | diciendo «recuerda que…», «llámame…», «no me digas X, dime Y» |
| `constitucion.md` | los 7 principios que viajan en el `system` de cada frase | se edita a mano; si tiene más de 40 caracteres, CORT usa este y no el de fábrica |
| `cort_state.json` | modelo elegido y preferencias del puente | desde el panel ◉ o la consola |
| `vida/` | lista de compras, notas y pendientes con fecha | «anota que…», «pon como pendiente… para el…» |

Borrar la memoria es literalmente borrar el archivo, y CORT deja de saber esas cosas:

```bash
cp ~/.local/share/cort/memoria.json ~/memoria-cort-respaldo.json && rm ~/.local/share/cort/memoria.json
```

No entra audio ni imagen: los cuadros de la cámara se tiran después de sacar cuatro números
(fase S2), y a `memoria.json` sólo va texto que tú pediste recordar o corregir.

### Como servicio de usuario (que arranque solo)

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/cort.service <<'UNIT'
[Unit]
Description=CORT — puente local
After=default.target

[Service]
WorkingDirectory=%h/Documents/CORT
ExecStart=%h/Documents/CORT/.venv/bin/python -u %h/Documents/CORT/cort-bridge/cort_server.py
Restart=on-failure

[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload && systemctl --user enable --now cort
```

### Lanzador de escritorio

`~/.local/share/applications/cort.desktop`, con `Exec` apuntando al script de arranque
del repo; aparece en el menú de XFCE como «CORT».

---

## Variables que cambian el comportamiento

| Variable | Para qué | Por defecto |
|---|---|---|
| `CORT_VOZ_MOTOR` | `rapida` (espeak-ng) o `natural` (Piper) | `rapida` |
| `CORT_VOZ` | `1` habla cada respuesta, `0` sólo texto | `1` |
| `CORT_MIC` | `1` enciende la escucha continua al arrancar | `0` |
| `CORT_WAKE` | `1` el micro sólo obedece después de oír «cort» | `0` |
| `CORT_WAKE_VENTANA` | segundos de escucha tras la palabra | `8` |
| `CORT_AUTOSONDA` | `1` mide el cerebro solo, cuando la RAM lo permita | `0` |
| `CORT_AUTOSONDA_UMBRAL` | MB libres a partir de los cuales se atreve a cargar | `900` |
| `CORT_ACTUALIZA` | `1` revisa las etiquetas del repo cada 6 h | `1` |
| `CORT_PERFIL_CICLO` | segundos entre re-escaneos del equipo; sólo avisa si el nivel cambia | `900` |
| `CORT_REPO` / `CORT_VERSION` | con qué repo y qué versión comparar (si no, se derivan de `git remote` y `git describe`) | derivados |
| `CORT_BIND` / `CORT_TLS` | abrir el puente a la red local, con certificado `cert,clave` | `127.0.0.1`, sin TLS |
| `CORT_RAM_MIN` | MB libres mínimos para cargar un modelo | según modelo |
| `CORT_HOME` / `CORT_DATOS` | dónde guarda estado, voz, memoria y registro | `~/.local/share/cort` |
| `CORT_STATE` | archivo de preferencias del puente; en las pruebas de arena apunta a `/tmp` para no escribir en el tuyo | `<esta carpeta>/cort_state.json` |
| `CORT_MEM_LIMITE` | caracteres de memoria que se re-inyectan en el prompt de cada frase | `420` |
| `CORT_WS_PORT` / `CORT_WEB_PORT` | puertos del puente | `8765` / `8766` |

---

## Límites dichos con número

- **Memoria.** Con 1851 MB totales y 227–266 MB libres con el navegador abierto, ningún
  modelo de Ollama cabe cargado a la vez que la interfaz. El puente lo bloquea y dice la
  cifra en vez de congelar el equipo.
- **Audio.** En esta laptop el códec analógico y el jack de 3,5 mm no funcionan: sólo
  existe `auto_null`. CORT sintetiza y entrega el audio (probado con un sink nulo:
  RMS 2521, pico 32754), pero suena únicamente si se conecta HDMI o un dongle USB de audio.
- **Micrófono.** No aparece ninguna fuente de captura. La escucha por el teléfono está
  en la fase F7.
- **CPU.** El tope de fotogramas de la interfaz en esta máquina no lo pone el orbe: lo
  pone la disputa por los 2 núcleos (medido con `load 5,9` y 1,36 GB de swap).

## Pruebas

Todo lo que toca el equipo se prueba en **arena**: `CORT_HOME` y `CORT_DATOS` apuntan a
`/tmp`, `CORT_MEDIA_SIMULA=1` y `CORT_NUCLEO_FALSO` fingen el plan. Ninguna de estas
pruebas mueve una carpeta real ni escribe en tu lista de compras.

```bash
.venv/bin/python scripts/prueba_intenciones.py   # la reja: 6 planes buenos pasan, 12 malos se frenan
.venv/bin/python scripts/prueba_nucleo.py        # frase → plan → reja → ejecución → verificación
.venv/bin/python scripts/prueba_wake.py          # palabra de despertar y su ventana de 8 s
.venv/bin/python scripts/prueba_actualiza.py     # canal de versión contra un GitHub falso
.venv/bin/python scripts/prueba_perfil.py        # el escáner: 6 equipos fingidos + la medida real
.venv/bin/python scripts/prueba_vision.py        # la mirada: cuadros, gestos y ventanas reales
.venv/bin/python scripts/prueba_memoria.py       # memoria, constitución y autocorrección por WebSocket
.venv/bin/python scripts/prueba_sonda.py         # la auto-sonda con un Ollama falso en arena
.venv/bin/python scripts/prueba_voz.py           # órdenes de voz por WebSocket y descarga del WAV
.venv/bin/python scripts/prueba_acciones.py      # pc_estado, detect_apps, apt, abrir/cerrar ventana
```

`prueba_acciones.py` lanza y cierra VLC: es la prueba de que la mano funciona de verdad.

```bash
# F4 en arena: el puente de prueba usa CORT_DATOS=/tmp y no toca tu lista real
CORT_HOME=/tmp/cort-arena CORT_DATOS=/tmp/cort-arena/datos CORT_WS_PORT=8775 \
  .venv/bin/python -u cort-bridge/cort_server.py &
CORT_WS_PORT=8775 .venv/bin/python scripts/prueba_vida.py   # lista, notas, pendientes y selección
```

Para ver la interfaz contra un puente de arena sin tocar el tuyo, la página acepta
`?puente=` con una URL `ws://` o con el puerto a secas (así se midieron las pantallas de
este repo). Lo del puerto suelto existe porque la página lleva 8765 fijado: si `?puente=8775`
no significara nada, la pestaña de arena se conectaría en secreto al puente vivo y allí se
mediría otra cosa. Antes de teclear, comprueba el destino real con
`CORT_puente().url` en la consola:

```
http://127.0.0.1:8776/index.html?puente=ws%3A%2F%2F127.0.0.1%3A8775%2Fws
http://127.0.0.1:8776/index.html?puente=8775
```

## Lo que se pidió y todavía no está, dicho con número

- **Mover ventanas con la cámara (PC y teléfono)** hace falta un modelo de visión. En
  esta máquina, con 2 núcleos y 1851 MB, quedan 172–233 MB libres y Ollama está
  apagado; un modelo de manos (MediaPipe o TFLite) corre en el Galaxy A16, no aquí.
  Se planifica como fase propia, no se improvisa.
- **Vincular PC y Android para que CORT comparta memoria** necesita tres cosas que
  aún no están todas: `CORT_BIND` abierto, TLS con certificado propio y un token.
  Sin HTTPS el navegador del teléfono no instala la PWA ni deja usar el micrófono,
  y compartir la memoria sin cifrar por la red local sería exponerla. El APK (F11/F12)
  es el que resuelve el frente.
- **El cerebro cargado**: la puerta de RAM manda. Con la interfaz abierta ningún
  modelo de los 6 en disco cabe; `auto_sonda()` lo mide solo en el turno en que la
  máquina respire.
