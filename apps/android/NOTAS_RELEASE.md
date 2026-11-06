# CORT {{VERSION}} — la cara del PC dentro del teléfono, con el oído puesto y las dos ABIs

**Autora:** Askher Vargas y Sandra Lopez · soporte: `Sandrasofialopezgomez3@gmail.com` · `Carlosa3325@gmail.com` · **Licencia:** MIT.

## Qué trae esta versión

- **El teléfono abre la misma interfaz que el portátil (F19).** La queja de la dueña con
  cuatro capturas del Galaxy A16 fue literal: «necesito que sea la copia exacta de la versión
  de PC incluyendo sus funciones». Hasta aquí el APK mostraba `Cara.java` —botones nativos
  hechos a mano— mientras la PC mostraba `cort-web/index.html` con su orbe de three.js, sus
  paneles y sus tarjetas. Ahora el APK **empaqueta esos mismos archivos** en `assets/web/`
  (`index.html`, el bundle de React con su hash de Vite, `cort/cort-ui.js`, `cort/cort-orbe.js`,
  `cort/cort-mock.js`, el CSS, los iconos y los fondos) y los abre en su propio `WebView`.
  No es un parecido: son los mismos bytes, y la auditoría adjunta los lista uno por uno —
  **{{CARA}}**, contados sobre el APK que te estás bajando, no sobre la carpeta de etapa.
- **Donde no hay servidor WebSocket, lo hace Java (F19b).** La cara del PC habla por
  `ws://<host>:8765/ws`; dentro del teléfono no hay ningún puerto escuchando, así que
  `assets/web/cort-android.js` sustituye `window.WebSocket` antes de que `cort-mock.js` lo
  guarde (por eso es el **primer** `<script>` que se inyecta), y cada cuadro viaja por el
  puente nativo hasta `Nexo.java`. La interfaz no sabe que está en Android salvo por una
  bandera honesta, `CORT_esAndroid`, que apaga justo los rótulos que mentirían.
- **El puente Java contesta el contrato cuadro por cuadro (F19c).** `Nexo.java` atiende el
  `type` de cada cuadro —`scripts/prueba_apk.py` comprueba en cada corrida que ese despacho
  no se quede por debajo de 40 ramas— con datos del propio aparato: clima
  real (open-meteo, con IP si no hay ciudad), estado del equipo, temperatura de los sensores,
  apps instaladas, lista de la compra, notas, pendientes, volumen y brillo, micrófono y orbe.
  Lo que en el teléfono no existe **no se simula**: sale con `puente_aviso`, nombre del panel,
  el motivo concreto y lo que hace falta para tenerlo. La tabla `panelDe` cubre VPN, domótica,
  impresión 3D, Obsidian, juegos, Windows, antivirus, Jarvis OS, actualización, mirada por
  cámara, papeles de modelo y arrancar Ollama, y cada aviso dice la razón, no un «no disponible».
- **Y lo que sólo se puede medir en la PC viaja a la PC cuando están enlazados.** El teléfono
  no inventa un número: si el cuadro necesita al portátil, se pide por el enlace con token
  (F14a/F16) y, si el enlace no está, la cara lo dice con palabras.

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
  volumen…), memoria SQLite propia y dictado dentro del aparato con Vosk (el modelo español
  `vosk-model-small-es-0.42` **ya viene dentro del APK**, así que oye nada más instalarlo),
  sin red y sin servicios de Google.
- **La voz es la de esta rama:** `es-ES`, porque el portátil habla con espeak-ng y Piper
  `es_ES-*` (1,90x y 2,55x medidos en `cort-bridge/cort_voz.py`).

## Los números, medidos sobre el archivo que te estás bajando

