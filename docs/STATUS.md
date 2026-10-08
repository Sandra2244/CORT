# STATUS — estado real del proyecto

> **Este archivo es la fuente de verdad operativa.** Cualquier agente (Qoder, OpenCode, Claude, DeepSeek)
> lee `AGENTS.md` + este archivo y continúa desde aquí. No se confía en chats anteriores.
> Última verificación: **2026-10-07**, ejecutando comandos, no recordándolos.

## Fase actual
**Fase 4 empezada: CORT ya ejecuta en vez de decir «entendido»**, y la verificación en vivo enseñó dos cosas que leer el código no enseñaba (el `returncode` de `wpctl` miente, y este portátil no tiene por dónde sacar audio). Efectos del holograma verificados en el navegador; la capa táctil está escrita, **sin verificar en un móvil real**. → Siguiente: decidir el **alcance de red** para el Samsung A16 (el core sigue atado a `127.0.0.1` a propósito) y el HUD de paneles (`Blades.tsx`, MIT). La **Fase 2 (voz)** y la **3 (VRM)** siguen pendientes de una decisión de hardware, no de código: 2 núcleos a 1,46 GHz.

## Respaldo
Repo: `git@github.com:Sandra2244/CORT.git` (funciona con la clave `~/.ssh/id_ed25519`, verificada).
- Rama **`cort-local-verified`** ← esta carpeta. Es la única que está verificada ejecutándola.
- Rama **`main`** ← lo que subió Copilot en octubre. Contiene humo: ver "Hallazgo" abajo.
- Rama **`scaffold/fastapi-ollama-frontend`** ← 50 archivos, más avanzada, de la que se trasplantó la memoria.
- **No hay merge todavía.** Las tres historias son independientes (`git merge-base` = vacío). Fusionar es decisión consciente, no un push.

## Qué existe y está verificado funcionando
| Cosa | Evidencia |
|---|---|
| Core `server/brain/intents/outfit` + `memory/` | compila, `make dev` escucha en `127.0.0.1:8765` |
| **67 pruebas** | `make test` → `Ran 67 tests ... OK` (tarda ~40 s: la poda mete 300 recuerdos de verdad). Repartidas en `test_logic` 8, `test_brain` 10, `test_memory` 24, `test_protocol` 6, `test_actions` 19. Quedan `ResourceWarning` por bases de datos sin cerrar al morir el intérprete: ruido, no fallos |
| **Poda de memoria (Fase 1.1)** | 302 recuerdos → `prune(keep=200)` deja 201, y `context_for` responde en **1-4 ms** (criterio del roadmap: <1 s). Conectada al arranque del core. Verificado: tras arrancar con la poda, el saludo sigue siendo "Hola de nuevo, Sandra." |
| WebSocket completo | saludo, `state` con atuendo, modo eco en ~0.3 s, intents sin LLM |
| **Chat con Ollama (función 1)** | Por WebSocket real contra el core: "¿qué sabes de mí hasta ahora?" → **"Sandra, …"**. La memoria llega al modelo. Lento: 48–66 s por turno con el modelo caliente |
| **Guarda de memoria del LLM** | Con el Ollama de verdad: detecta los 4 modelos instalados y descarta `qwen3.5:2b` (2614 MiB) y `airaos-local` (718) por no caber. 10 pruebas con `httpx.MockTransport`, sin encender modelos |
| **Memoria persistente (Fase 1)** | Proceso 1: "me llamo Sandra" → guarda `El usuario se llama Sandra`. Se mata el proceso. Proceso 2: saluda **"Hola de nuevo, Sandra."** y "¿cómo me llamo?" → **"Te llamas Sandra."** sin pasar por el LLM |
| **Interfaz holográfica (React+Three)** | Capturas de pantalla reales a `localhost:5173`: anillo azul/violeta Cortana, polvo de 4000 puntos, bloom. **18 fps sin GPU.** `make web-build` → `✓ built`. Enviar "me llamo Sandra y estudio ingeniería" por la UI escribió `El usuario estudia ingeniería` en SQLite |
| Reacción a estados | Con `thinking=true` el anillo pasó a magenta y la cabecera a "CORT procesando"; al terminar volvió a azul |
| **Efectos (`Effects.tsx`, MIT)** | Medido en el navegador con un `MutationObserver` puesto **antes** de hacer clic: 1 aparición, clases `fx-play fx-pulse`, 2 nodos `.fx-wave`, `animation-duration: .9s`, y `--accent: #93a0ff` — que es el color `ui` del atuendo `casual` en `palette.ts`. La onda sale del mismo sitio que el anillo, no de un color fijo. **El primer intento de medirlo dio `false` y era falso**: el pulso dura 900 ms y mi sonda llegó tarde |
| **Protocolo WebSocket** | `services/core/tests/test_protocol.py` (6 pruebas) mueve el `TestClient` de Starlette de verdad: saludo al conectar, `intent → effect → assistant_message` en ese orden, y que un `kind` desconocido no llega a pintarse. El ejecutor va sustituido por un fake: la suite **no le mueve el audio a Sandra** |
| **Acciones reales (capa de permisos)** | `actions.py` ejecuta `wpctl`/`xdotool` con argv fijo. **Verificado de extremo a extremo con el core levantado y un websocket de verdad**: "baja el volumen" → intent → comando real → lectura del nivel → `effect` → mensaje. 19 pruebas nuevas en `test_actions.py`, tres de ellas ejecutando mandos reales inofensivos (`true`, `false`, un binario que no existe) |

