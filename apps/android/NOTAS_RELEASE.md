# CORT {{VERSION}} — el teléfono ya piensa solo: motor GGUF, almacén de cerebros y su ruta

**Autora:** Askher Vargas y Sandra Lopez · soporte: `Sandrasofialopezgomez3@gmail.com` · `Carlosa3325@gmail.com` · **Licencia:** MIT.

## Qué trae esta versión

- **Se enlaza con la PC leyendo un QR (F14b).** En la pantalla de enlace está el botón
  «Escanear el QR del portátil»: la cámara del teléfono lee el cuadro que CORT imprime en la
  terminal de la PC (`python3 cort-bridge/cort_enlace.py --qr`) y la dirección se rellena sola.
  El decodificador es zxing core 3.5.3 (Apache-2.0), descargado, leído y fijado por SHA-256 en
  `apps/android/deps.txt`. **Ningún fotograma se guarda**: se decodifica y se tira, la cámara
  no es obligatoria y si algo falla el teléfono lo dice con palabras en vez de cerrarse.
- **Pegar la línea sigue valiendo (plan B).** Se copia la línea completa que imprime el
  arranque de CORT —con su `?token=`— en el campo de enlace. `Puente.urlDelPuente` quita el
  puerto de la interfaz (8766), pone el del core (8765) y conserva la llave. Escribir sólo la
  IP también abre la ventana, pero sin llave el puente contesta `401` y el teléfono avisa de
  que así no hay memoria compartida.
- **La memoria del teléfono ya habla con la de la PC (F14a).** `GET`/`POST /memoria/puente`
  está servido en el puerto del core, detrás del token de la red. Topes: 300 caracteres por
  fila, 500 filas, 262 144 bytes. Las cuatro reglas —la llave nunca dentro de un recuerdo,
  fusionar no borra, el dedupe ignora espacios de sobra, los topes escritos— están en
  `cort-bridge/cort_enlace.py`.
- **Hablarle a la PC y oírla por el auricular (F16).** Botón «Hablar con la PC (voz)» en la
  pantalla de enlace, y también desde el pulso largo en cualquier superficie: se **mantiene
  pulsado**, se habla, se suelta. La grabación (16 kHz mono, 16 bits) viaja a
  `POST /parlamento` en el puerto del core —con el mismo `?token=` del enlace—, allí el oído de
  la PC (Vosk) la convierte en texto, la frase entra por **el mismo despacho que el WebSocket**
  y la voz sintetizada en la PC vuelve dentro de la respuesta para sonar en el **auricular** de
  tu oreja, no por el altavoz de la casa. Medido en esta PC con habla real: un dictado de
  2,33 s contestó en **3 273 ms** con el modelo ya cargado (la voz sintetizada en 191 ms) y en
  **9 267 ms** en el primer turno del proceso, que paga los ~6 s de carga del modelo. La pantalla
  imprime los cuatro tiempos de cada vuelta y cuántos caracteres le dijo la PC.
  **El auricular no traga arengas:** dice la primera frase —techo de 90 caracteres— y el texto
  entero queda escrito en la pantalla. Medido: la respuesta honesta de 416 caracteres sin techo
  eran 22,8 s de voz y 1 342 768 bytes de base64; con el techo son 10,95 s y 643 640 bytes.
  **El dictado no se guarda en ninguna parte:** se arma en memoria, se envía, y en la PC se
  borra el WAV de paso y el de voz en el mismo `finally`; lo que la PC habla por su altavoz
  caduca a los 600 s para que `/tmp` no sea un archivo de todo lo que CORT dijo.
- **Te lee en cualquier aplicación (U2, `Lectura.java`).** Mantén pulsado un mensaje de
  WhatsApp, un párrafo de un PDF o lo que estés escribiendo, y en el menú sale **«Leer con
  CORT»**. No es un servicio de accesibilidad ni un modo molesto que habla solo: es la
  intención `ACTION_PROCESS_TEXT` de Android, así que CORT sólo suelta voz cuando tú lo
  eliges. La pantalla trocea el texto **por frases** (hasta 380 caracteres y cortando en `.`
  `!` `?` o salto de línea), da tres pasos de lectura (normal / rápido / muy rápido), botón
  **Parar** y botón **Copiar**. El texto se queda en memoria: no se escribe en disco en ningún
  sitio. Con `ACTION_SEND` declarado, lo compartido desde el navegador entra por la misma cara.
