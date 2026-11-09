# CORT {{VERSION}} — el oído en segundo plano, la mano en la pantalla y un cerebro que sí cabe en el A16

**Autora:** Askher Vargas y Sandra Lopez · soporte: `Sandrasofialopezgomez3@gmail.com` · `Carlosa3325@gmail.com` · **Licencia:** MIT.

## Qué trae esta versión

### Lo nuevo (F20 y el P0 de la auditoría del 2026-11-08)

- **«Oye CORT» dicho a secas, sin abrir la app (F20, `ServicioEscucha.java`).** Un servicio
  en primer plano —lo único que Android deja vivir fuera de la pantalla— mantiene el oído
  Vosk de español abierto con una gramática de tres palabras: `hola cort`, `oye cort` y el
  comodín. Al oír la palabra, CORT contesta; el resto del audio no se guarda ni se manda a
  ningún sitio. Se enciende desde la app o desde la baldosa «CORT te escucha» del panel
  rápido, y se apaga solo por cuatro salidas: pantalla apagada, cinco minutos de silencio,
  fallo del oído u orden de la dueña. **Los límites, escritos:** Android 14+ no deja arrancar
  un servicio de micrófono con el encendido del teléfono, así que tras reiniciar hay que
  abrir CORT o tocar la baldosa; y con la pantalla apagada el servicio se detiene (nadie le
  habla a un teléfono guardado, y el micrófono abierto cobra batería). El aviso en la bandeja
  es obligatorio y es la prueba de que está escuchando: sin aviso, no hay escucha.
- **Leer lo que estás viendo y escribir por ti (F20b/c, `Pantalla.java`).** Un servicio de
  accesibilidad que lee la ventana completa de cualquier aplicación, puede escribir texto
  por la dueña y analizar lo que hay en pantalla. **Se enciende ella, en los Ajustes de
  Android → Accesibilidad:** no hay forma de autoconceder esto (por diseño de Android), y
  CORT abre la pantalla exacta del ajuste. Mientras no esté encendido, `Pantalla` no hace
  nada y lo dice; el «Leer con CORT» del menú de texto seleccionado (`Lectura.java`) sigue
  siendo la vía que no pide ningún ajuste.
- **El WebSocket de verdad y el certificado de la casa (F20a, `PuenteWs.java` y
  `cort-bridge/cort_tls.py`).** El teléfono ya habla RFC 6455 escrito a mano sobre
  `java.net.Socket` y `SSLSocket`: los paneles viajan entre las dos máquinas por el enlace
  con token, no sólo por el invento local del WebView. Y para fiarse del puente,
  `cort_tls.py` genera un par autofirmado con el `openssl` que ya esté instalado (RSA de
  2048 bits, 825 días, SAN para `localhost` y cada IP del equipo, modo 0600 desde el
  instante en que existe); el teléfono fija la huella SHA-256 del certificado (pinning) y
  no acepta cualquier autofirmado que se le ponga delante. **Es opcional:** `CORT_TLS=cert,clave`
  explícito manda, y `CORT_TLS_AUTO=1` usa el par si ya está generado. Sin eso, el enlace
  sigue en claro dentro del Wi-Fi de casa, como siempre.
- **El cerebro que se baja solo (F20e, `AutoCerebro.java` + `ServicioBajada.java`).** Al
  conectarse a internet, CORT puede bajar el primer modelo del catálogo que pase la puerta
  de RAM y no esté ya en disco —hoy el 0,5B q2_K de 415 182 688 B— con la misma bajada de
  siempre (`Range`, `.part`, SHA-256 al terminar) pero dentro de un servicio en primer plano
  que sobrevive a que se cierre la ventana. **El interruptor viene apagado por defecto:**
  a los ~40 KB/s de la casa son casi tres horas de bajada continua, y el costo está escrito
  junto al interruptor. Si ningún modelo cabe holgado, no baja nada y dice por qué.