## Qué NO existe (aunque otros documentos y chats lo dieron por hecho)
`apps/desktop/` (Electron/overlay) · `services/voice`, `vision`, `audio`, `sensors` · `packages/` · `scripts/context-pack.py` · `upstream/` vacío (URLs con `REEMPLAZAR`).
`LICENSE` sí existe, pero **en las ramas remotas, no en esta carpeta**.

## Hallazgo: el servicio de voz del remoto era humo
`origin/main:services/voice/src/main.py` (143 líneas) define `/stt`, `/tts`, `/wake-word/detect`, `/vad/detect` y **no hace ni una llamada real** a Whisper, Piper o cualquier motor: la única aparición de "piper" es un string en un diccionario de config. Parece un servicio que funciona; devuelve `ok` a todo.
**No transplantar sin reescribir.** Lo aprovechable de esa rama es `services/core/src/main.py` (personalidad, endpoints) y la **`scaffold`**: `backend/app/services/memory.py` (trasplantada hoy) y sus adaptadores STT/TTS, que sí intentan llamar a los motores.

## Transplante hecho hoy
Origen: `origin/scaffold:.../backend/app/services/memory.py` (código propio, MIT).
Destino: `services/core/cort_core/memory/{store,facts}.py`.
Correcciones aplicadas al copiar:
1. La versión original creaba la carpeta de la BD **en el momento del `import`** → los tests no se podían aislar. Ahora la ruta se inyecta por el constructor.
2. Sin `created_at` ni deduplicación → añadidos (`content UNIQUE`).
3. Búsqueda `LIKE '%término%'` no encontraba "llama" al preguntar "llamo" → búsqueda por raíces de 4 letras con lista de stopwords.
4. Se **descartó faiss + sentence-transformers**: piden ~1,5 GiB de RAM y esta máquina tiene 1,8 GiB en total, sin GPU.

