# Arquitectura

```
 Mic / Cámara / Sensores
          │
 ┌────────▼─────────┐   WebSocket JSON
 │ services/voice   │──────────────┐
 │ services/vision  │──────────┐   │
 │ services/sensors │───────┐  │   │
 └──────────────────┘       │  │   │
                       ┌────▼──▼───▼────┐
                       │ services/core  │  Python/FastAPI
                       │ LLM · memoria  │  puerto 8765
                       │ intents · tools│
                       └────┬───────────┘
                            │ eventos (WebSocket)
                 ┌──────────▼──────────┐
                 │ apps/web (y desktop)│  React 19 · Vite · Three.js r185
                 │ reactor · HUD · chat│  GLSL + post-proceso
                 └─────────────────────┘
```

## Lenguajes (híbrido, con motivo)
- **Python**: cerebro, voz, visión, audio (ecosistema de IA).
- **TypeScript/JS**: interfaz, avatar, puente (Three.js, VRM).
- **Rust/Go** (más adelante, opcional): demonio del sistema si se necesita bajo consumo.
- **C++/MicroPython**: firmware ESP32 para sensores.

## Protocolo (v0)
Mensajes JSON por WebSocket `ws://localhost:8765/ws`:
```json
{"type":"user_message","text":"hola"}
{"type":"assistant_message","text":"...","mood":"calm"}
{"type":"greeting","text":"Hola, soy CORT.","mood":"calm"}
{"type":"state","outfit":"casual","mood":"calm","thinking":false}
{"type":"intent","action":"volume","delta":10}
{"type":"effect","kind":"pulse"}
{"type":"status","memories":18,"keep":200,"brain":"qwen2.5:0.5b","ollama":true,"actions":true}
```
Los tipos nuevos se añaden aquí primero y luego al código.
(`intent` ya se emitía desde `server.py` pero no estaba documentado: se añade aquí en cumplimiento de la regla 5 de `AGENTS.md`.)

`greeting` es el saludo y viaja **separado** de `assistant_message` por un motivo medido: el core lo manda en cada conexión, y el cliente reconecta a los tres segundos cuando el servidor se cae o se reinicia. Como `assistant_message` que fuera, cada reintento habría añadido un «Hola, soy CORT.» más a una conversación ya empezada —cuatro, en la captura que lo destapó—. El cliente lo pinta **sólo si el registro está vacío**: presentarse está bien al abrir la página, no al recuperar el cable.

`status` es **lo que CORT puede afirmar de sí mismo**: recuentos y hechos medidos en el proceso, no adornos. Se manda al conectar —después del saludo— y al cerrar cada turno, tanto si pasó por el LLM como si fue un atajo de `intents`. Sale de `status.py`, que lee tres cosas y nada más: `memory.count()` (un `SELECT COUNT(*)`, no la base entera), `brain.last_model()` y `brain.last_reachable()`, `actions.enabled()`. Los tres campos de `brain` son `null` hasta que `think()` se ejecuta de verdad: el panel no puede nombrar un modelo que todavía no habló. El cliente valida cada campo antes de pintarlo (`readStatus` en `connection.ts`) porque el panel muestra lo que recibe sin comprobarlo.

`effect` es **puntuación, no estado**: un destello, una onda, un rasguño. `kind` es uno de `glitch · pulse · scan · shake · flash`. No se guarda en ningún sitio ni se reenvía al conectar; si el cliente no lo ve, da igual. Lo emite el core cuando algo ocurre de verdad —`pulse` cuando una acción del sistema **se ejecutó**, `glitch` cuando **falló**—, no en cada mensaje: un holograma que parpadea todo el tiempo no comunica nada. El resultado de la acción viaja como `assistant_message` normal, con el número real que devolvió el mando; no hace falta un tipo nuevo.

## Capa de permisos (`actions.py`) — regla 6 de `AGENTS.md`
Un `intent` ya no es un "entendido": ejecuta. Y ejecuta **sólo lo que está en una lista cerrada**:

