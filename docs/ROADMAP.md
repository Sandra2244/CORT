# Roadmap

Cada fase termina con algo que corre y una prueba. No avances si la anterior no funciona.

| Fase | Entrega | Criterio de "listo" |
|---|---|---|
| 0 ✅ | Repo, docs, core + UI orbe | `make test` pasa; el chat responde (modo eco o Ollama) |
| 1 ✅ | Memoria persistente (SQLite) | Cerrado 2026-10-07: matar el proceso y levantarlo; CORT saluda "Hola de nuevo, Sandra" y responde "¿cómo me llamo?" sin LLM |
| 1.1 ⬜ | Resumen y poda de la memoria (que no crezca sin límite) | 300 recuerdos siguen respondiendo en menos de 1 s |
| 2 ⚠️ | Voz: Whisper + Piper + wake word | Dices "Hey CORT" y responde hablando. **Revisar viabilidad: la máquina tiene 1,8 GiB de RAM y sin GPU** |
| 3 | Avatar VRM + shader holográfico + lip-sync | Un VRM habla con la boca sincronizada |
| 4 | Control de PC: volumen, reproductor, apps | "Sube el volumen" cambia el volumen real |
| 5 | Audio: ecualizador y normalizador en tu reproductor | Se aplica a una pista local |
| 6 | Gestos con MediaPipe | Mano levantada despierta a CORT |
| 7 | Sensores ESP32 + MQTT | La temperatura real cambia el atuendo |
| 8 | Móvil (PWA → Capacitor) | CORT abre en tu Android conectado al core |
| 9 | Pulido: overlay, atuendos, README con vídeo | Demo de 60 s para TikTok |