## Limitaciones reales de esta máquina (marcan el roadmap entero)
- **2 núcleos a 1,46 GHz, 1,8 GiB de RAM, sin GPU, y swap de 2 GiB que se llena.** El límite no es sólo la memoria: el número de núcleos es lo que deja la generación en ~1,3 tokens/s. Ningún modelo de más de ~700 MiB cabe. Hay 4 modelos en `~/.ollama` (`qwen2.5:0.5b` 379 MiB, `qwen3:0.6b` 498, `airaos-local` 718, `qwen3.5:2b` 2614) y **4 blobs `-partial`** = descargas interrumpidas.
- El server de Ollama **no arranca solo**; hay que lanzar `ollama serve`. CORT funciona sin él (modo eco).
- **No hay por dónde salir con audio.** Único chip de sonido: `HDA Intel PCH` = *Intel Valleyview2 HDMI*, perfiles sólo HDMI, `Active Profile: off`, y el puerto `hdmi-output-0` reporta **not available**. El sink por defecto es *Dummy Output*, que acepta cualquier `set-volume` con returncode 0 y no mueve el nivel. Consecuencia directa sobre **Fase 2 (CORT hablando), 5 (ecualizador) y la función 15 (volumen)**: el código puede estar bien y no se oye nada. Hay que conectar algo por HDMI, unos auriculares Bluetooth, o llevar CORT a otro equipo para medirlo de verdad.
- Consecuencia: las fases **2 (voz)**, **3 (VRM)**, **6 (MediaPipe)** y la generación de vídeo van a ir muy justas o no van a ser viables aquí. Antes de comprometerlas hay que medir. Regla 10 de `AGENTS.md`: decirlo, no simularlo.
- Material de referencia **ya en disco** (no hace falta clonar): `~/Documentos/jarvis/` = adewaskar/JARVIS, **MIT**, con React+Three.js+GLSL, voz real (Porcupine, VAD, Kokoro) y `src/lib/hands.ts` con MediaPipe. Su `bridge/` va atado al SDK de Claude → no reutilizable tal cual. `~/Documentos/bases o proyectos git /OpenJarvis-main/` = **Apache-2.0**. `fullstack-agent-main.zip` = **AGPL-3.0 → no copiar código** (arrastraría a CORT a AGPL), solo leer ideas.

## El LLM medido: funciona, pero lento, y la primera medición estaba contaminada
Aviso sobre este documento: una versión anterior de esta sección decía "0,53 tokens/s, inviable". **Era una medición mal tomada** — estaba el navegador WebGL + Vite + el core + el agente peleando por la memoria, con el zram al 99 %. Números nuevos, en las condiciones que indica cada uno:

| condición | tiempo por turno |
|---|---|
| Modelo recién cargado (primer turno tras `ollama serve`) | **~3 min** |
| Modelo caliente, sólo Ollama + core + agente | **48–66 s** |
| Modelo caliente, sin nada más abierto | **11–15 s** |
| Evaluación del prompt (50 tokens), caliente | **0,9 s** (en frío: 113 s) |

Traducción: **la máquina real es de 2 núcleos a 1,46 GHz**, no sólo "1,8 GiB de RAM". Genera a ~1,3 tokens/s, así que un turno normal cuesta entre 15 y 60 s. Se puede usar, no es una conversación fluida.

Lo que sí se sacó en claro y ya está implementado en `brain.py`:
1. **`keep_alive=30m` en cada petición.** Es la diferencia entre 0,9 s y 113 s en el prompt: sin él Ollama descarga el modelo a los 5 minutos y cada conversación vuelve a pagarlo entero.
2. **Cadena de sustitución** `CORT_LLM_CHAIN`: habla el primero que responda; si uno se cae o se pasa de tiempo, sigue el siguiente.
3. **Guarda de memoria**: ningún modelo entra en la cadena si en disco pesa más de `CORT_LLM_MAX_MODEL_MIB` (700). Con los datos reales de esta máquina descarta `qwen3.5:2b` (2614 MiB) y `airaos-local` (718 MiB), y deja `qwen2.5:0.5b` (379) y `qwen3:0.6b` (498).
4. Timeout y "sin servidor" se reportan aparte. El `except` del bucle de la cadena se tragaba el `ConnectError` y lo llamaba "la cadena no respondió" — el mismo diagnóstico falso otra vez, ahora con test.

**El incidente:** mientras hacía estas mediciones dejé Ollama + navegador + Vite + el core a la vez y **el PC de Sandra se congeló; tuvo que apagar y encender**. No se perdió trabajo (estaba hecho `commit` + `push`), pero no se repite: una sola carga pesada cada vez, `free -m` antes de lanzar nada, y verificar con `httpx.MockTransport` en vez de encender modelos.

**Y un bug real que salió de medir, no de leer el código:** "¿qué sabes de mí?" no comparte ninguna raíz de 4 letras con "El usuario se llama Sandra", así que `recall()` devolvía vacío y el modelo contestaba —con razón— que no te conocía. Arreglado con `context_for()`, que si nada coincide mete los recuerdos más recientes (tope 6). Verificado antes/después en la máquina real: ahora responde "Sandra".

Consecuencia para el roadmap: la **ruta local** (intents + memoria + `WHO_AM_I`) sigue siendo lo que responde en menos de 0,6 s. El LLM ya vale, pero para conversación fluida hace falta otro equipo en la red (`CORT_OLLAMA_URL` ya lo permite).

