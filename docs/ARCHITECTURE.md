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
```
Los tipos nuevos se añaden aquí primero y luego al código.

## Módulos de `services/core/cort_core`
- `brain.py` — habla con Ollama; si no está disponible, modo eco.
- `intents.py` — comandos locales rápidos ("sube el volumen") sin gastar LLM.
- `outfit.py` — atuendo según hora y temperatura.
- `server.py` — FastAPI + WebSocket.
