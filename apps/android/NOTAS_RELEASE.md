# CORT {{VERSION}} — asistente Android, cerebro híbrido y acciones confirmadas

**Autora:** Askher Vargas y Sandra Lopez · soporte: `Sandrasofialopezgomez3@gmail.com` · `Carlosa3325@gmail.com` · **Licencia:** MIT.
**Fecha de cierre:** 2026-11-27.

## Qué trae esta versión

### Asistente Android sin desinstalar el anterior

- CORT declara `VoiceInteractionService`, sesión de conversación, reconocedor y un
  asistente superpuesto. La persona puede elegirlo en **Ajustes → Aplicaciones →
  Aplicaciones predeterminadas → Asistente digital**; Gemini no se desinstala, se
  deshabilita ni se modifica.
- La superposición tiene controles de texto, micrófono, voz y **Detener**. Si Android
  no concede el permiso de superposición o el fabricante limita el asistente, CORT lo
  dice y deja disponibles la app y la baldosa.
- Un APK normal no puede preinstalarse como asistente privilegiado ni garantizar que
  todas las capas de One UI expongan la misma opción. La selección sigue siendo del
  usuario y del sistema.

### Paneles, herramientas y vida diaria

- Centro único con búsqueda, capacidades filtradas por dispositivo y estados
  `real`, `simulado` o `no disponible`; los paneles que sólo existen en PC no se
  presentan como funcionando en el teléfono.
- Sensores reales del aparato, podómetro con permiso y línea base, dispositivo medido,
  escucha foreground/background visible, audio focus, `MediaSession`, auriculares y
  controles multimedia.
- Memoria SQLite con procedencia y borrado, rutinas allowlisted, alarmas del sistema,
  cronómetro/temporizador, linterna, volumen, apertura de destinos permitidos y
  búsquedas acotadas.
- Notificaciones de otras apps sólo con acceso manual y allowlist; compartir abre el
  selector de Android con el borrador visible. CORT no envía mensajes arbitrarios de
  WhatsApp/SMS ni responde notificaciones automáticamente.
- La vista teléfono mantiene paneles adaptables y controles táctiles de al menos
  48 px. La misma cara Web viaja dentro del APK y el puente nativo atiende sus cuadros.

### Cerebro híbrido y catálogo Ollama

- El catálogo local incluye **272 modelos oficiales de Ollama**, con fecha de captura
  `2026-11-27`, búsqueda y metadatos de tamaño de parámetros. Estar en el catálogo no
  significa que un teléfono pueda ejecutarlo.
- En Android no corre un demonio de Ollama: el motor real es `llama.cpp`/JNI y consume
  GGUF. En la PC, el puente puede usar Ollama cuando está instalado y configurado.
- Hay cuatro GGUF verificados para descarga opcional: Qwen2.5 0.5B q2_K
  (415 182 688 B), 0.5B q4_K_M (491 400 032 B), 1.5B q2_K (752 880 160 B) y 1.5B q4_K_M
  (1 117 320 736 B). La descarga valida tamaño y SHA-256; ningún GGUF viaja dentro del
  APK.
- Para el Samsung A16 con unos 500–600 MB disponibles, el 0.5B q2_K puede **intentar**
  cargar con `mmap`; no se exige la puerta holgada. `CABE` pide archivo + 200 MiB,
  `INTENTAR` al menos la mitad del archivo + 100 MiB. El éxito y la velocidad sólo los
  puede medir el teléfono.
- La selección automática tiene en cuenta RAM, batería, temperatura y espacio. Exige
  al menos 20 % de batería para carga automática y 30 % + cargador para descarga
  automática; la descarga automática viene apagada. La carga manual pide 10 %. Por
  encima de 42 °C se bloquean carga y descarga manual; las operaciones automáticas no
  continúan si batería o temperatura son desconocidas.

### Nube, personalidades y planificador neuronal

- Ocho proveedores configurables: Anthropic, OpenAI, Gemini, OpenRouter, Groq, Mistral,
  DeepSeek y xAI; varios perfiles proveedor/modelo/clave. La clave se cifra con
  `AndroidKeyStore` y AES-256-GCM. El proveedor se declara y normaliza: CORT no intenta
  adivinar el origen de una clave leyendo su secreto.
- Sólo se aceptan endpoints HTTPS públicos, sin credenciales en URL, sin redirecciones
  y con respuesta limitada a 1 MiB. El modo Teléfono no cae a la nube; en Automático,
  cada turno de nube requiere confirmación.
- Tres personalidades —`cercana`, `directa`, `creativa`— comparten el mismo system para
  GGUF y nube.
- Las frases conocidas siguen ejecutándose primero por reglas. Para una petición no
  reconocida, el modelo puede conversar o proponer un plan JSON estricto. Java valida
  esquema, claves, tipos, longitud, acción y argumentos antes de tocar una herramienta.
- El plan admite como máximo cuatro pasos allowlisted. Shell, llamadas, mensajes,
  compras, escritura de memoria, destinos arbitrarios y JSON inválido se rechazan.
  Todo efecto espera una confirmación visible, exacta y de un solo uso; cancelar o
  agotar la espera no ejecuta nada.

## Qué puedes usar desde ya

Una vez instalada y concedidos los permisos que elijas:

1. Hablar o escribir con las reglas locales, el oído Vosk español incluido y la voz del
   sistema, sin portátil ni red.
2. Usar sensores, dispositivo, linterna, volumen, multimedia, auriculares, memoria,
   rutinas, alarmas y temporizador.
3. Elegir CORT como asistente digital y abrir su superposición si Android lo permite.
4. Activar la escucha en segundo plano desde la app o la baldosa; el aviso permanente
   indica cuándo está escuchando y **Detener** la cierra.
