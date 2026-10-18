# C.O.R.T. — Cognitive Orchestrator / Real-Time

Asistente personal holográfico inspirado en JARVIS (Iron Man) y Cortana (Halo).
Cerebro **híbrido**: funciona con IA local (Ollama), IA online gratuita (Groq/Gemini),
o ambos a la vez, eligiendo automáticamente la mejor ruta según el equipo.
Multiplataforma: Linux, Windows y (fase final) Android vía APK.

## Arquitectura

```
┌───────────── Interfaz (ui/index.html → Electron en F6) ─────────────
│  Three.js: orb de partículas + anillos   Paneles HUD · chat · reloj │
│  Web Speech API: micrófono y voz (gratis, sin instalar nada)        │
└───────────────┬──────────────────────────────────────────────────────┘
                │ HTTP localhost:8000
┌───────────────┴───────────────┐
│  Backend Python (FastAPI)     │
│  brain.py — enrutador híbrido:│
│   1. comando local instantáneo│  hora, fecha, batería, CPU… (sin internet)
│   2. Ollama local             │  equipos 8 GB+ RAM
│   3. Groq → Gemini online     │  capa gratuita, sin tarjeta
│   4. modo supervivencia       │  siempre responde algo útil
│  memory.py — SQLite persistente
└───────────────────────────────┘
```

## Instalación (3 pasos)

1. **Requisitos**: Python 3.10+ y un navegador Chrome/Edge (para voz y micrófono).
2. **Arrancar**:
   - Linux: `bash scripts/run.sh`
   - Windows: doble clic en `scripts\run.bat`
3. **Abrir el holograma**: `cort/ui/index.html` en Chrome/Edge.

### Opcional — activar la IA conversacional

- **Online (recomendado, gratis):** crea `backend/.env` (copia de `.env.example`) y
  pega tu `GROQ_API_KEY` de <https://console.groq.com/keys> o `GEMINI_API_KEY` de
  <https://aistudio.google.com/apikey>. Reinicia el backend.
- **Local (equipos potentes):** instala [Ollama](https://ollama.com), ejecuta
  `ollama pull qwen2.5:3b` y CORT lo detecta solo.
- `CORT_MODE` en `.env` fuerza la ruta: `auto` (por defecto), `local`, `online`, `offline`.

## Estructura

| Ruta | Qué es |
|------|--------|
| `backend/app/main.py` | API FastAPI (`/api/chat`, `/api/status`, `/api/history`, `/api/profile`) |
| `backend/app/brain.py` | Cerebro híbrido y enrutador |
| `backend/app/local_commands.py` | Comandos instantáneos sin IA |
| `backend/app/memory.py` | Memoria persistente SQLite |
| `ui/index.html` | Holograma: orb Three.js + HUD + voz |
| `scripts/run.sh` / `run.bat` | Arranque en Linux / Windows |

## Estado del proyecto (hoja de ruta F0–F7)

- [x] F1 Backend híbrido + memoria + comandos locales — **probado en Linux**
- [x] F2 Orb Three.js + chat + reloj + micrófono — **probado en navegador**
- [ ] F3 Paneles HUD (archivos, clima, sensores animados)
- [ ] F4 Gestos con MediaPipe (palma abre, pinza agarra)
- [ ] F5 Wake word "Oye CORT" + Piper TTS + perfil personalizable
- [ ] F6 Electron transparente + instaladores .exe / .AppImage
- [ ] F7 APK Android con Capacitor

Todo el software usado es gratuito. Ningún puerto se expone a internet: backend y
Ollama solo escuchan en `localhost`.