| | antes (`cort-v0.11.0`, la ventana sin oído) | ahora |
|---|---|---|
| peso | 16 873 B | **{{PESO}} B = {{MB}} MB** |
| oído | el del aparato, por internet | {{OIDO}} — con el modelo de {{MODEL}} B dentro |
| cara | botones nativos | **la misma interfaz del portátil**: {{CARA}} |
| arquitecturas | la que hubiera | **{{ABIS}}** |
| cerebro | 33 reglas y la nube | **motor GGUF dentro del teléfono** + tres modelos descargables (ninguno dentro del APK) |
| enlaces | pegar la IP a mano | QR con la cámara **o** pegar la línea, con token |
| dependencias | ninguna | Vosk 0.3.75 (Apache-2.0) · JNA 5.14.0 (LGPL-2.1+) · modelo español Apache-2.0 · zxing core 3.5.3 (Apache-2.0) · llama.cpp b12121 (MIT) · three.js (MIT, con el aviso de derechos dentro del propio módulo) · Leaflet 1.9.4 (BSD-3-Clause) · Qwen2.5 GGUF (Apache-2.0, se bajan aparte) |

**Firmado:** {{LLAVE}} — `versionCode {{CODE}}`, huella del certificado `{{HUELLA}}…` (la misma
de las versiones anteriores, así que se instala encima: no hace falta desinstalar).

`auditoria.txt` (adjunto) es el desglose entrada por entrada, sacado del propio APK. Tres cosas
cambiaron respecto a `cort-v0.16.2`, y hay que decir por qué van hacia atrás de las tres
reducciones de aquella versión:

* **El modelo de español (**{{MODEL}} B**) vuelve a venir dentro del APK.** En `cort-v0.16.2`
  salió fuera para bajar el peso, y dejaba el dictado pendiente de un «Bajar el oído» que nadie
  había pulsado: un teléfono que abre la cara del PC y no oye es exactamente la queja anterior.
  Almacén sigue sabiendo bajarlo (`assets/oido.json` conserva URL, peso y la suma
  `09b23988…c6511f` de `deps.txt`) para el aparato que ya lo tenía; y `Motor.java` mira primero
  el archivo del almacén, así que no se desarma el del APK dos veces.
* **Las dos arquitecturas dentro: `arm64-v8a` y `armeabi-v7a`** (las que realmente viajaron son
  las que lista la tabla de arriba, leída del APK). Pregunta por el peso, la dueña contestó con
  las palabras que se citan tal cual: *«tiene que pesar más, no importa»*. El costo está medido,
  no estimado: `libcortmotor.so` es 56 508 296 B en arm64 y 46 695 488 B en armeabi-v7a, pero
  con las `.so` comprimidas la segunda añade del orden de 12 MB, no 46.
* **Sigue la tercera palanca de `cort-v0.16.2`, que es la que hace posible las otras dos:** las
  `.so` viajan comprimidas (`extractNativeLibs="true"`). El instalador las saca a
  `/data/app/…/lib` al instalar, así que `libvosk.so` (10 042 800 B en arm64) y
  `libcortmotor.so` salen con deflate — medido en la corrida 42115030288: de 56 508 296 B a
  14 265 297 B dentro del APK — en vez de byte por byte. El motor **no** se baja a la carpeta de
  datos de la app: Android 10+ se niega a ejecutar librerías nativas desde ahí.

El antecedente de todo esto es la tarde del 2026-11-05: el APK de `cort-v0.16.1` medía
162 817 475 bytes y bajado en esta casa (~40 KB/s, 70 minutos) se cortaba. Samsung, ante un
archivo truncado, dice **«aplicación no instalada»** — lo que la dueña leyó, y no era un
problema de Play Protect ni de la firma. Con el peso de esta release delante, si la bajada se
corta otra vez, no hace falta desinstalar nada: se reanuda con el `curl -C -` de abajo, o se
compila el paquete de una sola ABI con `CORT_ABIS="arm64-v8a"`.

El método de compilación no cambió: `aapt2` → `javac --release 11` → `d8` → `zip` → `zipalign`
→ `apksigner`, **sin Gradle y sin AndroidX**.

## Instalar

**Teléfono (Android 8+).** Descarga `CORT-movil.apk` y su `.sha256` y comprueba antes de abrirlo:

```bash
sha256sum -c CORT-movil.apk.sha256
```

Si el navegador corta la bajada (se nota en que el archivo pesa menos que el número de arriba,
y entonces el instalador dice «aplicación no instalada»), reanúdala en vez de empezar de nuevo:

