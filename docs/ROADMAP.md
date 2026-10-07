# Roadmap

Cada fase termina con algo que corre y una prueba. No avances si la anterior no funciona.

| Fase | Entrega | Criterio de "listo" |
|---|---|---|
| 0 ✅ | Repo, docs, core + UI orbe | `make test` pasa; el chat responde (modo eco o Ollama) |
| 1 | Memoria persistente (SQLite) | CORT recuerda tu nombre tras reiniciar |
| 2 | Voz: Whisper + Piper + wake word | Dices "Hey CORT" y responde hablando |
| 3 | Avatar VRM + shader holográfico + lip-sync | Un VRM habla con la boca sincronizada |
| 4 | Control de PC: volumen, reproductor, apps | "Sube el volumen" cambia el volumen real |
| 5 | Audio: ecualizador y normalizador en tu reproductor | Se aplica a una pista local |
| 6 | Gestos con MediaPipe | Mano levantada despierta a CORT |
| 7 | Sensores ESP32 + MQTT | La temperatura real cambia el atuendo |
| 8 | Móvil (PWA → Capacitor) | CORT abre en tu Android conectado al core |
| 9 | Pulido: overlay, atuendos, README con vídeo | Demo de 60 s para TikTok |