## Transplante del holograma (hecho hoy)
Origen: `~/Documentos/jarvis/` = **adewaskar/JARVIS, licencia MIT** → copiable con atribución, que está en `apps/web/CREDITS.md`.
Destino: `apps/web/src/scene/{Core,Particles,Scene}.tsx`, `src/ui/Hud.tsx`, `src/cort/{palette,connection}.ts`, `src/index.css`.
Adaptaciones:
1. Paleta reescrita a **azul/violeta estilo Cortana** (`src/cort/palette.ts`), no el cian del original.
2. **Sin `zustand` ni `drei`**: el estado vive en un módulo propio con `useSyncExternalStore`. Menos dependencias, menos RAM.
3. El shader del anillo se copió **término a término**. Durante el copiado fundí `outer + wall + edge` en una sola variable y perdí el factor `(0.5 + uLevel*0.45)` del `mix` de color; se detectó y se revirtió.
4. La UI vieja (vanilla) no se borró: está en `apps/web/orbe-vanilla.html`.

Bug encontrado al verificar (no estaba en el original): `connect()` reprogramaba el reintento desde `onclose` incluso al cerrar a propósito, así que React StrictMode abría **dos** websockets y el log salía duplicado. Arreglado con comprobación de identidad (`if (sock !== s) return`) y verificado: el saludo aparece una sola vez.

## Segunda tanda del transplante: efectos de un solo disparo
Origen: `~/Documentos/jarvis/src/ui/Effects.tsx` + sus keyframes en `src/index.css` (**MIT**, atribución ampliada en `apps/web/CREDITS.md`).
Destino: `apps/web/src/ui/Effects.tsx`, `src/cort/connection.ts`, `src/index.css`, `src/App.tsx`, y el `send_json` de `server.py`.
Lo que cambió al adaptar:
1. En el original el efecto lo publica el puente de Claude en `zustand`; aquí lo publica el **core por WebSocket** con `{"type":"effect","kind":"pulse"}`, y viaja por la misma capa mutable que el color del anillo (`useSyncExternalStore`, sin store externo).
2. El cliente **valida `kind` contra su propia lista** y descarta lo que no conoce: un holograma que no sabe qué pintar no debe romperse, debe no pintar nada.
3. `--accent` se fija a mano en la capa `.fx`, porque cuelga **fuera** de `.hud` y no hereda su `--tint`. Sin eso la onda saldría de otro color que el anillo que la disparó.
4. Se dispara sólo cuando un `intent` se ejecuta, no en cada mensaje.

**`Orbits.tsx` se descartó a propósito.** Lo revisé antes de decidir: es una bandeja que hace orbitar **imágenes que JARVIS va capturando**, alimentada por `ui.orbits` del store y por un bridge HTTP que las lee desde disco. CORT no produce ninguna imagen todavía, así que su lista estaría siempre vacía: trasplantarlo hoy sería código muerto. Volverá cuando exista un productor (captura de pantalla, Fase 4).

**Interfaz táctil** — trabajo propio, no transplant: `@media (pointer: coarse)` con pulsaciones de 48 px, `font-size: 16px` en el campo (por debajo de eso el navegador móvil hace auto-zoom al enfocar), `env(safe-area-inset-bottom)` con `viewport-fit=cover` en el meta, y `enterKeyHint="send"`. **Sin verificar en un móvil real**: no se puede probar desde el navegador de esta máquina, y el core sigue atado a `127.0.0.1`.

**Y un aviso sobre cómo se descubrió el hilo de SQLite.** `test_protocol.py` falló con `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`: el store se construye al importar el módulo, en el hilo principal, y `TestClient` corre la app en un hilo de portal de anyio distinto. Se arregló con `check_same_thread=False`.

Ahora, **para ser exacto: ese fallo no se había manifestado con el servidor real.** `uvicorn.run(app, …)` en el `__main__` monta el bucle asíncrono en el mismo hilo que hizo el `import`, así que los websockets de `make dev` siempre usaban la conexión desde su propio hilo —y de hecho memoria y saludos funcionaron por WebSocket real antes del arreglo. Lo que la prueba destapó es una **fragilidad latente**, no una caída en curso: el día que alguien corra el core con un runner que sí separe hilos, o lo importe desde un hilo secundario, la primera escritura revienta. El mensaje de commit que acompañó al arreglo dice «el asistente nunca habría respondido»; **eso es una exageración mía**, y queda corregida aquí, que es donde se consulta el estado.