- **Carácter dicho en un archivo (F20d, `Consticion.java`).** La personalidad de CORT vive
  en `assets/consticion.json`, no escrita en Java: cambiar el tono no cuesta una corrida de
  compilación, y el JSON lo valida la suite en segundos.
- **Investigar con el origen dicho (F20c, `Investigacion.java`).** «Investiga» y «analiza»
  consultan dos fuentes públicas y las nombran en la respuesta: Wikipedia en español
  (`es.wikipedia.org/w/api.php`) y DuckDuckGo Instant Answer (`api.duckduckgo.com`). Sin
  buscador de pago y sin clave que guardar; si las dos callan, la respuesta lo dice en vez
  de inventar.
- **Los sensores que este teléfono tiene, no los del folleto (F19e, `Sensores.java`).** Se
  pregunta al `SensorManager` y se lista lo que contestó: un sensor que se anuncia y no
  existe es una respuesta mentirosa, y el Galaxy A16 no es el teléfono de al lado.
- **La RAM dicha en MB, en todas partes (P0-1 de la auditoría).** La cabecera del cerebro
  enseñaba bytes crudos donde el cuerpo hablaba de megas, y cinco sitios más comparaban
  bytes contra umbrales en MB (entre ellos la decisión de FPS del orbe). Ahora `Nexo.java`
  convierte en cada cuadro: `ram_disponible_mb`, `ram_libre_mb`, la puerta del perfil y la
  iniciativa dicen el mismo número que la pantalla «El aparato, medido».
- **Un cerebro que sí cabe en el A16 (P0-2).** La puerta vieja pedía el **doble** del
  archivo en RAM libre: con ~650 MB libres reales, ningún modelo pasaba y el teléfono
  contestaba «946 MB» a todo. La regla nueva es medida, no castigo: **cabe holgado** si la
  RAM libre supera el archivo **más 200 MB de reserva de contexto**; **se puede intentar**
  con la mitad de esa puerta (el motor ya usa `mmap`: el archivo se mapea y el sistema
  pagina lo que no cabe). El botón «Probar (mide tokens/s)» es una orden explícita: carga
  aunque vaya justo y la verdad la dicen el código de apertura y los tokens/s, no un
  bloqueo previo. Y el catálogo estrena primera entrada: **Qwen2.5-0.5B-Instruct q2_K,
  415 182 688 B** (SHA-256 `9ee36184…f798cb8`, medido contra Hugging Face), contexto 1024,
  2 hilos: su puerta holgada son 596 MB, así que en el A16 con ~650 MB libres **cabe**.

### Lo que ya venía y sigue puesto

- **El teléfono abre la misma interfaz que el portátil (F19).** El APK empaqueta los mismos
  archivos de `cort-web/` en `assets/web/` y los abre en su propio `WebView`: no es un
  parecido, son los mismos bytes, y la auditoría adjunta los lista uno por uno —
  **{{CARA}}**, contados sobre el APK que te estás bajando. Donde no hay servidor WebSocket,
  lo hace Java: `cort-android.js` sustituye `window.WebSocket` y cada cuadro viaja por el
  puente nativo hasta `Nexo.java`, que atiende el contrato cuadro por cuadro con datos del
  propio aparato. Lo que en el teléfono no existe **no se simula**: sale con `puente_aviso`,
  nombre del panel, el motivo concreto y lo que hace falta para tenerlo.
- **Se enlaza con la PC leyendo un QR (F14b)** o pegando la línea con su `?token=`. El
  decodificador es zxing core 3.5.3 (Apache-2.0), fijado por SHA-256 en `deps.txt`; ningún
  fotograma se guarda. **La memoria del teléfono habla con la de la PC (F14a):**
  `GET`/`POST /memoria/puente` detrás del token, con topes escritos (300 caracteres por
  fila, 500 filas, 262 144 bytes).
- **Hablarle a la PC y oírla por el auricular (F16).** Se mantiene pulsado, se habla, se
  suelta: la grabación viaja a `POST /parlamento`, el oído de la PC la convierte, y la voz
  sintetizada vuelve para sonar en el auricular de la oreja. El auricular no traga arengas:
  dice la primera frase (techo de 90 caracteres) y el texto entero queda en pantalla. El
  dictado no se guarda en ninguna parte.
