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
| Mapa propio (Leaflet + OSM) | **aparcado (F6)** | recortable por acuerdo; no se finge un mapa |
| PWA instalable (el teléfono) | real medido | service worker `activated` y `cort-v1` con las 9 piezas del programa; `CORT_BIND`/`CORT_TLS` para HTTPS en LAN |
| Panel de APK nativo | en fase | se compila en GitHub Actions, no en esta máquina |

Cada mensaje del puente lleva `origen`: `"real"` o `"no disponible"`. Si algo no se
puede, CORT lo dice con el motivo y con el número que falta — no simula.

---

## Arquitectura

```
cort-bridge/            proceso único, dos puertos
  cort_server.py        8766 HTTP (interfaz) + 8765 WebSocket (protocolo JSON)
  cort_voz.py           voz de salida (espeak-ng / Piper) y escucha (Vosk)
  cort_acciones.py      manos en Linux: wmctrl, pactl, xdotool, scrot, xclip, apt, dpkg
  cort_state.json       preferencias personales (ignoradas por git)
cort-web/
  index.html            la interfaz (rediseñada sobre la plantilla)
  cort/cort-mock.js     enlace con el puente; lo que no hay puente se simula y se dice
  cort/cort-orbe.js     capa de partículas del orbe (medida, no decorada)
  cort/cort-ui.js       idioma español, avisos honestos, testigo de voz y de PC
  cort/cort-style.css   recorte HUD, paneles y testigos
scripts/                pruebas por WebSocket (prueba_voz.py, prueba_acciones.py, prueba_vida.py)
PLAN_FASES.md           las fases F1–F8 con lo cerrado y lo pendiente
INFORME_FUNCIONES.md    censo de las 34 órdenes de lectura de la plantilla
```

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
| `CORT_RAM_MIN` | MB libres mínimos para cargar un modelo | según modelo |
| `CORT_HOME` / `CORT_DATOS` | dónde guarda estado, voz y registro | `~/.local/share/cort` |
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

```bash
.venv/bin/python scripts/prueba_voz.py        # órdenes de voz por WebSocket y descarga del WAV
.venv/bin/python scripts/prueba_acciones.py    # pc_estado, detect_apps, apt, abrir/cerrar ventana
```

`prueba_acciones.py` lanza y cierra VLC: es la prueba de que la mano funciona de verdad.

```bash
# F4 en arena: el puente de prueba usa CORT_DATOS=/tmp y no toca tu lista real
CORT_DATOS=/tmp/cort-arena/datos .venv/bin/python -u cort-bridge/cort_server.py &
.venv/bin/python scripts/prueba_vida.py      # lista, notas, pendientes y selección
```