## Fase 4 empezada: la capa de permisos, y lo que reveló
`intents.py` decía «Entendido: volume» y **no tocaba el volumen**. Eso es justo lo que la regla 10 prohíbe, así que ahora hay `actions.py` (lista cerrada, argv fijo, `asyncio.create_subprocess_exec`, `CORT_SYSTEM_ACTIONS=0` para apagarla) y el core informa del resultado.

Medido con el core levantado y un websocket de verdad, no con simulacro:

```
>>> baja el volumen
    effect: glitch
    dijo: No pude: el mando obedeció pero el nivel sigue en 100 % (¿salida de audio en Dummy?).
>>> activa el ecualizador
    effect: glitch
    dijo: No pude: la acción «equalizer» no está en la lista permitida.
```

Tres cosas se supieron sólo por ejecutarlo:
1. **La tubería funciona.** Texto → intent → comando real → lectura del nivel → efecto + mensaje. Todo por el protocolo de siempre, sin tipos nuevos.
2. **El `returncode` mentía.** `wpctl set-volume` devuelve **0** sobre el sink *Dummy Output* sin cambiar nada. La primera versión del código reportaba «Volumen al 100 %» con el nivel intacto, y la prueba en vivo la desenmascaró. Ahora se lee antes y después, y si el número no se movió CORT lo dice. **El fallo de la primera versión era mío y lo encontró una ejecución, no una lectura del código.**
3. **Este portátil no tiene por dónde sacar audio** (ver Limitaciones). La función 15 queda 🔨: código hecho y verificado el comportamiento; efecto audible, imposible de verificar aquí.

## Deuda conocida
- **Ningún módulo carga `.env`.** La configuración se pasa con variables de entorno: `CORT_LLM_CHAIN=qwen3:0.6b make dev`. `.env.example` documenta las que existen de verdad.
- El README local sigue prometiendo un alcance que el código no tiene.
- `scripts/upstreams.txt` conserva URLs con `REEMPLAZAR`; ya se conocen las reales (ver arriba).
- **El móvil todavía no puede hablar con el core.** Vite escucha en la red (`http://192.168.100.171:5173`) pero el core se ató a `127.0.0.1` a propósito. Abrirlo a la red local es una decisión de seguridad consciente (cualquiera en tu WiFi podría controlar el PC), no un flag que se pone sin pensarlo.
- `node_modules/` de `apps/web` ocupa **144 MB**; `dist/` queda ignorado en git.
- **El rescate de `context_for` puede meter ruido.** Medido con 300 recuerdos de prueba: "¿qué sabes de mí?" se trae 5 "Preferencia NNN" que no vienen al caso, porque son simplemente los más recientes. Con la base real (2 hechos) no pasa; con cientos, sí. Es un cambio consciente: ruido en el prompt antes que prompt vacío, pero habría que afinarlo (p. ej. priorizar el nombre y las preferencias declaradas).
- **`history[-20:]` en `server.py`** manda hasta 20 turnos al prompt. Con ~1,3 tokens/s eso es tiempo de más; bajarlo es una línea, pero cambia cuánto recuerda CORT dentro de una misma conversación.
- **"Apareció un `hola` suelto en el log al cargar la página" — explicado, no reproducido.** Leyendo `connection.ts`: una entrada `from:'user'` sólo la añade `send()`, que sólo corre al enviar el formulario; ningún mensaje del servidor puede escribirla. O sea que era mi propia prueba anterior, conservada por el Fast Refresh de Vite (el estado del módulo `connection.ts` sobrevive a los cambios de componente; sólo una recarga real lo pondría a `msgs: []`). No lo doy por cerrado con una captura: **no lo volví a cargar en el navegador**, y no lo hice porque el zram está al **99 %** (915 de 925 MiB) y reiniciar Vite + core + navegador es exactamente la carga que congeló el PC. Queda por confirmar al arrancar la próxima sesión.

