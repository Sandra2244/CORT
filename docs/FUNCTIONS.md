# Funciones de CORT

Estado: ✅ hecho · 🔨 siguiente · ⬜ pendiente. Viabilidad: **F** fácil · **M** media · **D** difícil / depende del sistema.

## Núcleo
| # | Función | Est. | Viab. |
|---|---|---|---|
| 1 | Chat con LLM local (Ollama) | ✅ | M — funciona con cadena de sustitución y guarda de memoria. Lento: 15–60 s por turno, ~3 min el primero. Ver STATUS.md |
| 2 | Memoria de conversación (sesión) | ✅ | F |
| 3 | Memoria persistente (SQLite: hechos del usuario, raíces de 4 letras, poda con el nombre protegido, y **rescate para el prompt ordenado por contenido** —nombre y hechos declarados antes que «lo más reciente», medido con 303 recuerdos en 2,42 ms—) | ✅ | M |
| 4 | Comandos locales rápidos (intents) | ✅ | F |
| 5 | Búsqueda web | ⬜ | F |
| 6 | Resumen de documentos | ⬜ | F |
| 7 | Recordatorios y tareas | ⬜ | F |
| 8 | Traducción | ⬜ | F |
| 9 | Clima | ✅ | F — Open-Meteo, **sin clave de API** (`cort_core/weather.py`). `CORT_CITY` en el `.env` lo activa; vacío = no sale ni un paquete de la máquina. El nombre se resuelve con el geocoder **una sola vez** y las coordenadas quedan en caché; refresco cada 15 min (`CORT_WEATHER_TTL_S`) en una tarea aparte, nunca dentro del bucle del WebSocket. Un 500 devuelve la última foto y deja de afirmarla pasados tres TTL. 9 pruebas con `httpx.MockTransport` y una medición real: `Bogotá → 17,7 °C, código 3` |
| 10 | Generación/explicación de código | ⬜ | F |
| 65 | Configuración por `.env` (sin exportar nada a mano) | ✅ | F — `cort_core/env.py`: un **único parser** que leen el core y el lanzador (por ruta de archivo, sin `import`), para que no puedan discrepar en qué puerto están. Una variable ya exportada gana; `CORT_DOTENV=0` anula el archivo entero, que es como `make test` se asegura de no leer la base de datos de nadie. `make setup` crea el `.env` desde el ejemplo. 14 pruebas |

## Voz y audio
| # | Función | Est. | Viab. |
|---|---|---|---|
| 11 | Wake word ("Hey CORT") | ⬜ | M |
| 12 | Voz a texto (Whisper local) | ⬜ | M |
| 13 | Texto a voz (Piper / Kokoro) | ⬜ | M |
| 14 | Interrumpir mientras habla (barge-in) | ⬜ | M |
| 15 | Volumen del sistema | 🔨 | M (por SO) — **el código está y corre**: `wpctl set-volume` por la capa de permisos, con el nivel leído antes y después. Verificado de extremo a extremo por WebSocket. **Sin comprobar el efecto audible**: el único chip de audio de este portátil es HDMI (`Intel Valleyview2 HDMI`), su perfil está en `off` y el puerto reporta *not available*, así que el sink por defecto es *Dummy Output* y PipeWire acepta la orden con returncode 0 sin mover nada. CORT lo dice («sigue en 100 %, ¿salida en Dummy?») en vez de mentir. En un PC con altavoces reales es una línea de configuración, no de código |
| 16 | Ecualizador del sistema | ⬜ | D (Windows: Equalizer APO; Android: solo dentro de tu propio reproductor). Hoy `intents.py` lo reconoce y `actions.py` **lo rechaza por escrito** con `glitch`: no está en la lista cerrada |
| 17 | Normalizar decibeles de lo que se reproduce | ⬜ | D (en tu reproductor: fácil; global: depende del SO) |
| 18 | Control de reproductor (play/pausa/siguiente) | 🔨 | M — tecla `XF86Audio*` con `xdotool`, en la lista cerrada y probada por argv. **Sin verificar en un reproductor de verdad**: no hay ninguno sonando en esta máquina (ver 15), y una tecla XF86 la escucha quien esté reproduciendo, no CORT |
| 19 | Control de audífonos Bluetooth (conectar/desconectar, batería) | ⬜ | M |
| 20 | Reconocer canción | ⬜ | M (requiere servicio externo) |
| 21 | Detección de emoción en la voz | ⬜ | D |
| 22 | Cambio de voz/personaje | ⬜ | M |
| 63 | Sonda de audio en el arranque (diagnosticar si hay a dónde hablar y de dónde escuchar) | ✅ | F — `audio_probe()` en `scripts/cort.py` lee `wpctl status`, recorta **sólo la sección `Audio`** y pinta la quinta barra. Medido hoy en esta máquina: `0 salida(s): ninguna real (Dummy Output) · 0 entrada(s) — sin esto no hay voz que verificar`. El recorte es el punto: en `Video → Sources` hay dos cámaras, y leer el texto entero diría que hay micrófono. 9 pruebas en `test_launcher.py`. **En Windows y macOS la sonda es otra y aquí no se ha escrito: sin `wpctl` la barra se calla en vez de mentir** |