- **Sabe si llevas audífonos (U2, `Audifonos.java`).** Antes de contestar mira las salidas
  activas del aparato (`getDevices`) y decide: con auriculares puestos la voz va **a los
  auriculares** (y no se mete en modo de llamada, que arrastra el Bluetooth al perfil de
  teléfono y suena peor); sin nada en la oreja va al **auricular de llamada**, pegado a la
  oreja. La pantalla dice por dónde va a sonar: «Sale por los audífonos de cable» / «por los
  Bluetooth» / «por el auricular del teléfono». Y si te quitas los auriculares mientras está
  hablando, **se calla** en vez de quedarse leyendo por el altavoz de la casa. El sensor no
  pide ningún permiso: son lecturas del propio teléfono.
- **Saluda al encender (U2, `Arranque.java`).** `BOOT_COMPLETED` → «Buenos días / Buenas
  tardes / Buenas noches. Soy CORT y sigo aquí, en tu teléfono, sin red.», dicho por la voz e
  **hito** además en una notificación sin sonido, porque con la pantalla bloqueada hay motores
  de voz que no sueltan audio. **El límite, escrito:** Samsung (One UI) cierra procesos en
  segundo plano y puede que el saludo no llegue si CORT sigue optimizado por batería; la
  pantalla de enlace tiene el botón «Que el teléfono no cierre CORT», que abre el ajuste del
  sistema con esta app ya escrita. Con Android 13 además se pide el permiso de notificaciones
  la primera vez que abres la app.
- **Baldosa en el panel rápido (U2, `Baldosa.java`).** Bajar el panel y tocar «CORT te
  escucha» abre la escucha directamente, sin buscar el icono entre las páginas del lanzador.
- **El bolsillo: qué le debe la PC (F17, `Bolsillo.java`).** Con el enlace puesto, la pantalla
  lista los recordatorios pendientes de la PC con los minutos que faltan y su fecha, los
  vencidos, la compra y las notas, y cómo está la máquina (RAM libre, CPU, núcleos, tiempo
  encendida). Se pide a `GET /bolsillo` en el puerto del core con el mismo `?token=` del
  enlace; si la PC está apagada la pantalla dice **no contestó** y no inventa nada. Lo que
  hay en esa pantalla **no se manda a ningún sitio**.
- **Un cerebro GGUF dentro del teléfono (U1, `libcortmotor.so`).** CORT piensa en tu aparato
  sin portátil y sin internet: el motor es llama.cpp b12121 cruzado con el NDK r26d de Google en
  el runner (`.github/workflows/motor-local.yml`), enlazado **estático y autocontenido** porque
  la biblioteca compartida sale con SONAME `libllama.so.0` y el `System.loadLibrary` del APK no
  la encontraría. El pegamento JNI (`apps/android/jni/cort_motor.cpp`, 452 líneas) usa sólo la
  API pública de `llama.h` y CORT lo comprueba en el workflow: 11 símbolos nativos tienen que
  estar exportados, o la corrida se pone roja. Licencia leída antes de usarla: **MIT**.
- **Y se pueden descargar más cerebros, estilo la PC (U1, `Cerebros.java`).** La pantalla
  «Almacén de cerebros» ofrece tres Qwen2.5-Instruct con peso y SHA-256 **medidos el 2026-11-05**
  contra el árbol público de Hugging Face: 0,5B q4_K_M (491 400 032 B), 1,5B q2_k
  (752 880 160 B) y 1,5B q4_K_M (1 117 320 736 B). Bajar, **reanudar** donde se cortó (`Range`,
  sin `DownloadManager`: un enlace con token no viaja en una notificación), y al terminar CORT
  vuelve a calcular la suma del archivo entero en el teléfono — si no cuadra, lo borra y lo dice,
  porque un GGUF a medias no falla: abre y contesta basura. Se abre desde el botón de la pantalla
  de enlace o tocando el chip `◈ cerebro` de la cara. **Ningún modelo va dentro del APK**: el
  instalador sigue pesando lo que pesa.