## Siguiente paso exacto
1. **Que alguien la oiga.** Antes de seguir con audio (Fase 2 voz, Fase 5 ecualizador, función 15 audible) hace falta una salida de audio real: auriculares Bluetooth, altavoces por HDMI, u otro equipo. Sin eso nada de sonido es verificable, y la regla 11 no permite darlo por hecho.
2. **Decisión de red** (es de Sandra, no de código): abrir el core a la LAN para probar la interfaz táctil en el Samsung A16, o dejarlo en `127.0.0.1` y conformarse con probar el CSS desde el modo móvil del navegador de escritorio. Abrirlo expone el control del PC a todo el WiFi.
3. **`Blades.tsx`** (MIT): paneles laterales del HUD. Es el transplant que más se acerca a lo que ella pidió y no depende de ningún puente.
4. **Más acciones en la lista cerrada**: brillo (`gsettings` sí está, `ddcutil` no) y captura de pantalla (función 47), que es además el productor que necesita `Orbits` para dejar de ser código muerto.
5. **`src/lib/hands.ts`** (gestos MediaPipe): medir antes de prometer — 2 núcleos, y MediaPipe en CPU es una carga del tamaño de Ollama.

## Registro de sesiones
| Fecha | Quién | Qué hizo |
|---|---|---|
| 2026-10-06 | Gemini/Claude web | Generó docs y estructura teórica. Describió carpetas (desktop, voz, sensores, STATUS) que nunca creó |
| 2026-10-07 | **Qoder** | `git init`, reparó Makefile, venv+deps, core verificado por WebSocket, creó STATUS.md, respaldó a GitHub como `cort-local-verified`, **transplantó la memoria SQLite y cerró la Fase 1** (25 pruebas OK) |
| 2026-10-07 | **Qoder** | **Transplantó el holograma** (MIT, adewaskar/JARVIS) a `apps/web` como React+Vite+Three con paleta Cortana; verificado con capturas del navegador a 18 fps; arregló el doble websocket de StrictMode y el diagnóstico falso de `brain.py`; midió el LLM y documentó que es inviable conversar con él en esta máquina |
| 2026-10-07 (tarde) | **Qoder** | Integró Ollama de verdad: cadena de sustitución, guarda de tamaño por RAM, `keep_alive`. Corrigió su propia medición anterior (estaba contaminada) y encontró que **"¿qué sabes de mí?" no inyectaba contexto** — arreglado con `context_for`, verificado antes/después. 38 pruebas. **Dejó que la máquina se congelara al medir; ella tuvo que apagarla. Regla nueva: una carga pesada cada vez.** |
| 2026-10-07 (noche) | **Qoder** | Cerró la **FASE 1.1**: `prune()` protege el nombre siempre, conectada al arranque del core, criterio del roadmap medido (1-4 ms con 300 recuerdos). 42 pruebas. Todo verificado sin tocar Ollama. |
| 2026-10-07 (madrugada) | **Qoder** | Trasplantó **`Effects.tsx`** (MIT) y le conectó el mensaje `effect` del core: pulso verificado en el navegador con `MutationObserver` y `--accent` saliéndose de la misma paleta que el anillo. Añadió la **capa táctil** (sin probar en móvil, dicho está). Escribió `test_protocol.py` (46 pruebas) y **descartó `Orbits.tsx` con motivo**: sin productor de imágenes sería código muerto. Corrigió su propio comentario del bug de SQLite: era una **fragilidad latente**, no una caída real, y el mensaje de commit lo había exagerado. **No arrancó nada pesado más**: el zram está al 99 % y la máquina ya se congeló una vez por hacer justo eso. |
| 2026-10-07 (madrugada II) | **Qoder** | **Empezó la Fase 4** con `actions.py`: capa de permisos de lista cerrada, argv fijo, kill switch, y el nivel leído antes y después. Levantó el core y le habló por WebSocket de verdad — y **así descubrió que su primera versión mentía**: `wpctl` devuelve 0 sobre *Dummy Output* sin mover el volumen. Y lo de *Dummy* no es un detalle: **este portátil sólo saca audio por HDMI, y el puerto está `not available`**, así que Fase 2 (voz), Fase 5 (ecualizador) y la función 15 audible no se pueden verificar aquí con nada. 67 pruebas. Todo lo de audio queda 🔨 con la limitación escrita, no simulada. |
