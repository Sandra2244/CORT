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
                 │ apps/web (y desktop)│  JS/TS · Canvas/Three.js
                 │ avatar · HUD · chat │
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
{"type":"state","outfit":"casual","mood":"calm","thinking":false}
{"type":"intent","action":"volume","delta":10}
```
Los tipos nuevos se añaden aquí primero y luego al código.
(`intent` ya se emitía desde `server.py` pero no estaba documentado: se añade aquí en cumplimiento de la regla 5 de `AGENTS.md`.)

## Módulos de `services/core/cort_core`
- `brain.py` — habla con Ollama; si no está disponible, modo eco.
- `intents.py` — comandos locales rápidos ("sube el volumen") sin gastar LLM.
- `memory/store.py` — SQLite persistente en `services/core/data/memory.db` (fuera de git: son datos personales). `remember`, `recall`, `name_of_user`, `all`.
- `memory/facts.py` — convierte frases del usuario ("me llamo X", "estudio Y") en hechos almacenables.
- `outfit.py` — atuendo según hora y temperatura.
- `server.py` — FastAPI + WebSocket. Por cada mensaje: guarda los hechos detectados, y si el texto pregunta por la identidad del usuario responde desde la memoria (sin LLM); si no, inyecta los recuerdos relevantes como mensaje de sistema antes de llamar a `brain.think`.

La memoria es SQLite con búsqueda por raíces de 4 letras, no embeddings: `sentence-transformers` + `faiss` (como en la rama remota `scaffold`) piden ~1,5 GiB de RAM y el equipo de desarrollo tiene 1,8 GiB en total. Cambiar esto es un cambio de arquitectura que se documenta aquí antes de programarse.