- **Te lee en cualquier aplicación (U2, `Lectura.java`).** «Leer con CORT» en el menú de
  texto seleccionado: trocea por frases, tres pasos de lectura, botones Parar y Copiar, y
  el texto se queda en memoria. **Sabe si llevas audífonos (`Audifonos.java`):** con
  auriculares puestos la voz va a ellos; sin nada, al auricular de llamada; y si te los
  quitas mientras habla, se calla. **Saluda al encender (`Arranque.java`)** —con el límite
  escrito de que One UI puede cerrarlo si CORT sigue optimizado por batería— y hay
  **baldosa en el panel rápido (`Baldosa.java`)**.
- **El bolsillo: qué le debe la PC (F17, `Bolsillo.java`).** Recordatorios pendientes con
  los minutos que faltan, vencidos, compra, notas y estado de la máquina, pedidos a
  `GET /bolsillo` con el token. Si la PC está apagada dice **no contestó** y no inventa.
- **Un cerebro GGUF dentro del teléfono (U1, `libcortmotor.so`).** llama.cpp b12121 cruzado
  con el NDK r26d, enlazado estático y autocontenido; el pegamento JNI usa sólo la API
  pública de `llama.h` y el workflow comprueba que los 11 símbolos nativos estén exportados.
  Licencia MIT. **Ningún modelo va dentro del APK.**
- **Almacén de cerebros (U1, `Cerebros.java`):** ahora **cuatro** Qwen2.5-Instruct con peso
  y SHA-256 medidos contra Hugging Face, ordenados de menor a mayor: 0,5B q2_K
  (415 182 688 B), 0,5B q4_K_M (491 400 032 B), 1,5B q2_k (752 880 160 B) y 1,5B q4_K_M
  (1 117 320 736 B). Bajada con reanudación (`Range`) y suma del archivo entero al terminar:
  si no cuadra, se borra y se dice, porque un GGUF a medias abre y contesta basura.
- **Cómo decide a quién preguntar (U1).** Las 33 reglas exactas van delante (contestan en
  milisegundos). Lo que no esté en la tabla va al cerebro del teléfono si el modo y la RAM
  lo permiten, y si no a la PC o a la nube. Tres modos: **Automático · Teléfono · PC o nube**.
  La puerta es la nueva: archivo más 200 MB de reserva para ir holgado, la mitad para
  intentarlo con `mmap`, y la pantalla dice los megas que hay ahora.
- **«El aparato, medido» (U1, `Equipo.java`).** RAM total y libre ahora, núcleos, ABIs,
  almacenamiento, pila y motor de voz, con la misma puerta nueva escrita en números.
  Todo seleccionable para copiar; nada se envía a la PC.
- **Sigue funcionando sola, sin portátil encendido:** orbe y registro nativos, 33 reglas de
  frases, 15 manos locales, memoria SQLite propia y dictado dentro del aparato con Vosk
  (el modelo español `vosk-model-small-es-0.42` **ya viene dentro del APK**, así que oye
  nada más instalarlo), sin red y sin servicios de Google. La voz es `es-ES`.

## Los números, medidos sobre el archivo que te estás bajando

| | antes (`cort-v0.11.0`, la ventana sin oído) | ahora |
|---|---|---|
| peso | 16 873 B | **{{PESO}} B = {{MB}} MB** |
| oído | el del aparato, por internet | {{OIDO}} — con el modelo de {{MODEL}} B dentro |
| cara | botones nativos | **la misma interfaz del portátil**: {{CARA}} |
| arquitecturas | la que hubiera | **{{ABIS}}** |
| cerebro | 33 reglas y la nube | **motor GGUF dentro del teléfono** + cuatro modelos descargables (ninguno dentro del APK) |
| enlaces | pegar la IP a mano | QR con la cámara **o** pegar la línea, con token; WebSocket real y TLS opcional con pinning |
| dependencias | ninguna | Vosk 0.3.75 (Apache-2.0) · JNA 5.14.0 (LGPL-2.1+) · modelo español Apache-2.0 · zxing core 3.5.3 (Apache-2.0) · llama.cpp b12121 (MIT) · three.js (MIT, con el aviso de derechos dentro del propio módulo) · Leaflet 1.9.4 (BSD-3-Clause) · Qwen2.5 GGUF (Apache-2.0, se bajan aparte) |