```bash
curl -C - -OJL https://github.com/Sandra2244/CORT/releases/download/<etiqueta>/CORT-movil.apk
```

Instala y abre: **no pregunta por ninguna dirección para funcionar.** Pedirá permiso de
micrófono; sin él la cara sirve igual, sólo faltan el dictado y el parlamento, y la fila del
micrófono lo dice. Pide cámara **sólo** si pulsas «Escanear el QR». En el parlamento la contesta
de la PC sale por el **auricular de llamada**, el pegado a la oreja: no esperes sonido por el
altavoz de atrás.

**El oído ya viene puesto.** Con esta release no hay que bajar nada para dictar sin red: el
modelo español va dentro del APK y `Motor.java` lo descomprime **una sola vez** a
`filesDir/motor/` en el primer arranque (ese primer arranque tarda lo que tarda descomprimir
39,8 MB; después deja un marcador y no vuelve a tocarlo). La pantalla **Almacén → «Bajar el
oído»** sigue existiendo para el teléfono que venía de `cort-v0.16.2` y ya lo tenía descargado:
`Motor` mira primero el archivo del almacén, le comprueba la suma y, si cuadra, no desarma el
del APK. Mientras no haya modelo en ningún sitio, el dictado cede al motor de voz del aparato
—que manda el audio por internet— y la cara lo dice con esas palabras.

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
- **Todavía no levanta la PC desde el móvil** (Wake-on-LAN dentro de tu Wi-Fi). El bolsillo ya
  lee lo pendiente; encenderla desde el teléfono es lo que sigue.
- **En el teléfono no corre Ollama, y no hace falta.** Lo que sí corre es `llama.cpp` con el
  GGUF que elijas (U1): el razonamiento local existe y se mide con «Probar (mide tokens/s)».
  Lo que **no** está medido es cuántos tokens por segundo da tu aparato, así que aquí no se
  escribe ninguna cifra de velocidad.
- **Sigue sin despertar por voz en segundo plano** (es la fase F19d, con su decisión tomada:
  la palabra «oye CORT» reconocida con el propio modelo español de Vosk dentro de un servicio
  en primer plano, y corte a los 5 min de silencio o al apagarse la pantalla). Hoy el micrófono
  se abre cuando tú abres la cara o pulsas ●.
- **La cara del PC necesita el WebView del sistema.** Android no trae un navegador propio para
  las apps: CORT usa el WebView que Samsung ya tiene instalado. Si falta o es muy viejo y la
  página no arranca, `MainActivity` cae a la **cara nativa de siempre** (`Cara.java`) y lo dice
  en pantalla: el teléfono no se queda en blanco y ninguna función nativa se pierde.
  Actualizar el WebView (Play Store → «Android System WebView») devuelve la cara del PC.
- **Los paneles del portátil que no viajan al teléfono, y por qué.** VPN, domótica, impresión
  3D, Obsidian, juegos, Windows/winget, antivirus, Jarvis OS, actualización desde el repo,
  mirada por cámara, papeles de modelo de Ollama… Cada cuadro que la cara pregunta y el teléfono
  no tiene sale con `puente_aviso`: nombre del panel, el motivo concreto y lo que hace falta
  para tenerlo (enlazando la PC, casi siempre). No se pinta un panel lleno de ceros.
- **La cámara del teléfono sólo lee el cuadro del enlace** y no guarda ningún fotograma; los
  gestos ante la cámara (S2) corren en la PC, con su cámara. Leer la pantalla de otras apps con
  accesibilidad y los sensores restantes es la fase F19e.
- **Nadie lo ha instalado todavía en el A16.** Lo medido en esta corrida: el compile, la firma,
  la estructura del APK y las {{CHECS}} comprobaciones de `scripts/prueba_apk.py`, que el propio
  workflow ejecuta antes de publicar. Cuánto tarda el modelo en cargarse en tu teléfono, cuánta
  RAM ocupa, cuánto tarda un dictado real y **cómo se ve la cara del PC en tu pantalla** es lo
  que saca el ensayo físico; la app ya imprime el tiempo de cada dictado para que ese número
  salga de la mano y no de un deseo.

---
SHA-256 del APK publicado: `{{SHA}}`