- `volume` → `wpctl get-volume`, luego `wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 10%+`, luego `wpctl get-volume` otra vez.
- `media` (play/pause/next) → `xdotool key XF86Audio*`.
- `screenshot` → `scrot -o <ruta>`. La ruta la genera `shot_path()` con la marca de tiempo y microsegundos —**nunca** con el texto de la orden—, en `~/Imágenes/CORT` o donde diga `CORT_SHOTS_DIR`. Después de mandar el comando se mira el archivo: si no aparece o pesa menos de 1 KiB, no cuenta como éxito.
- `launch` → una de las dos entradas de la tabla `APPS` (`archivos` → `thunar`, `terminal` → `xfce4-terminal`), arrancada **desprendida del lanzador** (`start_new_session`) para que cerrar CORT no se lleve por delante la ventana que acabas de abrir. El argv no lleva argumentos: la tabla es cerrada y lo que el usuario dice solo selecciona una de sus claves. La prueba es un `pgrep -c -x <nombre>` antes y otro después —el reposo intermedio lo fija `CORT_LAUNCH_SETTLE_S`—: si hay un proceso más, se abrió; si había alguno y sigue habiendo el mismo, CORT dice «ya estaba en marcha» en vez de atribuirse el mérito.

Lo que la hace una capa de permisos y no un `subprocess` suelto:
1. **El argv es una lista fija, ejecutada con `asyncio.create_subprocess_exec`.** No hay `shell=True`, y en los argumentos no entra ni el texto del usuario ni la salida del LLM: sólo un `delta` entero que sale de *nuestra* tabla de patrones en `intents.py`, y una clave de tecla de una constante. El texto de la orden se separa del identificador de destino por comas, nunca por concatenación.
2. **El LLM no tiene herramientas.** `brain.py` devuelve texto y ese texto se pinta; no se interpreta ni se ejecuta. Pedirle "borra la carpeta tal" no borra nada, porque no hay camino del modelo al shell. Si algún día lo hay, ese camino es este módulo y su lista.
3. **Se puede apagar sin tocar código**: `CORT_SYSTEM_ACTIONS=0` deja el asistente mudo pero inofensivo. Es también lo que hace que la suite de pruebas no le mueva el volumen a Sandra.
4. **El resultado se comprueba, no se supone.** Se mira el `returncode`, y en el volumen **se lee el nivel antes y después**: lo que CORT afirma es la diferencia que PipeWire aplicó, no la que se pidió. No es un detalle — medido en el portátil de desarrollo, con el sink en *Dummy Output* `wpctl set-volume` responde 0 y el nivel no se mueve; un filtro por `returncode` habría dicho «hecho» ante una nada. Cuando el nivel no cambia, CORT lo dice y el holograma se rasga en vez de ondular. La misma regla gobierna los otros dos mandos: la captura se **mira en disco** y la app se **cuenta en la lista de procesos**, porque un lanzador que devuelve 0 no prueba que haya ventana.
5. **Todo lo demás se declara fuera de la lista.** `equalizer` y cualquier acción no contemplada responden «no está en la lista permitida» con `glitch`, en vez de fingir un «entendido». El **brillo** tampoco está, y no por olvido: en esta máquina el archivo de control es `root:root 644` sin ACL de sesión, así que el mando fallaría siempre (medido).

## Arranque (`scripts/cort.py`) — una sola puerta, dos modos
El lanzador es **la única** forma soportada de encender CORT entero, y el doble clic (`CORT.desktop`, `cort.bat`) no hace más que llamarlo. Sin dependencias y sin framework de terminal: ANSI directo con la biblioteca estándar.

