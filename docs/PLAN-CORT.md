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
| Móvil | **Java puro sin Gradle** (`aapt2` + `javac` + `d8` + `zipalign` + `apksigner`) embebiendo la misma `ui/`: **un solo APK**, `CORT-IA-2.0.0.apk`, con su reproductor en primer plano y su marcador. La vía de rempaquetar el binario de Kotlin está fuera del repo | Un `gradle build` congeló el portátil de 1,8 GB (medido); en Actions no pasa, y ahí se compila. Dos APK que había que elegir eran doble trabajo y doble publicación |
| Pantallas | `ui/js/pantallas.js`: hojas a pantalla completa (Orbe · Música · Charla · Código) que se cambian con ☰, deslizando, `Alt+←/→` o por voz, y apagan el WebGL cuando no les toca | La dueña pidió interfaces separadas que **no toquen ni obstruyan** el orbe, como las apps multiventana |
| Lectura en voz alta | PC: SQLite + `sensors.leer_texto`. Teléfono: `NotificationListenerService` en RAM | No hay API de WhatsApp: la barra de notificaciones es lo que la dueña ya ve, y no deja rastro en disco |

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
- **F7 — APK**: ya no Capacitor y **ya no dos APK**: sale uno solo de `apps/apk/`,
  `CORT-IA-2.0.0.apk`, y lo compila GitHub Actions con `compilar.sh` (Java puro sin
  Gradle: `aapt2` + `javac` + `d8` + `zipalign` + `apksigner`). Es el que puede ser el
  asistente predeterminado (rol pedido con `RoleManager`, y `res/xml/asistente.xml`
  **sin** `settingsActivity`, que es lo que lo borraba de la lista), escucha el doble
  toque del auricular, lee los avisos, y trae dentro su **propio reproductor**
  (`Reproductor.java`, un servicio en primer plano con `mediaPlayback`: gustos,
  playlists y cuadro a cuadro en vídeo, sin trabar el teléfono) y el marcador de
  contactos (`Telefono.java`). El icono es el anillo de siempre: se saca de
  `base/CORT-IA-1.1.0.apk`. La vía `rempaquetar.sh` —el cuerpo de Kotlin con sólo la
  cara cambiada— está borrada del repo y del workflow: dos APK que había que elegir
  era trabajo doble. Viaja en la Release con su `-firma.txt`.
- **F7b — Te lo lee en voz alta** (lo que hace una SIRI): «lee mis notas», «lee mis
  tareas», «lee el documento recibo» y «lee mis avisos». Notas y pendientes viven en
  SQLite (`memory.py`), los documentos se leen por la lista blanca de raíces seguras
  (`sensors.leer_texto`, solo texto plano y tope de 400 KB), y los avisos del teléfono
  los aporta un `NotificationListenerService` (`Avisos.java`) que mantiene doce líneas
  en RAM y nunca escribe disco. Se comprueba sin teléfono con
  `scripts/prueba-lectura.py` (las frases y sus respuestas) y
  `scripts/prueba-costura.py` (manifiesto ↔ Java ↔ cara).
- **F7c — Que se pueda usar de verdad** (lo que dijo el dedo encima del teléfono):
  el anillo del teléfono como logo de los instaladores
  (`scripts/icono-del-telefonito.sh` + `scripts/empaqueta-ico.py`); `/api/optimize`
  que contesta al instante y cuenta la caché del disco en un hilo aparte; las
  descargas de Ollama **en cola**, con MB y MB/s reales y su `✕ cancelar`
  (`POST /api/models/cancel`); CORT **dentro de la lista de asistentes** — fuera la
  `settingsActivity` que hacía descartar el contrato por no ser app del sistema,
  dentro el rol `RoleManager.ROLE_ASSISTANT`—; y el **freno del oído**, que cierra
  el micro al ir a segundo plano (`pause`/`resume` entre Java y la cara), con música
  sonando, con la pantalla apagada y mientras se cuenta la caché.
- **F7d — Pantallas aparte del orbe** (`ui/js/pantallas.js` + su CSS en `ui/css/hud.css`):
  hoja a pantalla completa con barra ☰, cambio deslizando el dedo de lado, con
  `Alt+←/→`/`Alt+1…4` o por voz («abre el chat», «pantalla de código», «vuelve al
  orbe»). **Charla** (burbujas, modelos de Ollama con `/api/models` y
  `/api/models/use`, copiar y guardar en Notas), **Código** (terminal contra
  `/api/command` + cuaderno en `localStorage`) y **Música** sólo en el teléfono, que
  manda al `Reproductor` y pinta su barra con el evento `music` del puente, sin
  martillearlo. No tapan el orbe: cuando no es su pantalla el lienzo WebGL se
  congela (`orb.pausa()` en `ui/js/orb.js`) y el HUD se apaga por CSS anclado a la
  clase `pantallas-montadas`, así que si el módulo fallara al montarse la interfaz
  de siempre queda intacta en vez de negra. Se comprueba en
  `scripts/prueba-costura.py` apartado [6] (28 métodos del puente usados desde la
  cara, todos existentes; y las cinco rutas del núcleo, todas reales).

## 5. Riesgos honestos

1. **1,8 GB de RAM**: Electron + navegador + MediaPipe a la vez es justo. Mitigación: cerrar todo lo demás al probar; MediaPipe solo activo cuando hay gesto.
2. **Transparencia en Linux** depende del compositor (en Wayland a veces falla) — probaremos temprano en F2.
3. **Vosk/Whisper locales** pesan: empezamos con Web Speech API (coste cero).
4. El orb del video es de alguien más: recrearemos el *estilo* (partículas azules + anillos + estrellas) con nuestra propia escena Three.js, no copiando el archivo.

## 6. Decisión pendiente única

Confirmar el nombre final del wake word y si el cerebro online será Groq (más rápido) o Gemini (más generoso en cuota gratis). Recomendación: **Groq + Llama 3.3 8B gratis**, con Gemini de respaldo.
