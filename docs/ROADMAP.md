# Roadmap

Cada fase termina con algo que corre y una prueba. No avances si la anterior no funciona.

| Fase | Entrega | Criterio de "listo" |
|---|---|---|
| 0 ✅ | Repo, docs, core + UI orbe | `make test` pasa; el chat responde (modo eco o Ollama) |
| 1 ✅ | Memoria persistente (SQLite) | Cerrado 2026-10-07: matar el proceso y levantarlo; CORT saluda "Hola de nuevo, Sandra" y responde "¿cómo me llamo?" sin LLM |
| 1.1 ✅ | Poda de la memoria (que no crezca sin límite) | Cerrado 2026-10-07: con 302 recuerdos, `prune(keep=200)` deja 201 y `context_for` responde en **1-4 ms** (techo: 1 s). La **poda por resumen con el LLM se descarta**: medido a ~1,3 tokens/s, resumir costaría minutos. El nombre del usuario nunca se poda |
| 2 ⚠️ | Voz: Whisper + Piper + wake word | Dices "Hey CORT" y responde hablando. **Revisar viabilidad: la máquina tiene 1,8 GiB de RAM y sin GPU** |
| 3 | Avatar VRM + shader holográfico + lip-sync | Un VRM habla con la boca sincronizada |
| 4 🔨 | Control de PC: volumen, reproductor, apps | "Sube el volumen" cambia el volumen real. **Empezado con capa de permisos** (`actions.py`: lista cerrada, argv fijo, `CORT_SYSTEM_ACTIONS=0`) y verificado por WebSocket contra el core. **El criterio no puede cerrarse en este portátil**: su único chip de audio es HDMI, el puerto está `not available` y el sink es *Dummy Output*, que acepta la orden con returncode 0 sin mover el nivel — CORT ya lo detecta y lo dice, hace falta un altavoz real encima para cerrar la fase |
| 5 | Audio: ecualizador y normalizador en tu reproductor | Se aplica a una pista local |
| 6 | Gestos con MediaPipe | Mano levantada despierta a CORT |
| 7 | Sensores ESP32 + MQTT | La temperatura real cambia el atuendo |
| 8 🔨 | Móvil (PWA → Capacitor) | CORT abre en tu Android conectado al core. **Empezado por la única parte que no cuesta RAM: la capa táctil** (48 px, `font-size:16px`, `safe-area`, `enterKeyHint`) — sin verificar en un móvil real. **Está bloqueada por una decisión, no por código**: el core escucha en `127.0.0.1` a propósito, y abrirlo a la LAN expone el control del PC a todo el WiFi |
| 9 | Pulido: overlay, atuendos, README con vídeo | Demo de 60 s para TikTok |
