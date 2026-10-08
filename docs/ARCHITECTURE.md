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
{"type":"state","outfit":"casual","mood":"calm","thinking":false}
{"type":"intent","action":"volume","delta":10}
```
Los tipos nuevos se añaden aquí primero y luego al código.
(`intent` ya se emitía desde `server.py` pero no estaba documentado: se añade aquí en cumplimiento de la regla 5 de `AGENTS.md`.)

## Módulos de `services/core/cort_core`
- `brain.py` — habla con Ollama a través de una **cadena de sustitución** (`CORT_LLM_CHAIN`): prueba los modelos en orden y usa el primero que responda. Antes de intentarlo pide `/api/tags` y **descarta por tamaño** lo que no cabe en RAM (`CORT_LLM_MAX_MODEL_MIB`, 700 MiB) — cargar `qwen3.5:2b` en esta máquina la congeló. Manda `keep_alive=30m` en cada petición: sin él Ollama descarga el modelo y la siguiente conversación paga 113 s de carga. Timeout en `CORT_LLM_TIMEOUT_S`. Distingue "Ollama no está" de "la cadena no respondió": confundirlos hace depurar un servidor caído que no existe. Si nada funciona, modo eco.
- `intents.py` — comandos locales rápidos ("sube el volumen") sin gastar LLM.
- `memory/store.py` — SQLite persistente en `services/core/data/memory.db` (fuera de git: son datos personales). `remember`, `recall`, `context_for`, `prune`, `name_of_user`, `all`. `context_for` es el que arma el prompt: si la pregunta no comparte raíces con ningún recuerdo, devuelve los más recientes en vez de nada, porque un prompt sin contexto hace que el modelo niegue que te conoce. `prune` se llama al arrancar el core y **nunca borra la fila del nombre**, que es de la que dependen el saludo y "¿cómo me llamo?".
- `memory/facts.py` — convierte frases del usuario ("me llamo X", "estudio Y") en hechos almacenables.
- `outfit.py` — atuendo según hora y temperatura.
- `server.py` — FastAPI + WebSocket. Por cada mensaje: guarda los hechos detectados, y si el texto pregunta por la identidad del usuario responde desde la memoria (sin LLM); si no, inyecta los recuerdos relevantes como mensaje de sistema antes de llamar a `brain.think`.

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
- `ui/Hud.tsx` — estado, registro de mensajes y entrada de texto.

El reactor mide **18 fps sin GPU** en el equipo de desarrollo. Cualquier añadido (más partículas, un segundo paso de blur, un avatar VRM) se nota en ese número.
