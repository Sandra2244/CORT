# PLAN_MOVIL — CORT integrada en el Galaxy A16, con cerebro local

Escrito el 2026-11-04, después de publicar F16 (`cort-v0.14.0`) y de medir la PC.
Su regla: **primero el teléfono**, y que sea el mismo CORT en los dos aparatos.
Cada número de aquí abajo está medido en esta PC o en el runner de GitHub; lo que no
está medido lleva la palabra *por medir*.

## 0. Diagnóstico sin adornos

| superficie | lo que funciona hoy | lo que falta |
|---|---|---|
| Teléfono (APK `cort-v0.14.0`, 20 clases Java, 6 435 líneas) | orbe y registro nativos, 33 reglas de frases, 15 manos locales, memoria SQLite propia, dictado offline con Vosk, enlace con la PC por QR/token, y desde hoy **hablarle a la PC y oírla por el auricular** | **un cerebro que hable lenguaje libre**: hoy el teléfono contesta con reglas y con la voz de la PC; sin la PC encendida no piensa |
| PC (puente Python) | escucha Vosk, habla espeak-ng/Piper, acciones nativas, vida diaria, autocrítica, núcleo con reja | que el teléfono le vea los pendientes (ya está en la rama: `GET /bolsillo`, F17) y levantarla apagada |

Lo que la dueña siente como «descerebrada» es exactamente una fila de esa tabla: **el
móvil no tiene modelo**. Todo lo demás es cosmético al lado de eso.

## 1. Fase U1 — el cerebro dentro del teléfono (F13, la urgente)

**Qué se trasplanta.** `llama.cpp` (ggml-org, MIT, ~80 k estrellas) compilado con el NDK
en el runner de Actions para `arm64-v8a` y `armeabi-v7a`, y un envoltorio JNI propio de
~200 líneas (`CerebroLocal.java`) que expone `carga(modelo)`, `dice(prompt, max)`,
`tok_s`, `ram_usada`. Se acreditan llama.cpp y su GGML en `NOTICE` junto a Vosk.

**El modelo NO va dentro del APK.** El que dio la dueña mide **752 880 160 bytes
(718 MB)** en disco: `qwen2.5-1.5b-instruct-q2_k`. Metido en el APK, el archivo pesaría
lo mismo que un sistema operativo y la release sería inutilizable.

**Cómo viajó al final, y por qué ya no viaja por el enlace.** Lo previsto aquí era que lo
sirviera la PC por HTTP local; en la práctica la dueña pidió que el teléfono **descargue
más cerebros estilo la PC**, así que U1 lo baja directamente de Hugging Face desde la
pantalla «Almacén de cerebros», sin encender el portátil: `assets/cerebros.json` fija tres
modelos con su peso y su SHA-256 medidos el 2026-11-05, el hilo de CORT reanada con `Range`
y la suma se recalcula en el teléfono al terminar. El enlace de la casa sigue siendo el
camino del oído y de la memoria compartida (F14/F16/F17), no el de los modelos.

**Puerta de RAM, medida en el aparato antes de prometer.** La primera corrida de la fase
imprime en pantalla `getMemoryInfo().availMem`, `totalMem` y núcleos del A16. Con 4 GB
libres en el momento de la prueba, 718 MB de modelo + caché clave-valor caben; con 1,5 GB
libres no. Si no cabe, CORT lo dice con el número y ofrece el escalón menor
(`qwen2.5-0.5b-instruct-q4_K`, ~400 MB, y más rápido), o el cerebro de la PC por el
parlamento, que ya funciona.

**Presupuesto de velocidad, para no vender humo.** En un móvil de gama de entrada de dos
clusters, un 1,5 B en q2_K da **~2-6 tokens/s** por token generado (cifra de catálogo del
motor, *por medir en su A16*). Una respuesta de 120 caracteres son ~35 tokens: entre 6 y
18 segundos. Por eso la fase U1 entrega también **la respuesta en streaming**: CORT
empieza a hablar en cuanto tiene la primera frase, como hace la PC.

**Misma constitución.** El prompt del sistema, la reja y el `origen` (real / no
disponible) se copian de `cort_memoria.py` para que lo que salga del móvil sea lo mismo
que saldría del portátil.

Release objetivo: `cort-v0.16.0`, **ya con las dos piezas que faltaban**: el pegamento JNI
existe (`apps/android/jni/cort_motor.cpp`, 452 líneas sobre la API pública de `llama.h`) y
`motor-local.yml` descarga el NDK r26d y el fuente de llama.cpp b12121 con su SHA-256 fijada
y compilada en el runner. Una medición obligó a cambiar el enlace: `libllama.so` comparte con
SONAME `libllama.so.0` (el `SOVERSION` que fija el propio CMake de llama.cpp), así que el
pegamento se enlaza **estático y autocontenido** en `libcortmotor.so` y el workflow se niega
a publicar si todavía dependiera de `libllama` o `libggml`.

