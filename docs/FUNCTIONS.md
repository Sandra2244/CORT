# Funciones de CORT

Estado: ✅ hecho · 🔨 siguiente · ⬜ pendiente. Viabilidad: **F** fácil · **M** media · **D** difícil / depende del sistema.

## Núcleo
| # | Función | Est. | Viab. |
|---|---|---|---|
| 1 | Chat con LLM local (Ollama) | ✅ | M — funciona con cadena de sustitución y guarda de memoria. Lento: 15–60 s por turno, ~3 min el primero. Ver STATUS.md |
| 2 | Memoria de conversación (sesión) | ✅ | F |
| 3 | Memoria persistente (SQLite: hechos del usuario, raíces de 4 letras, poda con el nombre protegido) | ✅ | M |
| 4 | Comandos locales rápidos (intents) | ✅ | F |
| 5 | Búsqueda web | ⬜ | F |
| 6 | Resumen de documentos | ⬜ | F |
| 7 | Recordatorios y tareas | ⬜ | F |
| 8 | Traducción | ⬜ | F |
| 9 | Clima | ⬜ | F |
| 10 | Generación/explicación de código | ⬜ | F |

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

## Avatar
| # | Función | Est. | Viab. |
|---|---|---|---|
| 23 | Orbe/partículas holográficas reactivas | ✅ | F — reactor GLSL de anillo erosionado + 4000 puntos, paleta Cortana, reacciona a `thinking` y a atuendo. 18 fps sin GPU |
| 24 | Atuendo por hora y temperatura (lógica) | ✅ | F |
| 25 | Cargar modelo VRM (three-vrm) | ⬜ | M |
| 26 | Cambiar atuendo en el VRM | ⬜ | M |
| 27 | Lip-sync con el audio | ⬜ | M |
| 28 | Parpadeo y mirada | ⬜ | M |
| 29 | Expresiones según estado afectivo | ⬜ | M |
| 30 | Shader holográfico (scanlines, fresnel) | 🔨 | M — hecho: bloom, aberración cromática, ruido, viñeta y scanlines CSS. Falta: fresnel sobre malla (nada de esto tiene geometría que iluminar todavía) |
| 31 | HUD (hora, clima, estado del sistema) | 🔨 | F — hecho: conexión, atuendo, chat y **estado del sistema** (`Telemetry.tsx`, visto en el navegador): recuerdos sobre el techo, modelo que contestó la última vez y si la capa de permisos está encendida. Falta: reloj y clima real (hoy `CORT_CITY_TEMP_C` es un `TODO`) |
| 32 | Burbuja flotante siempre visible (overlay transparente) | ⬜ | M (Electron en PC; Android requiere permiso de superposición) |
| 61 | Efectos de un solo disparo en el holograma (`glitch · pulse · scan · shake · flash`) | ✅ | F — transplantado de `Effects.tsx` (MIT), atribuido en `apps/web/CREDITS.md`. El core emite `{"type":"effect","kind":"pulse"}` al ejecutar un intent. Verificado en el navegador con `MutationObserver`: onda de 0,9 s con el color del atuendo. Hoy **sólo lo dispara un intent**; ningún error lo usa todavía |

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
| 45 | Abrir/cerrar aplicaciones | ⬜ | M |
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