## Avatar
| # | Función | Est. | Viab. |
|---|---|---|---|
| 23 | Orbe/partículas holográficas reactivas | ✅ | F — reactor GLSL de anillo erosionado + 4000 puntos, paleta Cortana, reacciona a `thinking` y a atuendo. **Y cambia de tamaño desde la interfaz** (función 64). 18 fps sin GPU |
| 24 | Atuendo por hora y temperatura (lógica) | ✅ | F |
| 25 | Cargar modelo VRM (three-vrm) | ⬜ | M |
| 26 | Cambiar atuendo en el VRM | ⬜ | M |
| 27 | Lip-sync con el audio | ⬜ | M |
| 28 | Parpadeo y mirada | ⬜ | M |
| 29 | Expresiones según estado afectivo | ⬜ | M |
| 30 | Shader holográfico (scanlines, fresnel) | 🔨 | M — hecho: bloom, aberración cromática, ruido, viñeta y scanlines CSS. Falta: fresnel sobre malla (nada de esto tiene geometría que iluminar todavía) |
| 31 | HUD (hora, clima, estado del sistema) | ✅ | F — hecho: conexión, atuendo, chat, **estado del sistema** (`Telemetry.tsx`, visto en el navegador: recuerdos sobre el techo, modelo que contestó la última vez, capa de permisos encendida o apagada), **reloj** en el cabezal (`Clock()` en `Hud.tsx`, medido en el navegador: `00:25:04 → 00:25:07` en 2,1 s; es un temporizador propio alineado al segundo, no un fotograma más del bucle de Three.js) y **clima real** (función 9) en la misma línea. El clima se pinta sólo si el core lo midió: sin `CORT_CITY` la línea queda como estaba, en vez de un `0°` inventado |
| 32 | Burbuja flotante siempre visible (overlay transparente) | ⬜ | M (Electron en PC; Android requiere permiso de superposición) |
| 61 | Efectos de un solo disparo en el holograma (`glitch · pulse · scan · shake · flash`) | ✅ | F — transplantado de `Effects.tsx` (MIT), atribuido en `apps/web/CREDITS.md`. El core emite `{"type":"effect","kind":"pulse"}` al ejecutar un intent. Verificado en el navegador con `MutationObserver`: onda de 0,9 s con el color del atuendo. Hoy **sólo lo dispara un intent**; ningún error lo usa todavía |
| 62 | App instalable en el móvil (PWA) | 🔨 | F. **Escrito y servido**: `apps/web/public/manifest.webmanifest` (nombre, `display: standalone`, `theme_color` `#02040c`, tres iconos) + iconos generados con código propio (anillo del mismo color que `palette.ts`, sin arte de terceros) + `<link rel="manifest">` en `index.html`. **Verificado sirviendo `dist`**: `GET /manifest.webmanifest → 200 application/manifest+json`, el JSON parsea y `list_console_messages` no tiene ni un aviso de manifiesto. **Sin service worker, dicho en vez de simulado**: lo único que puede contestar es el core en `:8765`, y cachar una interfaz que depende de él sirve para abrir un CORT mentiroso. **Falta lo que no puede comprobarse desde aquí**: el botón «Añadir a pantalla de inicio» en el Samsung A16, que exige que el lanzador escuche en la LAN (función 66, ya escrita) e HTTPS — Chrome sólo instala PWA por `localhost` o TLS |
| 64 | Tamaño del reactor ajustable por la usuaria (50 % – 200 %) | ✅ | F — slider y botones ± en el cabezal del HUD (`ZoomControl` en `Hud.tsx`, 44 px de diana para el pulgar). Mueve `target.zoom`, el objeto mutable de la escena, **no estado de React**: `Scene.tsx` lo persigue con `lerp` por frame, así que el orbe crece en vez de saltar, y arrastrar el control no reconcilia el registro de mensajes. Probado en el navegador con la interfaz servida: 100 % → 200 % → 100 %, y **18 fps en los tres casos** — el coste es el postproceso rasterizado sin GPU, no el tamaño |
| 66 | Abrir CORT desde el teléfono (`--lan`) | ✅ | F — sexta barra del lanzador. Por defecto todo sigue en `127.0.0.1`: el core no tiene contraseña ni TLS, así que publicarlo es decisión de quien arranca. Con `--lan` se abren a la vez core e interfaz, y la terminal imprime la IP que hay que escribir (la sonda usa un socket UDP de salida, no envía paquetes: si no hay red dice «sin IP de red» en vez de inventarse una). **Medido en esta red**: `0.0.0.0:8765` y `0.0.0.0:8780` escuchando, `200` desde la IP de red y un WebSocket por esa IP que saludó y respondió. **Sin verificar en un móvil físico** |
| 67 | CORT como aplicación nativa (Windows / macOS / Android) | ⬜ | M — la pila ya es la misma en todos los sistemas (core Python + interfaz web), pero empaquetarla en un binario es Electron o Capacitor, y ambos están medidos y descartados para **esta** máquina en `docs/PLATFORM.md`: 263 MB libres frente a los ~120 MB de un Chromium extra. En un PC de 8 GiB la decisión cambia; aquí no |