Medido el 2026-11-05 en la corrida verde 42025488743: `libcortmotor.so` pesa **56 508 296
bytes** en arm64-v8a y **46 695 488** en armeabi-v7a, y el artefacto completo del motor suma
208 125 998 bytes repartidos en diez librerías. Dentro del APK **sólo va el pegamento**: las
otras ocho (`libllama`, `libggml`, `libggml-base`, `libggml-cpu` por cada ABI) las produce el
CMake de llama.cpp de paso y están ya dentro de `libcortmotor.so` por el enlace estático, así
que copiarlas costaría ~105 MB de APK sin añadir una sola función. `compilar.sh` lo hace así y
lo imprime con su peso.

Cómo llega ese archivo al build, escrito con los dos intentos fallidos dentro: `apk-movil.yml`
busca el artefacto `motor-local-ndk` por la API y saca **su id** (el `first` va dentro del
`--jq`, porque un `| head -1` pegado a `gh` con `set -uo pipefail` puede abortar el paso con
señal 141). La descarga es `curl -sSI` contra `api.github.com` para leer el `Location` — medido
con el artefacto 13414146808: 622 caracteres hacia el almacén de Azure, y ese enlace respeta
`Range` (206 con 4 bytes pedidos) — y después `curl` de ese enlace firmado **sin cabecera de
autorización**, porque un token de Actions no debe salir hacia el almacenamiento en una
redirección. Lo que NO funciona y quedó dicho en el YAML: `actions/download-artifact@v4` con
`run-id: ${{ env.MOTOR_ARTIFACT }}`, porque un `env.` dentro del `with:` de un `uses:` no se
rellena y la acción buscó en su propia corrida (corrida 42104161078: build verde de punta a
punta y `lib/arm64-v8a/libcortmotor.so: no está en el APK`), y `gh api … -i`, porque `gh` sigue
la redirección y se pone a bajar los 208 MB por la tubería. Y el paso que publica la release se
niega si `auditoria.txt` dice que el pegamento no entró: compilar puede ser tolerante con un
trabajo ajeno; publicar notas que prometen el cerebro y no lo llevan, no.

Lo que **todavía no está** de esta fase, dicho con nombre: los `tokens/s` y la RAM que ocupa
en el A16 (sólo se miden en el aparato; el botón «Probar (mide tokens/s)» los imprime), y la
respuesta **en streaming en la cara** — el nativo sí emite token a token (`nativeOir`) y el
almacén lo muestra, pero `Cara.porNube` espera la frase entera antes de hablar.

## 2. Fase U2 — que se integre en el sistema (lo del menú de WhatsApp)

Lo que ella describe —pulsar un mensaje, que aparezca *transcribir / editar / copiar* y
añadir **leer**— es en Android la intención `ACTION_PROCESS_TEXT`: cualquier activity que
la declara aparece en el menú de selección de texto de **cualquier aplicación** (WhatsApp,
Chrome, Notas), sin permisos especiales, sin ser TalkBack y sin servir molesta. Se añade
`Lectura.java`: recibe el texto subrayado, y **lo lee en voz alta, lo resume o lo
pregunta al cerebro**, con un botón de velocidad y otro de pausa.

Lo demás de la integración, en el mismo orden de valor:

* **Compartir (`SEND`)** — desde el navegador o el lector de PDF: «leer con CORT».
* **Baldosa del panel rápido** (`TileService`, API 24): un toque = escuchar, otra vez =
  callar. No requiere mantener pulsado.
* **Sensor de audífonos** (lo que estaba a medias): `AudioManager.getDevices()` +
  `AudioDeviceCallback` + `ACTION_HEADSET_PLUG`. Regla: si hay audífonos, la voz sale por
  los audífonos; si no, por el auricular de la oreja. Y el botón del auricular
  (`KEYCODE_MEDIA_PLAY_PAUSE`, vía `MediaSession`) dicta sin tocar la pantalla.
* **Saludo al encender** (`RECEIVE_BOOT_COMPLETED`): «buenos días / buenas tardes /
  buenas noches», con lo pendiente y el tiempo. Honestidad obligada: One UI cierra
  procesos en segundo plano, así que la pantalla de enlace trae el paso para
  eximir a CORT de la optimización de batería, y la fase termina con **el número de
  reinicios probados y cuántos salieron**, no con la promesa.
* **Asistente del sistema**: el servicio `VoiceInteractionService` ya está declarado; en
  el A16 se activa desde Ajustes y *hay que medir si One UI 7 deja ponerlo por defecto*.
  Si Samsung no lo permite, queda la baldosa, el gesto del orbe y el botón del auricular,
  que hacen el mismo servicio.