- **Decide cómo servir la interfaz**: si existe `apps/web/dist/index.html` lo sirve él, con un servidor estático de la estándar en `127.0.0.1:8780`; si no, arranca `npm run dev` y usa el 5173. No es un capricho: Vite en desarrollo son ~120 MB de RAM y un watcher de archivos, y en esta máquina eso es el 7 % de la memoria. `--serve dist|dev` anula la decisión.
- **Comprueba en vez de suponer**: el core se da por vivo cuando el puerto 8765 acepta una conexión, no cuando el proceso arranca. Y las barras de estado dicen lo que se midió —si Ollama no responde, la barra dice «apagado» en rojo, no omite la línea.
- **`--demo`** apunta `CORT_MEMORY_DB` a una base en `/tmp`. Es la única forma segura de enseñar CORT a alguien: sin esa bandera, una conversación de prueba deja recuerdos escritos en la memoria real.
- **Ctrl+C cierra todo**: los hijos se terminan desde el lanzador, no se dejan huérfanos. Con la salida redirigida a un archivo `stdout` pasa a búfer de línea; si no, las barras se quedaban en memoria y el log acababa en blanco justo en la parte que interesa.
- Sin color cuando no hay terminal (`sys.stdout.isatty()` falso) o con `--no-color`: se quitan los códigos de escape **conservando el texto**.

## Módulos de `services/core/cort_core`
- `brain.py` — habla con Ollama a través de una **cadena de sustitución** (`CORT_LLM_CHAIN`): prueba los modelos en orden y usa el primero que responda. Antes de intentarlo pide `/api/tags` y **descarta por tamaño** lo que no cabe en RAM (`CORT_LLM_MAX_MODEL_MIB`, 700 MiB) — cargar `qwen3.5:2b` en esta máquina la congeló. Manda `keep_alive=30m` en cada petición: sin él Ollama descarga el modelo y la siguiente conversación paga 113 s de carga. Timeout en `CORT_LLM_TIMEOUT_S`. Distingue "Ollama no está" de "la cadena no respondió": confundirlos hace depurar un servidor caído que no existe. Si nada funciona, modo eco.
- `intents.py` — comandos locales rápidos ("sube el volumen") sin gastar LLM. Devuelve una acción estructurada; **no ejecuta nada**.
- `actions.py` — la capa de permisos: convierte esa acción estructurada en un comando real de la lista cerrada (arriba). Recibe un `runner` inyectable para que los tests comprueben el argv **sin tocar el sistema de audio de Sandra**.
- `status.py` — la telemetría que el panel de la interfaz pinta: recuento de recuerdos, qué modelo habló la última vez y si la capa de permisos está encendida. Lee, no calcula nada propio; si un valor no se puede medir, manda `null` en vez de un adorno.
- `memory/store.py` — SQLite persistente en `services/core/data/memory.db` (fuera de git: son datos personales), o donde diga `CORT_MEMORY_DB` si se quiere otra cabeza para el mismo cuerpo: una demo, una segunda persona en el mismo PC, o una base vacía para sacar una captura sin tocar los datos de nadie. `remember`, `recall`, `context_for`, `prune`, `name_of_user`, `all`, `count`. `context_for` es el que arma el prompt: si la pregunta no comparte raíces con ningún recuerdo, devuelve los más recientes en vez de nada, porque un prompt sin contexto hace que el modelo niegue que te conoce. `prune` se llama al arrancar el core y **nunca borra la fila del nombre**, que es de la que dependen el saludo y "¿cómo me llamo?".
- `memory/facts.py` — convierte frases del usuario ("me llamo X", "estudio Y") en hechos almacenables.
- `outfit.py` — atuendo según hora y temperatura.
- `server.py` — FastAPI + WebSocket. Por cada mensaje: guarda los hechos detectados, y si el texto pregunta por la identidad del usuario responde desde la memoria (sin LLM); si no, inyecta los recuerdos relevantes como mensaje de sistema antes de llamar a `brain.think`. Si el texto casa con un `intent`, lo ejecuta con `actions.perform` y **emite el resultado**: `pulse` si fue, `glitch` si no. La acción va con `await` sobre `asyncio.create_subprocess_exec`, nunca `subprocess.run` — un `run` bloqueante pararía el bucle que atiende a todos los clientes. Cada turno termina con un `status`, tanto si pasó por el modelo como si fue un atajo de `intents`: los hechos de un mensaje se guardan antes de mirar los intents, así que el contador puede cambiar sin que hable ningún LLM.