- **Cómo decide a quién preguntar (U1).** Las 33 reglas de siempre van delante (son exactas y
  contestan en milisegundos). Lo que no esté en la tabla va **al cerebro del teléfono** si el
  modo y la RAM libre lo permiten, y si no a la PC o a la nube. Tres modos elegibles en pantalla:
  **Automático · Teléfono · PC o nube**. La puerta es medidora, no promesa: hace falta el **doble**
  del archivo en RAM libre, y la pantalla dice los megas que hay en este teléfono ahora.
- **«El aparato, medido» (U1, `Equipo.java`).** Una pantalla que lee en este teléfono lo que
  decide si el cerebro local cabe: RAM total y **libre ahora** (`ActivityManager` + 
  `/proc/meminfo`), núcleos, ABIs, almacenamiento libre frente a los 752 880 160 bytes del
  modelo, carga de la pila y el motor de voz asignado. Todo el texto es seleccionable para
  copiarlo. Estos números son los que se usan en el informe de la fase; no se envían a la PC.
- **Y sigue funcionando sola, sin portátil encendido:** orbe y registro nativos, 33 reglas de
  frases, 15 manos locales (linterna, hora, fecha, alarma, cronómetro, decir, buscar, app,
  volumen…), memoria SQLite propia y dictado dentro del aparato con Vosk (modelo español
  `vosk-model-small-es-0.42`), sin red y sin servicios de Google.
- **La voz es la de esta rama:** `es-ES`, porque el portátil habla con espeak-ng y Piper
  `es_ES-*` (1,90x y 2,55x medidos en `cort-bridge/cort_voz.py`).

## Los números, medidos sobre el archivo que te estás bajando

| | antes (`cort-v0.11.0`, la ventana sin oído) | ahora |
|---|---|---|
| peso | 16 873 B | **{{PESO}} B = {{MB}} MB** |
| oído | el del aparato, por internet | {{OIDO}} |
| cerebro | 33 reglas y la nube | **motor GGUF dentro del teléfono** + tres modelos descargables (ninguno dentro del APK) |
| enlaces | pegar la IP a mano | QR con la cámara **o** pegar la línea, con token |
| dependencias | ninguna | Vosk 0.3.75 (Apache-2.0) · JNA 5.14.0 (LGPL-2.1+) · modelo Apache-2.0 · zxing core 3.5.3 (Apache-2.0) · llama.cpp b12121 (MIT) · Qwen2.5 GGUF (Apache-2.0, se bajan aparte) |

**Firmado:** {{LLAVE}} — `versionCode {{CODE}}`, huella del certificado `{{HUELLA}}…` (la misma
de las versiones anteriores, así que se instala encima: no hace falta desinstalar).

`auditoria.txt` (adjunto) es el desglose entrada por entrada, sacado del propio APK: modelo
**{{MODEL}} B**, `libvosk.so` 10 042 800 B (arm64) y 8 985 628 B (armeabi-v7a) y `libcortmotor.so` (el motor GGUF, cuyo peso exacto sale del propio `auditoria.txt` de esta release, no de aquí), con las
bibliotecas **sin comprimir y alineadas a página** porque el manifiesto declara
`extractNativeLibs="false"` — si falta algo de eso, el arranque muere con
`UnsatisfiedLinkError`. El método de compilación no cambió: `aapt2` → `javac --release 11` →
`d8` → `zip` → `zipalign -p` → `apksigner`, **sin Gradle y sin AndroidX**.

## Instalar

**Teléfono (Android 8+).** Descarga `CORT-movil.apk` y su `.sha256` y comprueba antes de abrirlo:

```bash
sha256sum -c CORT-movil.apk.sha256
```

