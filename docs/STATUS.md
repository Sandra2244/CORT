# STATUS — estado real del proyecto

> **Este archivo es la fuente de verdad operativa.** Cualquier agente (Qoder, OpenCode, Claude, DeepSeek)
> lee `AGENTS.md` + este archivo y continúa desde aquí. No se confía en chats anteriores.
> Última verificación: **2026-10-07**, ejecutando comandos, no recordándolos.

## Fase actual
**Transplante del holograma (UI) — cerrado y verificado en el navegador hoy.** → Siguiente: **FASE 1.1 (poda de memoria)**, o decidir qué se hace con el LLM, que hoy es inviable en esta máquina (ver "El LLM medido").

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
| **25 pruebas** | `make test` → `Ran 25 tests ... OK` |
| WebSocket completo | saludo, `state` con atuendo, modo eco en ~0.3 s, intents sin LLM |
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
- **1,8 GiB de RAM, ~340 MiB libres, sin GPU.** Ningún modelo de Ollama mediano cabe. Hay 9,2 GB descargados en `~/.ollama` con 4 modelos (`qwen2.5:0.5b`, `qwen3:0.6b`, `qwen3.5:2b`, `airaos-local`) y **4 blobs `-partial`** = descargas interrumpidas.
- El server de Ollama **no arranca solo**; hay que lanzar `ollama serve`. CORT funciona sin él (modo eco).
- Consecuencia: las fases **2 (voz)**, **3 (VRM)**, **6 (MediaPipe)** y la generación de vídeo van a ir muy justas o no van a ser viables aquí. Antes de comprometerlas hay que medir. Regla 10 de `AGENTS.md`: decirlo, no simularlo.
- Material de referencia **ya en disco** (no hace falta clonar): `~/Documentos/jarvis/` = adewaskar/JARVIS, **MIT**, con React+Three.js+GLSL, voz real (Porcupine, VAD, Kokoro) y `src/lib/hands.ts` con MediaPipe. Su `bridge/` va atado al SDK de Claude → no reutilizable tal cual. `~/Documentos/bases o proyectos git /OpenJarvis-main/` = **Apache-2.0**. `fullstack-agent-main.zip` = **AGPL-3.0 → no copiar código** (arrastraría a CORT a AGPL), solo leer ideas.

## El LLM medido: inviable como conversación en esta máquina
No es una impresión, son tres peticiones cronometradas contra `qwen2.5:0.5b` con el servidor ya caliente:

| prompt | tokens de salida | tiempo |
|---|---|---|
| 32 | 11 | 145 s |
| 40 (24 cacheados) | 36 | 93 s |
| ~60 con contexto de memoria | — | >180 s, agotó el timeout |

**~0,53 tokens/s reales, sin GPU.** La segunda petición descarta el *thrashing*: el modelo ya estaba cargado. Con estos números una respuesta normal tarda dos minutos, y encima `qwen2.5:0.5b` contestó tonterías ("CORT es un término de la medicina… clavícula").

Arreglado en `brain.py`: el `except Exception` de antes convertía "el modelo va lento" en "Ollama no responde", que es un diagnóstico falso. Ahora el timeout es configurable (`CORT_LLM_TIMEOUT_S`, 180 s) y el tiempo agotado se reporta aparte. Verificado llamando a `think()` de verdad.

Consecuencia para el roadmap: lo que responde en <0,6 s y ya funciona es la **ruta local** (intents + memoria + `WHO_AM_I`). El LLM es opcional aquí; para usarlo en condiciones hace falta otro equipo en la red (`CORT_OLLAMA_URL` ya lo permite) o conformarse con esa latencia. Regla 10: esto es un no-se-puede, no un "ya casi".

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
- **Ningún módulo carga `.env`.** La configuración se pasa con variables de entorno: `CORT_MODEL=qwen3:0.6b make dev`.
- El README local sigue prometiendo un alcance que el código no tiene.
- `scripts/upstreams.txt` conserva URLs con `REEMPLAZAR`; ya se conocen las reales (ver arriba).
- **El móvil todavía no puede hablar con el core.** Vite escucha en la red (`http://192.168.100.171:5173`) pero el core se ató a `127.0.0.1` a propósito. Abrirlo a la red local es una decisión de seguridad consciente (cualquiera en tu WiFi podría controlar el PC), no un flag que se pone sin pensarlo.
- `node_modules/` de `apps/web` ocupa **144 MB**; `dist/` queda ignorado en git.

## Siguiente paso exacto
**FASE 1.1 — poda de memoria** (corta y segura en esta máquina):
1. `MemoryStore.prune(max_rows=…)` y un test que meta 300 recuerdos y compruebe que `recall` sigue devolviendo lo relevante.
2. Política: **borrar los más antiguos**. Descartado "resumirlos con el LLM" tras medir los 0,53 tok/s de arriba — un resumen costaría minutos.

Después de eso, lo que queda del holograma pedido:
- **`Orbits.tsx`** y los gesto-hands (`src/lib/hands.ts`) del repo MIT, que aún no se han traído.
- **Interfaz táctil** para el Samsung A16: la UI actual es de ratón (input de texto + botón). Botones grandes y gestos es trabajo propio, no un transplant.

## Registro de sesiones
| Fecha | Quién | Qué hizo |
|---|---|---|
| 2026-10-06 | Gemini/Claude web | Generó docs y estructura teórica. Describió carpetas (desktop, voz, sensores, STATUS) que nunca creó |
| 2026-10-07 | **Qoder** | `git init`, reparó Makefile, venv+deps, core verificado por WebSocket, creó STATUS.md, respaldó a GitHub como `cort-local-verified`, **transplantó la memoria SQLite y cerró la Fase 1** (25 pruebas OK) |
| 2026-10-07 | **Qoder** | **Transplantó el holograma** (MIT, adewaskar/JARVIS) a `apps/web` como React+Vite+Three con paleta Cortana; verificado con capturas del navegador a 18 fps; arregló el doble websocket de StrictMode y el diagnóstico falso de `brain.py`; midió el LLM y documentó que es inviable conversar con él en esta máquina |
