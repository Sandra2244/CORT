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
| 15 | Volumen del sistema | ⬜ | M (por SO) |
| 16 | Ecualizador del sistema | ⬜ | D (Windows: Equalizer APO; Android: solo dentro de tu propio reproductor) |
| 17 | Normalizar decibeles de lo que se reproduce | ⬜ | D (en tu reproductor: fácil; global: depende del SO) |
| 18 | Control de reproductor (play/pausa/siguiente) | ⬜ | M (MPRIS/Windows media keys/Android MediaSession) |
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
| 31 | HUD (hora, clima, estado del sistema) | 🔨 | F — hecho: conexión, atuendo y chat. Falta: reloj, clima real (hoy `CORT_CITY_TEMP_C` es un `TODO`), estado del sistema |
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
| 46 | Brillo de pantalla | ⬜ | M |
| 47 | Captura de pantalla | ⬜ | F |
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
