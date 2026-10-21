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
| Móvil | **Java puro sin Gradle** (`aapt2` + `javac` + `d8` + `zipalign` + `apksigner`) embebiendo la misma `ui/`: **un solo APK**, `CORT-IA-2.1.0.apk`, con su reproductor en primer plano y su marcador. La vía de rempaquetar el binario de Kotlin está fuera del repo | Un `gradle build` congeló el portátil de 1,8 GB (medido); en Actions no pasa, y ahí se compila. Dos APK que había que elegir eran doble trabajo y doble publicación |
| Pantallas | `ui/js/pantallas.js`: hojas a pantalla completa (Orbe · Música · **MV** · Charla · Código) que se cambian con ☰, deslizando, `Alt+←/→` o por voz, y apagan el WebGL cuando no les toca — en **MV** el orbe no se apaga: se encoge a una esquina girando como disco | La dueña pidió interfaces separadas que **no toquen ni obstruyan** el orbe, como las apps multiventana, y un visionado estilo Lark Player con la letra sincronizada |
| Letras de canciones | **LRCLIB** (`/api/letras`, sin clave) con marcas `[mm:ss.xx]`, cacheo en memoria de 40 canciones, `timeout` y `reintenta` si el servidor está saturado | Es gratis y no pide registro; el plan de «letra sincronizada» no depende de que ella tenga una API key |
| Orden de archivos | `backend/app/organiza.py`: **plan primero, hechos después**, con token de 15 minutos y sin primitiva de borrado | La promesa que se le hizo: «no me pierdes nada». Un `mv` a ciegas en sus Documentos sería irreparable |
| Modo juego | `CortNative.modoJuego(bool)` con su `volatile` y sus `silenciar`/`soltarSesion`: cierra el micro, no pide foco audio, calla el auricular | Los juegos (Call of Duty Mobile) se le cerraban y la música desaparecía. **Sin** `PACKAGE_USAGE_STATS`: la dueña rechazó ese permiso, así que es interruptor, no detección |
| Auto-actualización | `backend/app/actualiza.py` + `scripts/actualiza.sh`: compara con la Release, respalda la instalación anterior, instala sin sudo y no toca `~/.cort` | «que CORT revise si hay actualizaciones en tu repositorio y se autorepare para eso es la terminal» |
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
  `CORT-IA-2.1.0.apk`, y lo compila GitHub Actions con `compilar.sh` (Java puro sin
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
- **F7e — La ronda «todo en uno» (la 2.0.0)**, pedida tal cual por la dueña: la hoja
  **MV** con **letra sincronizada** de LRCLIB y el orbe hecho disco en una esquina, el
  **modo juego** («modo juego» / «vuelve CORT»: cierra el micro, no pide el foco audio
  y deja de susurrar por el auricular, **sin** permiso de uso de aplicaciones), el
  **organizador de archivos** con plan y confirmación (`backend/app/organiza.py`, sin
  una sola primitiva de borrado), la **auto-actualización por voz** contra GitHub
  (`backend/app/actualiza.py` + `scripts/actualiza.sh`, con respaldo y sin sudo), y la
  **llave de firma definitiva** ya como secreto del repo (`CORT_APK_KEYSTORE_B64` /
  `CORT_APK_KEYSTORE_PASS`) para que actualizar sea instalar encima.
- **F7f — La ronda 2.1: «todo lo prometido dentro del APK».** Nueve clases Java
  nuevas (`Acciones`, `VozNueva`, `Recuerdos`+`Sincroniza`, `Mente`+`Nube`+`Cerebro`,
  `Paleta`, `Agenda`, `Flotante`, `ArchivosProvider`) que exponen **ocho funciones** en
  el puente —`accion`, `ajusteVoz`, `memoria`, `mente`, `atuendo`, `agenda`, `burbuja`
  y `comparte`— con su contrato escrito en `docs/CONTRATO-PUENTE-2.1.md` (es la única
  fuente de los nombres). Del lado de la cara, la hoja **Equipo** con **seis bloques**
  (Voz · Mando · Cerebro · Memoria · Atuendos · Agenda) y doce grupos de frases de voz.
  Lo que añade de fondo: **pensar sin el portátil** (la nube que la dueña ajusta desde
  la pantalla, con la clave sin salir del teléfono, y 35 patrones de
  `assets/habilidades.json` que además **ejecutan** la orden que reconocen), memoria en
  SQLite del teléfono cuadradable con `~/.cort` por `/api/memories` y `/api/profile`,
  la **burbuja** flotante (`SYSTEM_ALERT_WINDOW`, que en modo juego nunca aparece), la
  **linterna** por `setTorchMode`, las **citas** de `CalendarContract.Instances` con
  `READ_CALENDAR` de sólo lectura (y `apunta` abriendo el formulario del sistema:
  `WRITE_CALENDAR` no está pedido a propósito), el correo contado desde la barra de
  avisos, y **enviar un archivo tuyo a otra app** por `ArchivosProvider` (sin él,
  Android corta el `Uri` con `FileUriExposedException`). Tres permisos nuevos que la
  dueña da a mano: cámara, calendario y aparecer encima. Se comprueba sin teléfono en
  los **nueve sectores** de `scripts/prueba-costura.py`, y en el sector [9] cada
  función se mira en los **cuatro** sitios donde vive: su clase, el puente, la cara y
  el manifiesto o el backend.

## 5. Riesgos honestos

1. **1,8 GB de RAM**: Electron + navegador + MediaPipe a la vez es justo. Mitigación: cerrar todo lo demás al probar; MediaPipe solo activo cuando hay gesto.
2. **Transparencia en Linux** depende del compositor (en Wayland a veces falla) — probaremos temprano en F2.
3. **Vosk/Whisper locales** pesan: empezamos con Web Speech API (coste cero).
4. El orb del video es de alguien más: recrearemos el *estilo* (partículas azules + anillos + estrellas) con nuestra propia escena Three.js, no copiando el archivo.
5. **El teléfono de verdad no está en esta máquina.** Ninguna ronda del APK se ha
   probado con un dedo encima: lo que garantía hay es que `javac` del runner revisa
   las firmas de la plataforma, que `aapt2` enlaza el manifiesto, que `apksigner`
   valida la firma y que `scripts/prueba-costura.py` comprueba que las tres capas se
   nombran igual. Quedan sin probar en un aparato real: la burbuja con
   `SYSTEM_ALERT_WINDOW` en cada fabricante, el `<video>` del MV sobre su `content://`,
   el cuadro de `RoleManager` en los lanzadores modificados y el `ACTION_INSERT` del
   calendario. El primer fallo que salga en el teléfono se corregirá hacia adelante
   (etiqueta nueva), nunca moviendo la publicada.

## 6. Decisión pendiente única

Confirmar el nombre final del wake word y si el cerebro online será Groq (más rápido) o Gemini (más generoso en cuota gratis). Recomendación: **Groq + Llama 3.3 8B gratis**, con Gemini de respaldo.
