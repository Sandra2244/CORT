# STATUS — estado real del proyecto

> **Este archivo es la fuente de verdad operativa.** Cualquier agente (Qoder, OpenCode, Claude, DeepSeek)
> lee `AGENTS.md` + este archivo y continúa desde aquí. No se confía en chats anteriores.
> Última verificación: **2026-10-07**, hecha ejecutando comandos, no recordándolos.

## Fase actual
**FASE 0 — cerrada y verificada hoy.** → Siguiente: **FASE 1 (memoria persistente con SQLite)**.

## Qué existe y está verificado funcionando
| Cosa | Evidencia |
|---|---|
| `services/core/cort_core/{server,brain,intents,outfit}.py` | `python -m py_compile` OK |
| 8 pruebas de lógica pura | `make test` → `Ran 8 tests ... OK` |
| Core arrancando | `make dev` → escucha en `127.0.0.1:8765`, `/docs` devuelve 200 |
| Habla por WebSocket | Cliente real: saludo + `state` con atuendo, respuesta en modo eco en ~0.3 s |
| Intents locales | "sube el volumen" → `{"type":"intent","action":"volume","delta":10}` sin pasar por el LLM |
| UI del orbe | `apps/web/index.html`: partículas, scanlines, se reconecta solo, respeta `prefers-reduced-motion` |
| Repo git | `git init` hecho, commit inicial `1c46dc5`. **Sin remoto todavía.** |

## Qué NO existe (aunque otros documentos y chats lo daban por hecho)
- `apps/desktop/` — nada de Electron, ventana transparente ni overlay.
- `services/voice/`, `services/vision/`, `services/audio/`, `services/sensors/` — no existen.
- `packages/` (shared, protocol, ui-components) — no existe.
- `scripts/context-pack.py` — no existe; el método de relevo entre IAs no tenía herramienta.
- `upstream/` está **vacío**: `scripts/upstreams.txt` aún tiene URLs con `REEMPLAZAR`.
- `LICENSE` — no hay, pese a que el README del repo GitHub habla de MIT.

## Correcciones hechas en esta sesión
1. **`Makefile` inservible en Linux**: usaba `python` (no existe en Debian) → `setup`, `dev`, `test` y `web` fallaban con `Error 127`. Ahora usa la ruta absoluta del interprete del venv.
2. **Dependencias nunca instaladas**: no había `.venv`. Creado e instalado (fastapi 0.142.3, uvicorn 0.54.0, httpx 0.28.1).
3. **Modelo fantasma**: `.env.example` y `brain.py` pedían `qwen2.5:3b`, que no está descargado. Cambiado a `qwen2.5:0.5b`, que sí existe en `~/.ollama`.
4. **`.env` no lo lee nadie**: ningún módulo carga el archivo. Mientras no se arregle, la configuración se pasa con variables de entorno (`CORT_MODEL=... make dev`). Apuntado como deuda, no arreglado a propósito para no añadir dependencias sin discutir.

## Limitaciones reales de esta máquina (importan para planificar)
- **RAM: 1,8 GiB total, ~340 MiB disponibles. Sin GPU.** Ollama tiene 9,2 GB descargados con 4 modelos
  (`qwen2.5:0.5b`, `qwen3:0.6b`, `qwen3.5:2b`, `airaos-local`) y **4 blobs `-partial`** = descargas cortadas a medias.
  Con esta RAM, los modelos medianos no van a caber: el trabajo local serio tiene que ser con 0.5b/0.6b, o delegando en una API.
- Las fases de avatar VRM, MediaPipe y generación de vídeo son **muy exigentes** para este hardware.
  No son imposibles, pero hay que probarlas antes de comprometerlas en el roadmap.

## Material de referencia YA en disco (no hace falta clonar)
| Ruta | Qué es | Licencia |
|---|---|---|
| `~/Documentos/jarvis/` | **adewaskar/JARVIS** completo: React+Vite+Three.js+GLSL (el holograma), voz (Porcupine wake word, VAD, Kokoro TTS), `lib/hands.ts` con MediaPipe. Su `bridge/` va atado al SDK de Claude → no reutilizable tal cual | **MIT** (copiable con atribución) |
| `~/Documentos/bases o proyectos git /OpenJarvis-main/` | Cerebro, memoria, agentes, ejemplos (ojo: la carpeta tiene un espacio al final del nombre) | **Apache-2.0** |
| `~/Documentos/Referencias AIRA/fullstack-agent-main.zip` | jaredrhod (memoria/visualizador/gestos) | **AGPL-3.0 → NO copiar código**: arrastraría a CORT a AGPL. Solo leer ideas |

Existencia comprobada por API de GitHub: `adewaskar/jarvis`, `jaredrhod/{fullstack-agent,ai-visualizer,ai-memory-vault,barehands}`, `open-jarvis/OpenJarvis`, `openclaw/openclaw`.

## Siguiente paso exacto
**FASE 1 — memoria persistente (SQLite), con pruebas primero:**
1. Crear `services/core/cort_core/memory/store.py` con `add/get` y tabla `memories`.
2. Crear `services/core/tests/test_memory.py`: *al reiniciar el proceso, CORT recuerda el nombre del usuario.*
3. `make test` en verde → actualizar `docs/FUNCTIONS.md` (función 3: 🔨 → ✅) y `docs/ROADMAP.md`.
4. Commit: `feat(memory): store SQLite persistente con pruebas`.

Después, para tener cerebro real: arrancar `ollama serve` y probar con `qwen2.5:0.5b` (con 340 MiB libres irá lento; es una prueba, no una producción).

## Registro de sesiones
| Fecha | Quién | Qué hizo |
|---|---|---|
| 2026-10-06 | Gemini/Claude web | Generó docs y estructura teórica. Describió carpetas (desktop, voz, sensores, STATUS) que nunca creó |
| 2026-10-07 | **Qoder** | `git init` + commit de seguridad, reparó Makefile, creó venv, instaló dependencias, verificó core end-to-end por WebSocket, corrigió el modelo fantasma, escribió este STATUS |