5. Leer notificaciones allowlisted y compartir borradores con el selector de Android.
6. Descargar un GGUF compatible y conversar localmente; el 0.5B q2_K es el primero que
   debe probarse en el A16.
7. Registrar tus propias claves de nube y combinar proveedores con el cerebro local,
   conservando el consentimiento por turno.
8. Enlazar la PC con **Escanear el QR** o pegando su token. `/memoria/puente` sincroniza
   memoria con límites y `/parlamento` sostiene **Hablar con la PC (voz)**: la respuesta
   puede sonar en el auricular y el texto completo queda en pantalla. Sin enlace, el
   teléfono informa `no disponible` en lugar de simular un resultado.

## Evidencia de esta corrida

- `scripts/prueba_apk.py`: **{{CHECS}}/{{CHECS}} comprobaciones** sobre el repositorio y
  el APK compilado.
- Suites JVM locales: **383/383 comprobaciones** entre RAM, secretos, escucha,
  sensores, medios, vida diaria, avisos, recursos, proveedores, planificador neural e
  integridad GGUF.
- `scripts/prueba_secretos.py`: **40/40 comprobaciones** de secretos, consentimiento,
  integridad, acciones y guardas de CI. Los permisos POSIX `0600` se validan en Linux.
- Producción Java compilada con `--release 11`; sintaxis de `cort-ui.js`,
  `cort-mock.js`, `cort-orbe.js` y `cort-android.js` verificada.
- El workflow comprueba motor nativo, oído, cara Web, alineación, firma, versión y
  contenido antes de publicar. `auditoria.txt` y `firma.txt` adjuntos salen del APK
  final.
- **No se ha instalado esta versión en el A16.** La calidad real del 0.5B, su latencia,
  RAM ocupada, conversaciones largas, permisos de One UI y comportamiento del asistente
  superpuesto siguen pendientes de ensayo físico.

## Los números del archivo publicado

| | Medida |
|---|---|
| peso | **{{PESO}} B = {{MB}} MB** |
| versión | `{{VERSION}}`, `versionCode {{CODE}}` |
| oído | {{OIDO}} |
| modelo español | {{MODEL}} B |
| cara Web | {{CARA}} |
| arquitecturas | {{ABIS}} |
| firma | {{LLAVE}} |
| certificado SHA-256 | `{{HUELLA}}` |
| SHA-256 del APK | `{{SHA}}` |

La huella del certificado está fijada en el workflow: si el secreto falta o la firma no
coincide con `cort-v0.19.0`, la release no se publica. Así se conserva la actualización
encima de CORT Móvil sin sustituir silenciosamente la identidad de firma.

## Instalar y comprobar

Descarga `CORT-movil.apk` y `CORT-movil.apk.sha256` desde esta release y comprueba:

```bash
sha256sum -c CORT-movil.apk.sha256
```

Si la bajada se corta, reanúdala:

```bash
curl -C - -OJL https://github.com/Sandra2244/CORT/releases/download/<etiqueta>/CORT-movil.apk
```

Instala encima de la versión anterior. Android puede mostrar Play Protect por tratarse
de una APK externa; **no se puede garantizar su comportamiento sólo desde el código**.
Verifica la huella SHA-256 de arriba y el certificado adjunto antes de autorizar una
instalación. CORT no solicita desinstalar Gemini.

El modelo español viene dentro del APK y se descomprime una vez. Para el cerebro GGUF,
abre **Almacén**, revisa RAM/batería/espacio y descarga el 0.5B q2_K. La primera carga
puede tardar o fallar si One UI tiene menos memoria libre de la medida; el panel muestra
el código de error y no inventa una respuesta.

## Límites y trabajo que sigue

- **Fase 8 — sugerencias acotadas:** pendiente. No hay proactividad que interrumpa ni
  ejecución automática de acciones sensibles.
- **Fase 9 — cámara y gestos:** pendiente. La cámara actual sólo lee el QR del enlace y
  no guarda fotogramas; no hay detector de manos ni preview de gestos.
- **Fase 10 — cierre 1.0:** matriz conductual completa y pruebas físicas pendientes.
- **Escucha:** no es continua 24/7. El servicio foreground se detiene con la pantalla
  apagada, tras cinco minutos de silencio, ante fallo o por orden del usuario. Android
  14+ no permite iniciar este micrófono con `BOOT_COMPLETED`; tras reiniciar hay que
  abrir CORT o tocar la baldosa. One UI puede limitar procesos en segundo plano.
- **Asistente:** selección y superposición dependen de Android, permisos y fabricante;
  no sustituye un asistente del sistema privilegiado.
- **Notificaciones y mensajes:** acceso manual, allowlist y borradores; no hay API
  universal de mensajes ni respuesta automática.
- **Alarmas:** se usa el reloj del sistema. Una alarma exacta propia requeriría otra
  aprobación y no está incluida.
- **Nube:** cada proveedor necesita su propia clave y configuración. No hay
  autodetección del proveedor por el contenido de la clave ni garantía de disponibilidad
  del servicio.
- **PC:** el puente existente se conserva; instalador Windows, paridad completa de
  herramientas, webcam/gestos y adaptador universal de nube siguen diferidos.
- **Wake-on-LAN:** pendiente; el bolsillo puede leer el estado de la PC, no encenderla.
- **Rendimiento A16:** sin cifra física todavía. No se declara soporte de conversaciones
  largas hasta medir carga, tokens/s, RAM, batería y térmica con el 0.5B.
- **Play Protect:** puede avisar o bloquear según ajustes del teléfono; no se promete lo
  contrario.

El detalle de alcance, pruebas y siguientes pasos está en
`docs/sdd/INFORME_HIBRIDO_PC_ANDROID.md`, `SPEC-OMNI-001.md` y `PLAN-OMNI-001.md`.
