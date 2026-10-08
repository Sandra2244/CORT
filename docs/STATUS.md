# STATUS — estado real del proyecto

> **Este archivo es la fuente de verdad operativa.** Cualquier agente (Qoder, OpenCode, Claude, DeepSeek)
> lee `AGENTS.md` + este archivo y continúa desde aquí. No se confía en chats anteriores.
> Última verificación: **2026-10-07**, ejecutando comandos, no recordándolos.

## Fase actual
**FASE 1.1 (poda de memoria) cerrada, y Ollama respondiendo de verdad.** → Siguiente: `Orbits.tsx` + gestos del repo MIT, e **interfaz táctil** para el móvil. La **Fase 2 (voz)** y la **3 (VRM)** siguen pendientes de una decisión de hardware, no de código: 2 núcleos a 1,46 GHz.

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
| **42 pruebas** | `make test` → `Ran 42 tests ... OK` (tarda ~46 s: la poda mete 300 recuerdos de verdad) |
| **Poda de memoria (Fase 1.1)** | 302 recuerdos → `prune(keep=200)` deja 201, y `context_for` responde en **1-4 ms** (criterio del roadmap: <1 s). Conectada al arranque del core. Verificado: tras arrancar con la poda, el saludo sigue siendo "Hola de nuevo, Sandra." |
| WebSocket completo | saludo, `state` con atuendo, modo eco en ~0.3 s, intents sin LLM |
| **Chat con Ollama (función 1)** | Por WebSocket real contra el core: "¿qué sabes de mí hasta ahora?" → **"Sandra, …"**. La memoria llega al modelo. Lento: 48–66 s por turno con el modelo caliente |
| **Guarda de memoria del LLM** | Con el Ollama de verdad: detecta los 4 modelos instalados y descarta `qwen3.5:2b` (2614 MiB) y `airaos-local` (718) por no caber. 10 pruebas con `httpx.MockTransport`, sin encender modelos |
| **Memoria persistente (Fase 1)** | Proceso 1: "me llamo Sandra" → guarda `El usuario se llama Sandra`. Se mata el proceso. Proceso 2: saluda **"Hola de nuevo, Sandra."** y "¿cómo me llamo?" → **"Te llamas Sandra."** sin pasar por el LLM |
| **Interfaz holográfica (React+Three)** | Capturas de pantalla reales a `localhost:5173`: anillo azul/violeta Cortana, polvo de 4000 puntos, bloom. **18 fps sin GPU.** `make web-build` → `✓ built`. Enviar "me llamo Sandra y estudio ingeniería" por la UI escribió `El usuario estudia ingeniería` en SQLite |
| Reacción a estados | Con `thinking=true` el anillo pasó a magenta y la cabecera a "CORT procesando"; al terminar volvió a azul |

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

## Deuda conocida
- **Ningún módulo carga `.env`.** La configuración se pasa con variables de entorno: `CORT_LLM_CHAIN=qwen3:0.6b make dev`. `.env.example` documenta las que existen de verdad.
- El README local sigue prometiendo un alcance que el código no tiene.
- `scripts/upstreams.txt` conserva URLs con `REEMPLAZAR`; ya se conocen las reales (ver arriba).
- **El móvil todavía no puede hablar con el core.** Vite escucha en la red (`http://192.168.100.171:5173`) pero el core se ató a `127.0.0.1` a propósito. Abrirlo a la red local es una decisión de seguridad consciente (cualquiera en tu WiFi podría controlar el PC), no un flag que se pone sin pensarlo.
- `node_modules/` de `apps/web` ocupa **144 MB**; `dist/` queda ignorado en git.
- **El rescate de `context_for` puede meter ruido.** Medido con 300 recuerdos de prueba: "¿qué sabes de mí?" se trae 5 "Preferencia NNN" que no vienen al caso, porque son simplemente los más recientes. Con la base real (2 hechos) no pasa; con cientos, sí. Es un cambio consciente: ruido en el prompt antes que prompt vacío, pero habría que afinarlo (p. ej. priorizar el nombre y las preferencias declaradas).
- **`history[-20:]` en `server.py`** manda hasta 20 turnos al prompt. Con ~1,3 tokens/s eso es tiempo de más; bajarlo es una línea, pero cambia cuánto recuerda CORT dentro de una misma conversación.

## Siguiente paso exacto
Fase 1.1 cerrada. Lo que queda del holograma pedido:
- **`Orbits.tsx`** y los gesto-hands (`src/lib/hands.ts`) del repo MIT, que aún no se han traído.
- **Interfaz táctil** para el Samsung A16: la UI actual es de ratón (input de texto + botón). Botones grandes y gestos es trabajo propio, no un transplant.

## Registro de sesiones
| Fecha | Quién | Qué hizo |
|---|---|---|
| 2026-10-06 | Gemini/Claude web | Generó docs y estructura teórica. Describió carpetas (desktop, voz, sensores, STATUS) que nunca creó |
| 2026-10-07 | **Qoder** | `git init`, reparó Makefile, venv+deps, core verificado por WebSocket, creó STATUS.md, respaldó a GitHub como `cort-local-verified`, **transplantó la memoria SQLite y cerró la Fase 1** (25 pruebas OK) |
| 2026-10-07 | **Qoder** | **Transplantó el holograma** (MIT, adewaskar/JARVIS) a `apps/web` como React+Vite+Three con paleta Cortana; verificado con capturas del navegador a 18 fps; arregló el doble websocket de StrictMode y el diagnóstico falso de `brain.py`; midió el LLM y documentó que es inviable conversar con él en esta máquina |
| 2026-10-07 (tarde) | **Qoder** | Integró Ollama de verdad: cadena de sustitución, guarda de tamaño por RAM, `keep_alive`. Corrigió su propia medición anterior (estaba contaminada) y encontró que **"¿qué sabes de mí?" no inyectaba contexto** — arreglado con `context_for`, verificado antes/después. 38 pruebas. **Dejó que la máquina se congelara al medir; ella tuvo que apagarla. Regla nueva: una carga pesada cada vez.** |
| 2026-10-07 (noche) | **Qoder** | Cerró la **FASE 1.1**: `prune()` protege el nombre siempre, conectada al arranque del core, criterio del roadmap medido (1-4 ms con 300 recuerdos). 42 pruebas. Todo verificado sin tocar Ollama. |
