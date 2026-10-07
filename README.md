# CORT — Cognitive Operating Reactive Technology

Asistente personal local-first inspirado en Cortana (Halo): avatar holográfico, voz, control de PC/teléfono y automatización. Todo lo "surreal" del lore se traduce a algo **real y posible**.

> Estado: **MVP 0.1** — chat por WebSocket + cerebro (Ollama o modo eco) + orbe holográfico + selector de atuendo por hora/temperatura.

## Arranque rápido
```bash
make setup      # crea venv e instala dependencias
make dev        # core en :8765  (y abre apps/web/index.html o `make web`)
make test       # pruebas de lógica pura
```
Opcional: instala [Ollama](https://ollama.com) y `ollama pull qwen2.5:3b` para respuestas reales. Sin Ollama, CORT responde en modo eco (para probar la UI).

## Documentación
| Documento | Para qué |
|---|---|
| [docs/VISION.md](docs/VISION.md) | Qué es CORT y qué se traduce de Cortana a la realidad |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Capas, lenguajes y protocolo |
| [docs/UPSTREAMS.md](docs/UPSTREAMS.md) | Qué tomar de OpenJarvis / OpenClaw / adewaskar-JARVIS |
| [docs/FUNCTIONS.md](docs/FUNCTIONS.md) | 60+ funciones con estado y viabilidad |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Fases pequeñas, cada una funciona sola |
| [docs/DEVELOPMENT-GUIDE.md](docs/DEVELOPMENT-GUIDE.md) | **Empieza aquí**: método de trabajo, herramienta elegida, prompts |
| [docs/AI-COPILOT-GUIDE.md](docs/AI-COPILOT-GUIDE.md) | Qué copiloto usar sin quedarte sin cuota |
| [AGENTS.md](AGENTS.md) | Instrucciones que cualquier agente de código debe leer |
