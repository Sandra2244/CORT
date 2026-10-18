# Proyecto C.O.R.T. — Plan de Arquitectura v1
*(Cognitive Orchestrator / Real-Time — asistente holográfico inspirado en JARVIS e Cortana)*
Fecha: 2026-10-17 · Referencia visual: orb de partículas azul que se dispersa en anillos de estrellas

---

## 1. Qué revelan los 7 videos de referencia

| # | Duración | Qué se ve | Qué robamos de ahí |
|---|----------|-----------|--------------------|
| v1 | 0:16 | Persona mueve paneles holográficos en el aire frente al monitor con las manos | Control por gestos con cámara + ventana HUD a pantalla completa |
| v2 | 5:11 | Tutorial francés de instalación de "JARVIS v1.0" (techanelair.fr) | **La arquitectura real**: Python + Flask backend, `.env` con claves Gemini/Groq/OpenAI/SerpAPI/YouTube, TTS en mp3 pregenerados, wake word, `INSTALLATION.bat` |
| v3 | 3:31 | **El orb azul** con anillos y estrellas, HUD sobre escritorio Windows, gestos de mano abren paneles de archivos y chat | El estilo visual objetivo: Three.js (orbe de partículas) + paneles translúcidos + terminal |
| v4 | 3:18 | "Iron Man Jarvis interface": listas HUD verdes, atrapar archivos con pinza de dedos | Interacción pinza-agarrar (MediaPipe) y paneles arrastrables |
| v5 | 3:12 | Instalador GUI del mismo JARVIS francés: idioma, perfil, pasiones, claves API, guía de comandos de voz (hora, batería, CPU, clima, Spotify, YouTube, comandos locales sin internet) | Menú de configuración + lista de comandos de voz a implementar (local vs online) |
| v6 | 2:13 | Otro orb (púrpura/azul) con mano abierta → se abren ventanas de archivos, reloj digital HUD | Animación de dispersión del orb al "hablar", reloj y barras de estado |
| v7 | 0:45 | Setup de un agente estilo JARVIS con Claude Code y system prompt | El "system prompt" de personalidad de CORT + logo de anillos concéntricos |

**Conclusión**: todos los proyectos "profesionales" de estos videos usan la misma receta de 4 capas:
`Voz (wake word + STT) → Cerebro (API online gratuita) → Interfaz HUD (web: Three.js/CSS) → Manos (MediaPipe)`, con memoria local en archivos/SQLite. Ninguno corre un modelo grande localmente.

## 2. Stack elegido (Linux + Windows, PC de 2 núcleos / 1,8 GB)

| Capa | Herramienta (gratuita) | Por qué |
|------|------------------------|---------|
| Interfaz | **React + Vite + Three.js + Arwes** (framework sci-fi UI) + GSAP | El orb y los anillos son partículas Three.js; Arwes da paneles/bordes/sonidos sci-fi ya hechos; todo corre en el navegador de Electron |
| Ventana | **Electron** con `transparent: true, frame: false, alwaysOnTop` | Ventana holográfica transparente sobre el escritorio, igual que los videos; funciona en Linux y Windows |
| Cerebro online | **Groq** y/o **Gemini API** (capa gratuita, sin tarjeta) | Responder inteligente y rápido; el PC de Sandra NO puede correr Ollama (lo confirma la guía PDF, que lo marca como opcional para equipos potentes) |
| Cerebro local (opcional) | Frases locales en Python para "hora, batería, CPU, abrir apps" | Los videos llaman a esto "comandos instantáneos sin internet" |
| Oído | **Web Speech API** (navegador, gratis, sin instalar nada) → mejora futura: **Vosk** modelo español pequeño (~40 MB, corre en CPU) | STT sin servidor |
| Voz | **Piper TTS** (voce español neural, ligera, local) o `gtts` online | Suena natural, no robótica como pyttsx3 |
| Manos | **MediaPipe Hands** (JavaScript, corre en CPU del navegador) | Detección de 21 puntos de la mano: abrir palma = desplegar, pinza = agarrar archivo |
| Memoria | SQLite + JSON local | Persistente entre sesiones |
| Sensores | `psutil` (Python): batería, CPU, RAM, red; API Open-Meteo para clima | Los paneles de estado del v3/v6 |
| Móvil | **Capacitor** al final → APK Android | La misma interfaz web empaquetada |

## 3. Arquitectura

```
┌─────────────── Electron (ventana holográfica transparente) ───────────────┐
│  React + Three.js: ORB (partículas) · paneles HUD · chat · reloj · sensores│
│  MediaPipe Hands (cámara)          Web Speech (micrófono)                  │
└───────────────┬────────────────────────────────────────────────────────────┘
                │ WebSocket / HTTP localhost
┌───────────────┴───────────────┐
│  Backend Python (FastAPI)     │
│  · router de comandos         │
│  · locales: hora, batería,    │
│    clima, abrir apps, música  │
│  · online: Groq/Gemini API    │
│  · memoria SQLite             │
│  · TTS Piper                  │
└───────────────────────────────┘
```

## 4. Fases (cada una termina en algo que funciona y se ve)

- **F0 — Entorno** (ya empezado): Python venv, Node LTS, Git, ffmpeg instalado en `.venv-video`.
- **F1 — Cerebro con voz**: backend FastAPI + clave gratuita Groq/Gemini + hablar/escribir → CORT responde por audio. *Sin interfaz bonita todavía.*
- **F2 — Primera cara**: Electron transparente a pantalla completa con el **orb Three.js** (partículas + anillos, dispersión al "escuchar", pulso al "hablar") y panel de chat.
- **F3 — Paneles HUD**: reloj, clima, batería/CPU, ventanas de archivos estilo Arwes, animaciones de entrada/salida.
- **F4 — Manos**: MediaPipe — palma abierta despliega paneles, pinza agarra/suelta archivos, puño = dormir.
- **F5 — Automaata**: wake word ("Oye CORT"), memoria persistente, comandos de sistema, perfil personalizable (como el instalador del v5).
- **F6 — Empaquetar**: `electron-builder` → instalador .exe (Windows) y .AppImage/.deb (Linux).
- **F7 — APK**: Capacitor lleva la interfaz a Android (el orb y gestos funcionan; el backend se conecta por red local).

## 5. Riesgos honestos

1. **1,8 GB de RAM**: Electron + navegador + MediaPipe a la vez es justo. Mitigación: cerrar todo lo demás al probar; MediaPipe solo activo cuando hay gesto.
2. **Transparencia en Linux** depende del compositor (en Wayland a veces falla) — probaremos temprano en F2.
3. **Vosk/Whisper locales** pesan: empezamos con Web Speech API (coste cero).
4. El orb del video es de alguien más: recrearemos el *estilo* (partículas azules + anillos + estrellas) con nuestra propia escena Three.js, no copiando el archivo.

## 6. Decisión pendiente única

Confirmar el nombre final del wake word y si el cerebro online será Groq (más rápido) o Gemini (más generoso en cuota gratis). Recomendación: **Groq + Llama 3.3 8B gratis**, con Gemini de respaldo.