## Gestos y visión
| # | Función | Est. | Viab. |
|---|---|---|---|
| 33 | Detectar mano/gestos con cámara (MediaPipe) | ⬜ | M |
| 34 | Detectar rostro/presencia | ⬜ | F |
| 35 | Mirada del usuario | ⬜ | D |
| 36 | Describir lo que ve la cámara (modelo de visión) | ⬜ | M |
| 37-44 | Arrastrar, rotar, escalar, pellizcar, deslizar, tocar, doble toque, inclinar | ⬜ | F (táctil/ratón); inclinar = acelerómetro. **Base táctil ya escrita** (pulsaciones de 48 px, `font-size:16px` contra el auto-zoom, `viewport-fit=cover` + `env(safe-area-inset-bottom)`, `enterKeyHint="send"`): eso hace que se *pueda* tocar, no que los gestos existan. Ninguno de esos selectores se ha ejecutado en un móvil real |

## Control de dispositivos
| # | Función | Est. | Viab. |
|---|---|---|---|
| 45 | Abrir/cerrar aplicaciones | 🔨 | F. **Abrir, verificado de extremo a extremo**: "abre la terminal" por WebSocket → `intent: launch` → `effect: pulse` → *«Abriendo la terminal.»*, y `pgrep -c -x xfce4-terminal` pasó de 0 a 1. Repetido con el gestor de archivos (`thunar`, 0→1), y a la segunda vez CORT dice «ya estaba en marcha» en vez de atribuirse un proceso que no creó. **Dos apps de una tabla cerrada**, no "cualquier cosa": el argv no lleva texto del usuario. **Cerrar** sigue ⬜ —matar procesos por nombre es la clase de mando que borra de más si la lista se ensancha— |
| 46 | Brillo de pantalla | ⬜ | **D en Linux sin root**, medido hoy: `/sys/class/backlight/intel_backlight/brightness` es `root:root 644` sin ACL de sesión, y `brightnessctl`/`xbacklight` no están instalados. Volver a escribir el valor que ya tenía devolvió *Permiso denegado*. Se puede con una regla de udev o con `sudo` — decisión de ella, no de código—; mientras tanto no se escribe un mando que no va a obedecer |
| 47 | Captura de pantalla | ✅ | F. **Verificado de extremo a extremo**: "haz una captura de pantalla" por WebSocket → `scrot` → PNG real de 140 265 bytes (1366×768) en disco, y CORT dice el archivo y su tamaño. Como con el volumen, se comprueba el archivo *después* de mandarlo: el `returncode` no basta |
| 48 | Reproducir vídeo cuadro por cuadro (en tu reproductor) | ⬜ | M |
| 49 | Leer notificaciones | ⬜ | D (Android: permiso especial) |
| 50 | Enviar SMS / llamar | ⬜ | D (Android; iOS no lo permite) |
| 51 | Modo "no molestar" por contexto | ⬜ | M |

## Sensores y contexto
| # | Función | Est. | Viab. |
|---|---|---|---|
| 52 | Temperatura (API o sensor ESP32) | ⬜ | F |
| 53 | Luz ambiente | ⬜ | M |
| 54 | Ruido ambiente (dB) | ⬜ | F |
| 55 | Ubicación | ⬜ | F |
| 56 | Estado de red/Bluetooth | ⬜ | F |
| 57 | MQTT con ESP32/RPi | ⬜ | M |
| 58 | Sugerencias por rutina ("son las 7, ¿café?") | ⬜ | M |
| 59 | Aprender preferencias | ⬜ | M |
| 60 | Agentes en paralelo ("fragmentos") | ⬜ | M |