**Firmado:** {{LLAVE}} — `versionCode {{CODE}}`, huella del certificado `{{HUELLA}}…` (la misma
de las versiones anteriores, así que se instala encima: no hace falta desinstalar).

`auditoria.txt` (adjunto) es el desglose entrada por entrada, sacado del propio APK. El peso
y la estructura siguen las tres decisiones de `cort-v0.17.x`, que no se tocan:

* **El modelo de español ({{MODEL}} B) viene dentro del APK** para que el teléfono oiga nada
  más instalar; Almacén sigue sabiendo bajarlo (`assets/oido.json`) y `Motor.java` mira
  primero el archivo del almacén para no desarmar el del APK dos veces.
* **Las dos arquitecturas dentro: `arm64-v8a` y `armeabi-v7a`** (las que realmente viajaron
  son las que lista la tabla, leídas del APK). La dueña pidió el peso con sus palabras:
  *«tiene que pesar más, no importa»*.
* **Las `.so` viajan comprimidas** (`extractNativeLibs="true"`): `libcortmotor.so` sale con
  deflate —de 56 508 296 B a 14 265 297 B dentro del APK— en vez de byte por byte.

El antecedente es la tarde del 2026-11-05: el APK de 162 817 475 bytes se cortó al bajarlo
en esta casa (~40 KB/s) y Samsung dijo «aplicación no instalada». Con el peso de esta
release delante, si la bajada se corta, se reanuda con el `curl -C -` de abajo, o se compila
el paquete de una sola ABI con `CORT_ABIS="arm64-v8a"`.

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
micrófono; sin él la cara sirve igual, sólo faltan el dictado y la escucha, y la fila del
micrófono lo dice. Pide cámara **sólo** si pulsas «Escanear el QR». Para el «oye CORT» en
segundo plano: abre CORT o toca la baldosa, concede micrófono y deja el aviso en la bandeja;
si One UI cierra CORT, el botón «Que el teléfono no cierre CORT» abre el ajuste de batería
con esta app ya escrita. Para que lea y escriba en otras apps, enciende el servicio de
accesibilidad de CORT en los Ajustes de Android (la propia app te lleva a la pantalla exacta).

**El oído ya viene puesto.** El modelo español va dentro del APK y `Motor.java` lo
descomprime una sola vez a `filesDir/motor/` en el primer arranque; después deja un marcador
y no vuelve a tocarlo. La pantalla **Almacén → «Bajar el oído»** sigue existiendo para el
teléfono que ya lo tenía descargado.

**PC (Debian / Ubuntu / MX Linux XFCE).** Descarga el `Source code (tar.gz)` de esta release,
desempaqueta y:

```bash
cd CORT && ./scripts/instala_cort.sh        # y --red si además lo quieres ver desde el teléfono
```

El instalador comprueba `python3`/`venv`, crea `.venv`, instala sólo lo de
`requirements-cort.txt`, escribe el lanzador de menú y el arranque de XFCE, e imprime la
dirección del puente con su token y su QR. **No ejecuta `sudo` sin preguntarte con los paquetes
exactos delante y no baja instaladores de terceros a la shell.** Para el enlace cifrado:
`python3 cort-bridge/cort_tls.py` genera el par de la casa y la línea que exportar
(`CORT_TLS_AUTO=1`), sin instalar nada. `para_cort.sh` apaga y `desinstala_cort.sh` quita
lo instalado sin tocar tus datos.

**Windows.** Todavía no hay instalador probado: es la fase W1 y se dice aquí en vez de prometerlo.