La memoria es SQLite con búsqueda por raíces de 4 letras, no embeddings: `sentence-transformers` + `faiss` (como en la rama remota `scaffold`) piden ~1,5 GiB de RAM y el equipo de desarrollo tiene 1,8 GiB en total. Cambiar esto es un cambio de arquitectura que se documenta aquí antes de programarse.

## Módulos de `apps/web` (React + Vite + Three)
Transplantado de `~/Documentos/jarvis` (**MIT**, ver `apps/web/CREDITS.md`). Sin `zustand` ni `drei` a propósito: menos dependencias y menos RAM en una máquina de 1,8 GiB.

- `cort/palette.ts` — la paleta azul/violeta estilo Cortana. Cada atuendo tiene su `core` y su `hot`; `THINKING_HOT` es el magenta que toma el anillo mientras el core procesa. **Un solo sitio** define el color: si el HUD y el orbe discreparan, la interfaz parecería rota.
- `cort/connection.ts` — el WebSocket. Mantiene dos cosas distintas y esa separación es el diseño entero:
  - un *snapshot* inmutable para React, vía `useSyncExternalStore`;
  - un objeto **mutable** `target` (color, hot, spin, open) que la escena persigue con `lerp` cada frame.
  Si el color se entregara por estado de React, cambiar de atuendo parpadearía en vez de respirar, y la escena entera se reconciliaría 60 veces por segundo.
- `scene/Core.tsx` — el reactor. **Un solo quad mirando a cámara** con un shader de coordenadas polares: la geometría no dibuja nada, todo es función de radio y ángulo (anillo erosionado por fbm, polvo, barrido radar, líneas concentricas). Por eso el borde es turbulencia real por píxel y no una malla deformada.
- `scene/Particles.tsx` — 4000 puntos en una cáscara que se expande con el volumen.
- `scene/Scene.tsx` — `EffectComposer` con Bloom + aberración cromática + ruido + viñeta. Eso, y no la geometría, es lo que convierte líneas aditivas en "holograma". `multisampling={0}`: no hay una sola arista poligonal que suavizar.
- `ui/Hud.tsx` — estado, registro de mensajes y entrada de texto. El `Clock()` del cabezal tiene su propio temporizador (`setTimeout` hasta el siguiente segundo exacto, luego `setInterval`) en vez de vivir en el `Snapshot`: colgado del estado global, cada segundo del mundo obligaría a reconciliar el HUD entero. `font-variant-numeric: tabular-nums` para que los dígitos no bailen al cambiar.
- `ui/Telemetry.tsx` — el panel de arriba a la derecha: recuerdos, cerebro y estado de la capa de permisos, pintados del tinte del atuendo. Escrito sin dependencias nuevas a propósito — ni `zustand` ni `framer-motion` — porque aquí cada librería son megas de RAM que el reactor deja de tener. No se pinta hasta que llega el primer `status`.
- `ui/Effects.tsx` — la capa de un solo disparo. Vive **fuera** de `.hud` y cuelga a pantalla completa mientras suena algo; al terminar se desmonta, así que una sesión sin efectos no tiene ningún nodo decorativo en el DOM. Repite el `key` con la marca de tiempo del mensaje para que cinco `flash` seguidos sean cinco destellos y no uno que se re-aplica.

El reactor mide **18 fps sin GPU** en el equipo de desarrollo. Cualquier añadido (más partículas, un segundo paso de blur, un avatar VRM) se nota en ese número.