Release publicada: `cort-v0.15.1` — 59 581 673 bytes (56,82 MB), SHA-256
`03b001bd…4741`, `classes.dex` de 798 160 B, 17 entradas, 159/159 comprobaciones y la
misma firma del repo (`faabef46…1977`), medida en el run 41977159844 — verde de
principio a fin, incluido el paso de publicar. La
`cort-v0.15.0` quedó sin publicar: su árbol no compilaba — 8 errores de `javac` en la
corrida 41971907412 por tres nombres de API escritos de memoria
(`AudioDeviceCallback` anidado, `getTile()`, `getLongAvailableBytes()`). Se corrigió
hacia adelante, sin mover la etiqueta.

## 3. Fase U3 — que se porte como una persona (iniciativa e investigar)

* **Iniciativa en el móvil**: el motor de `cort_memoria.iniciativa()` (PC) se trasplanta
  con lo que el teléfono ya tiene medido —hora del día, batería, sus propios pendientes de
  SQLite, auricular conectado, último recuerdo— y propone en vez de esperar. Con tope:
  una propuesta por sesión, y calla si ella dice «ahora no».
* **Investigar sin Google**: Wikipedia (REST `summary`) y DuckDuckGo Instant Answer, por
  HTTPS, sin claves y sin cuentas. CORT busca, lee y **cita de dónde sacó la frase**. Es
  lo que ella llama ser «invasiva»: no espera que le abran la pestaña.
* **Leer documentos** (empezado): la PC ya saca las letras de un PDF con `poppler` —
  medido: `manual.pdf`, 93 páginas, 126 329 caracteres en **3 417 ms**, con tope de
  60 000 caracteres y el archivo borrado del disco en el mismo `finally`. El teléfono lo
  pide por el enlace y lo lee. Un PDF sin letras (escaneado) se dice como lo que es: el
  lector de caracteres (`tesseract`) no está instalado en esta PC.
* **El mismo CORT en los dos aparatos** (F14c): preferencias, lista y notas viajan por el
  enlace, con las cuatro reglas ya escritas (la llave nunca dentro de un recuerdo).

Release objetivo: `cort-v0.17.0`.

## 4. Fase U4 — la PC, sin duplicar el trabajo

* **Levantar la PC apagada: hoy no puede, y está medido.** `eth0` (r8169) no declara
  «Supports Wake-on» y no tiene cable; `wlan0` (rtl8723be) no anuncia WoWLAN en
  `iw phy0 info`; y el chip es un Celeron N2805 sin AVX. Tres salidas, todas suyas:
  (a) cable al router + BIOS con Wake-on-LAN + `ethtool -s eth0 wol g` (necesita sudo de
  red, que ella no me ha dado); (b) enchufe inteligente con firmware local (Tasmota/Sonoff
  LAN) + BIOS «encender al volver la corriente»; (c) no apagarla: suspenderla y despertarla
  desde otro aparato suyo. Sin una de estas tres, la función se queda en la lista con su
  motivo.
* **El bolsillo (F17)** está cerrado en las dos mitades: `GET /bolsillo` devuelve
  pendientes con sus minutos, lista, notas y la máquina medida, y `Bolsillo.java` (U2,
  `cort-v0.15.1`) ya lo pinta en la pantalla del teléfono.
* **Manos en el navegador (F18)** con `xdotool` (presente) y portapapeles — *medido*: en
  esta PC no hay `xsel` ni `wl-copy`, así que hay que resolver el portapapeles con
  `xdotool`/`xclip` antes de prometer copiar y pegar.

Release objetivo: `cort-v0.18.0`.

## 5. Lo que queda fuera, dicho con su motivo

* Playwright/Chromium para manejar el navegador: ~300 MB contra **260 MB de RAM
  disponible medidos** en esta laptop. Se hace con teclas y portapapeles.
* OCR de PDFs escaneados: sin `tesseract` instalado; entra sólo si ella pide el paquete.
* Palabra de activación en segundo plano en el móvil: gasta batería y detecta de más; se
  mide en otra fase si la quiere.
* Modelos de más de 1,5 B parámetros en el A16: no caben ni responden.

## 6. Cómo se entrega cada cosa

Cada fase: código → suite en `scripts/` con salida y exit code verificados → commit en
`web/cort-v0` → release `cort-vX.Y.Z` compilada en Actions con auditoría y SHA-256 →
informe corto con números, transplantes y límites. Los ensayos que necesitan el aparato
(cuánto tarda el modelo, si se oye el auricular, si el escáner lee a un metro) se hacen
**en su A16**, con la pantalla de medición de CORT imprimiendo las cifras.