## Lo que NO hace todavía, dicho con nombre

- **El «oye CORT» no sobrevive al reinicio ni a la pantalla apagada.** Android 14+ prohíbe
  arrancar el servicio de micrófono con `BOOT_COMPLETED`, y el servicio se detiene al apagarse
  la pantalla o a los cinco minutos de silencio. Tras reiniciar: abrir CORT o tocar la baldosa.
  Y One UI puede matar procesos en segundo plano si CORT sigue optimizado por batería.
- **La accesibilidad no se enciende sola.** Mientras la dueña no active el servicio en los
  Ajustes de Android, `Pantalla` no lee ni escribe en otras apps; el «Leer con CORT» del menú
  de texto seleccionado es la única vía sin ajuste.
- **El enlace por defecto no cifra.** El TLS de la casa existe (`cort_tls.py`) pero es
  opcional: sin `CORT_TLS` o `CORT_TLS_AUTO=1`, la llave viaja en el `?token=` dentro de tu
  red. Vale para tu casa; no lo abras a un Wi-Fi público ni a internet.
- **AutoCerebro viene apagado.** Casi tres horas de bajada a 40 KB/s no se hacen solas sin
  que la dueña lo sepa: el interruptor dice el costo y ella lo enciende.
- **Cuánto tarda el cerebro en el A16: sin medir.** La puerta nueva deja cargar el 0,5B q2_K
  (596 MB de puerta holgada frente a ~650 MB libres), pero los tokens/s reales sólo los puede
  dar el teléfono con «Probar (mide tokens/s)». El tope de tokens por vuelta y el botón
  «Interrumpir» existen precisamente porque esa cifra aún no está medida.
- **El parlamento necesita el puente renovado en la PC.** `/parlamento` se sirve desde el
  `cort_server.py` de esta versión: si el CORT del portátil sigue encendido de antes, la ruta
  contesta `404`. Reinicia CORT en la PC y ya oye.
- **Todavía no levanta la PC desde el móvil** (Wake-on-LAN dentro de tu Wi-Fi). El bolsillo ya
  lee lo pendiente; encenderla desde el teléfono es lo que sigue.
- **En el teléfono no corre Ollama, y no hace falta.** Lo que sí corre es `llama.cpp` con el
  GGUF que elijas (U1). Ninguna cifra de velocidad se escribe aquí hasta que el A16 la mida.
- **La cara del PC necesita el WebView del sistema.** Si falta o es muy viejo, `MainActivity`
  cae a la cara nativa de siempre (`Cara.java`) y lo dice en pantalla; actualizar «Android
  System WebView» devuelve la cara del PC.
- **Los paneles del portátil que no viajan al teléfono, y por qué.** VPN, domótica, impresión
  3D, Obsidian, juegos, Windows/winget, antivirus, Jarvis OS, actualización desde el repo,
  mirada por cámara… Cada cuadro que la cara pregunta y el teléfono no tiene sale con
  `puente_aviso`: nombre del panel, motivo concreto y qué hace falta. No se pinta un panel
  lleno de ceros.
- **La cámara del teléfono sólo lee el cuadro del enlace** y no guarda ningún fotograma.
- **Quedan restos de la plantilla francesa en lo hondo del bundle de React.** La cara se
  traduce al vuelo en el DOM (español por defecto), pero el fuente original aún tiene textos
  en francés que se limpian en la fase P1; lo que se ve en pantalla está en español.
- **Esta versión aún no se ha instalado físicamente en el A16.** La anterior (`cort-v0.17.2`)
  está instalada y funciona; lo medido en esta corrida es el compile, la firma, la estructura
  del APK y las {{CHECS}} comprobaciones de `scripts/prueba_apk.py`, que el propio workflow
  ejecuta antes de publicar. Cuánto tarda el modelo en cargar, cuánta RAM ocupa y cómo se ve
  la cara en tu pantalla lo saca el ensayo físico.

---
SHA-256 del APK publicado: `{{SHA}}`