Instala y abre: **no pregunta por ninguna dirección para funcionar.** Pedirá permiso de
micrófono (sin él la cara sirve igual, sólo faltan «● hablar» y «Hablar con la PC (voz)») y
permiso de cámara sólo si pulsas «Escanear el QR». En el parlamento la contesta de la PC sale
por el **auricular de llamada**, el pegado a la oreja: no esperes sonido por el altavoz de atrás.
El primer dictado puede tardar: el modelo se descomprime una sola vez
a los datos de la app (~90 MB ocupados) y la cara dice en qué punto está.

**PC (Debian / Ubuntu / MX Linux XFCE).** Descarga el `Source code (tar.gz)` de esta release,
desempaqueta y:

```bash
cd CORT && ./scripts/instala_cort.sh        # y --red si además lo quieres ver desde el teléfono
```

El instalador comprueba `python3`/`venv`, crea `.venv`, instala sólo lo de
`requirements-cort.txt`, escribe el lanzador de menú y el arranque de XFCE, e imprime la
dirección del puente con su token y su QR. **No ejecuta `sudo` sin preguntarte con los paquetes
exactos delante y no baja instaladores de terceros a la shell.** `para_cort.sh` apaga y
`desinstala_cort.sh` quita lo instalado sin tocar tus datos.

**Windows.** Todavía no hay instalador probado: es la fase W1 y se dice aquí en vez de prometerlo.

## Lo que NO hace todavía, dicho con nombre

- **El enlace no cifra.** Falta TLS local: la llave viaja en el `?token=` dentro de tu red.
  Vale para tu casa; no lo abras a un Wi-Fi público ni a internet.
- **Sólo viajan los recuerdos.** Preferencias, lista de tareas y notas entran en el siguiente
  viaje (F14c).
- **Cuánto tarda el cerebro en un teléfono real: sin medir.** El motor compila y la pantalla
  «Probar (mide tokens/s)」saca la cifra del aparato; en el PC de desarrollo no hay NDK ni
  `javac` del SDK, así que esa medida sólo puede darla tu Galaxy A16. El tope de 120 tokens por
  vuelta y el botón «Interrumpir» existen precisamente porque no se ha medido todavía.
- **El parlamento necesita el puente renovado en la PC.** `/parlamento` se sirve desde el
  `cort_server.py` de esta versión: si el CORT del portátil sigue encendido de antes, la ruta
  contesta `404` y el teléfono lo dice con palabras. Reinicia CORT en la PC y ya oye.
- **El cerebro que contesta es el que haya.** En el parlamento no hay un segundo motor: si la PC
  no tiene Ollama respondiendo, la voz que sale por el auricular es la respuesta honesta
  («Sin cerebro local…», con la RAM medida delante) —entera en la pantalla, por su primera
  frase en el auricular. Sin esa respuesta no hay conversación.
- **Todavía no levanta la PC desde el móvil** (Wake-on-LAN dentro de tu Wi-Fi) **ni le muestra
  a la dueña las tareas pendientes del portátil.** Es lo que sigue, en ese orden.
- **No lleva cerebro grande dentro** (F13). El modelo que razona sigue en la PC con Ollama; en
  el teléfono sólo está el oído. «Ollama en Android» no se afirma sin haberlo compilado y medido.
- **No despierta con «ok CORT» en segundo plano.** El ● se pulsa; el traje de asistente de
  Android (`VoiceInteractionService`) está declarado y enruta, pero activarlo como asistente del
  sistema es una prueba en el aparato.
- **La cámara del teléfono sólo lee el cuadro del enlace** y no guarda nada; los gestos ante la
  cámara (S2) corren en la PC, con su cámara.
- **Nadie lo ha instalado todavía en el A16.** Lo medido en esta corrida: el compile, la firma,
  la estructura del APK y las {{CHECS}} comprobaciones de `scripts/prueba_apk.py`, que el propio
  workflow ejecuta antes de publicar. Cuánto tarda el modelo en cargarse en tu teléfono, cuánta
  RAM ocupa y cuánto tarda un dictado real **es lo que saca el ensayo físico**; la app ya imprime
  el tiempo de cada dictado para que ese número salga de la mano y no de un deseo.

---
SHA-256 del APK publicado: `{{SHA}}`
