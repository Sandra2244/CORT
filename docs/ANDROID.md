# CORT en el teléfono (Android) — qué es, qué necesita y qué no hace

**Autora:** Askher Vargas y Sandra Lopez · soporte: `Sandrasofialopezgomez3@gmail.com` ·
`Carlosa3325@gmail.com`. **Licencia:** MIT (ver `LICENSE`).

---

## 1. Qué es exactamente

**Una aplicación nativa que funciona sola.** Desde `cort-v0.12.0` el teléfono no es una
ventana abierta al puente de la PC: lleva dentro la cara (el orbe y el registro), el cerebro
de frases, las manos locales, su propia memoria SQLite y **su propio oído** (Vosk; desde
`cort-v0.17.1` el modelo español viaja dentro del APK, así que oye nada más instalar). Se
apaga el portátil y CORT sigue hablando, dictando, acordándose y obedeciendo.

Y desde `cort-v0.17.1` (F19) **la cara que se ve es la del portátil**: el mismo
`cort-web/index.html`, el mismo orbe de three.js y los mismos paneles, empaquetados dentro
del APK y abiertos en un `WebView` propio. La interfaz nativa (`Cara.java`) sigue ahí, como
respaldo si el WebView del sistema no arranca. El diagrama es ahora así:

```
teléfono (app nativa, Java, sin Gradle ni AndroidX)
   ├─ MainActivity   decide la cara: `assets/web/` en un WebView (F19) o `Cara.java` de respaldo
   ├─ Nexo.java      el puente: contesta el contrato del WebSocket cuadro por cuadro (F19c)
   ├─ Motor.java     Vosk dentro del aparato  → el audio NO sale del teléfono
   ├─ Voz.java       TextToSpeech (boca) + SpeechRecognizer (respaldo del oído)
   ├─ Cerebro/Acciones   33 reglas y 15 manos locales (linterna, hora, alarma, decir…)
   ├─ Recuerdos.java     SQLite propio (cort.db) — la memoria vive en el teléfono
   └─ Asistente/Sesiones/Reconocimiento   traje de asistente de Android
             │  (opcional, y se ve que es opcional)
             └─ http://IP_CASA:8766  ← la misma cara de la PC, si la PC está encendida
                      ws://IP_CASA:8765/ws  y  POST /mic (el teléfono también puede dictar al puente)
```

La sincronía de memoria con el portátil **sí la sirve ya esta rama** (F14a): el puente
monta `GET` y `POST /memoria/puente` en el puerto del core —`8765`— detrás de una llave que
se guarda en `~/.local/share/cort/enlace.json` con modo `0600`. El arranque de CORT imprime
la dirección completa, y `python3 cort-bridge/cort_enlace.py --qr` dibuja encima un cuadro
que se escanea con el teléfono; si se prefiere teclear, el plan B es pegar **esa línea
entera** (con su `?token=`) en la pantalla de enlace de la aplicación. El escáner de cámara
**ya está dentro del APK** desde F14b (`Escaner.java`, zxing core 3.5.3 fijado por SHA-256 en
`apps/android/deps.txt`): decodifica y tira, ningún fotograma se guarda. Lo que llega por el
puente son los recuerdos; las preferencias, la lista y las notas van en el siguiente viaje
(F14c).

Desde `cort-v0.15.1` (U2) el teléfono además **se integra en el sistema**, que es lo que la
dueña pidió con el ejemplo del iPhone:

```
Lectura.java    «Leer con CORT» en el menú de selección de CUALQUIER app (ACTION_PROCESS_TEXT
                + ACTION_SEND). Troza por frases, tres pasos, parar y copiar; el texto no se
                escribe en disco.
Audifonos.java  el sensor de salida (cable / Bluetooth / auricular del teléfono) con
                `getDevices` + `AudioDeviceCallback` + `ACTION_AUDIO_BECOMING_NOISY`.
                El parlamento y el lector preguntan aquí antes de abrir la boca, y si la
                dueña se quita los auriculares mientras habla, CORT se calla.
Arranque.java   el saludo al encender (`BOOT_COMPLETED`), dicho por la voz y escrito en una
                notificación sin sonido. Con el límite delante: One UI puede cerrar antes.
Baldosa.java    la baldosa del panel rápido (`TileService`), que abre la escucha de un toque.
Bolsillo.java   lo pendiente de la PC (F17): `GET /bolsillo` con recordatorios, vencidos,
                compra, notas y la máquina medida en /proc.
Equipo.java     el aparato dicho con números — la RAM libre de ESTE teléfono, que es la que
                decide si el cerebro local de U1 cabe. Nada de esto sale del aparato.
```

### La cara de la PC dentro del teléfono (F19)

La queja del 2026-11-05 vino con cuatro capturas del Galaxy A16 y una frase: «necesito que
sea la copia exacta de la versión de PC incluyendo sus funciones». El teléfono mostraba
`Cara.java` —botones hechos a mano— mientras el portátil mostraba `cort-web/index.html`. Son
tres piezas, y cada una se comprueba en `scripts/prueba_apk.py`:

1. **F19a — el empaquetado.** `apps/android/compilar.sh` copia `cort-web/` a
   `assets/web/` dentro del APK: `index.html`, `manifest.webmanifest`, `cort-sw.js`, el
   directorio `cort/` (mock, orbe, UI, estilos, el vendor de Leaflet), el `assets/` de React
   y CSS **sin los `*.orig`**, `iconos/` y `wallpapers/`. `demo/` y la documentación no van:
   la página no los pide. Si falta `index.html` el build **se cae** en vez de sacar un APK
   que muestre la cara nativa, y `auditoria.txt` lista la cara entrada por entrada sobre el
   archivo final (no sobre la carpeta de etapa: así se detecta un `-A` mal puesto en `aapt2`).
2. **F19b — el WebSocket que no existe.** La cara habla por `ws://<host>:8765/ws`; dentro del
   teléfono no hay nada escuchando, así que `apps/android/web/cort-android.js` sustituye
   `window.WebSocket` **antes** de que `cort-mock.js` lo guarde (línea 25 del mock; por eso el
   puente es el primer `<script>` que `Nexo.java` cose detrás de `<head>`). El sustituto abre
   `readyState` en el constructor —la interfaz compara `=== WebSocket.OPEN` y con 0 durante un
   tick tiraba el primer cuadro—, encola como máximo 64 mensajes para no perder lo que llega
   antes de suscribirse, y neutraliza `navigator.serviceWorker`, que en `file://` no registra
   nada y su fallo tapaba la cara entera. La vuelta es `window.__cortNative.emit(...)`.
3. **F19c — el contrato.** `Nexo.java` despacha por el `type` de cada cuadro, con datos del
   aparato: clima real (open-meteo; IP si no hay ciudad), `pc_estado`, temperatura de los
   sensores, apps instaladas, lista, notas, pendientes, volumen, brillo, micrófono, orbe y el
   cerebro GGUF. Tres reglas que costaron aprendizajes y están fijadas por comprobación:
   **`get_settings` no se responde desde Java** (un `settings_data` vacío borra los campos de
   Ajustes y deja `reminders` en cero — el mock lo contesta localmente en su línea 514);
   **un clima que falla no sale como `weather_panel`** (el lector del bundle se lee `ville`,
   `temperature`, `ressenti`… sin mirar `ok`, así que un panel a medias revienta la tarjeta:
   se dice en texto, como hace `cort_server.py`); y **lo no medido viaja como
   `JSONObject.NULL`**, no como `-1`, porque la cara muestra `?? "--"` y un `-1` se leería
   «-1 %».
4. **Lo que en el teléfono no hay no se simula.** `panelDe` es el equivalente android del
   `FALTA_EN_EL_PUENTE` de `cort_server.py`: cada cuadro sin atención sale con
   `puente_aviso` —panel, motivo concreto y qué hace falta—, y el resto de la cara lo pinta.
   Dos rótulos se apagan con la bandera `window.CORT_esAndroid`: el nombre del cerebro (en el
   teléfono no hay Ollama) y el botón de emparejar por QR, que sólo lo atiende `cort_server.py`.

Queda pendiente y tiene fase escrita: **F19d** (escuchar «oye CORT» en segundo plano con
Vosk dentro de un servicio, corte a los 5 min de silencio o al apagarse la pantalla) y
**F19e** (leer la pantalla de otras apps por accesibilidad, sensores restantes y que los
paneles que necesitan la PC viajen por el enlace con `PuenteWs.java`).

La aplicación es **híbrida de propósito**, y por eso hay dos instaladores distintos: el APK
del teléfono y el instalador de escritorio para Linux/Windows. Los dos hablan el mismo español
y compiten por la misma cara; ninguno necesita a la nube.

## 2. Por qué una APK y no la web instalable (PWA)

Medido, no opinado:

- El puente sirve la interfaz por **http** en la red local (no hay certificado).
- Chrome/WebView sólo dan `getUserMedia` (micrófono) y el service worker de instalación a
  **orígenes seguros**. `http://192.168.x.x` no lo es.
- Con `https` sí se podría (el puente ya acepta `CORT_TLS=certificado,clave`), pero un
  certificado válido exige un nombre de dominio público, y eso es sacar la red de tu casa a
  internet. No se hizo — y el TLS local con llave propia es la fase del enlace (F14/S3).

Desde F12 el motivo pesa menos (el teléfono ya no necesita la página para nada), pero la
razón sigue en pie para lo que sí cruza la red: el cliente nativo pide el permiso al sistema,
abre el micrófono él mismo y puede hablar con Vosk dentro del aparato.

## 3. Cómo se compila

**No se compila en esta máquina, y se dice por qué:** la Classmate tiene OpenJDK 21 sólo
*runtime* (`javac` no está), y no tiene Gradle, ni SDK de Android, ni `adb`. Prometer un APK
"hecho en casa" sería mentira. Se compila en GitHub Actions con el workflow
`.github/workflows/apk-movil.yml`, que corre `apps/android/compilar.sh`.

El método **es el mismo de siempre** —sin Gradle y sin AndroidX, con las herramientas que el
runner de Ubuntu trae preinstaladas:

1. `aapt2 compile` + `aapt2 link` sobre `AndroidManifest.xml`, `res/` y los `assets`
   montados, con `--min-sdk-version 26 --target-sdk-version 34` y el `versionCode` derivado
   de la versión (`0.12.0` → `1200`, que es lo que hace que Android lo tome como
   actualización);
2. `javac --release 11` contra `android.jar` **más** `classes.jar` de Vosk y de JNA;
3. `d8` para el dex (los `.jar` entran como programas, no como classpath), `zip` de las
   nativas, `zipalign -f -p 4` y `apksigner`;
4. peso en bytes, MB y **SHA-256** impresos, y si un paso falla su final sale como
   `::error::` **annotation del check-run**, que sí es pública (las logs de Actions de un
   repo privado no).

**Desde F12 este build sí descarga piezas de terceros**, y no "las que haya":
`apps/android/deps.txt` fija nombre, URL y SHA-256 de cada una (`vosk-android-0.3.75.aar`,
`jna-5.14.0.aar`, `vosk-model-small-es-0.42.zip`) y `compilar.sh` se cae si la suma no cuadra.
Las licencias, pieza por pieza, están en `apps/android/ACREDITACION.md`. `vendor/` está en
`.gitignore`: los ~90 MB del oído nunca entran al repositorio por descuido, y
`scripts/prueba_apk.py` lo comprueba mirando `git ls-files`.

**La firma — medido el 2026-11-04 en el run 41881069892.** El secreto `CORT_APK_KEYSTORE_B64`
**sí está montado** en el repo (subido el 2026-10-21 por la otra línea y compartido por las
dos), así que el APK salió con `llave: la del repo` y se instala encima del anterior sin
desinstalar. La huella del certificado es la misma que en `cort-v0.11.0`:
`faabef468f3ae04fdfab9659d6a051c453d6ded7b965468c9c3b85caffa31977` (SHA-256 del certificado;
es pública porque vive dentro del APK). Si algún día se quita el secreto, el script genera una
llave desechable y entonces sí hay que desinstalar; `firma.txt` y `auditoria.txt` de cada
release dicen en una línea en qué caso estás, en vez de esconderte eso en el log.

**Quién publica la release: el runner, no esta laptop.** Medido el 2026-11-04: con el APK ya
compilado, bajar los 56 MB del artefacto a la casa se cortó dos veces (`curl` código 28 y un
timeout del propio `gh`) y a ~40 KB/s cada viaje cuesta media hora. Así que el workflow crea la
release desde dentro de Actions con `gh release create`, y lo hace **sólo si la corrida recibió
`etiqueta`** (el botón «Run workflow» o un `push` con tag no la publican). Antes de publicar
ejecuta `scripts/prueba_apk.py` en el runner: si la suite cae, la release no se toca. Las notas
no se escriben a mano — se generan de `auditoria.txt`, `firma.txt` y el `stat` del archivo, así
que lo que lees en la página sale del APK de esa misma corrida. El APK se construye tras hacer
`git checkout --detach` al commit de la etiqueta, para que lo publicado salga del código que dice
salir y no de la punta de la rama.

**Peso: medido otra vez, y esta vez el peso era el problema.** La release `cort-v0.16.1` pesaba
**162 817 475 bytes = 155,27 MB**. La dueña lo bajó en su casa, el archivo llegó más corto de lo
que anuncia la release y Samsung dijo **«aplicación no instalada»**: ése es el mensaje que
Samsung saca con un APK truncado (y también con uno mal firmado, que no era el caso — la firma
`faabef46…1977` es la del repo desde `cort-v0.11.0`), así que la culpa no era del sistema ni de
Play Protect, sino de 163 MB a ~40 KB/s: 70 minutos de descarga, y en esta casa la luz se va.
`cort-v0.16.2` ataca el número, no el síntoma, y queda en
**17 982 662 bytes = 17,15 MB** (SHA-256 `665bfe42eefaf127e25a338349271b96038a59d7f029ef3f5283bccbf510e7af`,
run 42115030288, 17 entradas, `versionCode 1602`) — **9,05 veces menos**, y unos
**7 minutos** en la misma línea en vez de 70. Las tres palancas, cada una con su medida:

1. **Una sola arquitectura.** `CORT_ABIS` ahora vale `arm64-v8a` por defecto: fuera los
   46 695 488 bytes de `libcortmotor.so` en armeabi-v7a, que en esta casa no los usa nadie.
   Sigue compilándose para los dos con `CORT_ABIS="arm64-v8a armeabi-v7a"`.
2. **Las `.so` comprimidas** (`extractNativeLibs="true"` + `zip -9`): `libcortmotor.so` pasa de
   56 508 296 a **14 265 297** bytes dentro del APK, y `libvosk.so` de 10 042 800 a
   **3 253 940**. El instalador las saca a `/data/app/…/lib` al instalar. Lo que **no** se puede
   hacer es bajar `libcortmotor.so` después a la carpeta de datos de la app: Android 10+ (y este
   APK apunta al 34) se niega a cargar librerías nativas ejecutables desde ahí.
3. **El modelo de español fuera del APK** (39 817 833 bytes): se baja en el teléfono desde
   **Almacén → «Bajar el oído»**, con `Range`, `.part` y su SHA-256 verificada entera antes de
   descomprimir. La ficha (`assets/oido.json`) lleva la URL, el peso y la misma suma fijada en
   `deps.txt`, y `scripts/prueba_apk.py` no deja que las dos se separen.

`classes.dex` se queda en 829 588 bytes: el código nunca fue lo gordo. La anterior
`cort-v0.15.1` pesaba **59 581 673 bytes = 56,82 MB** sin motor y la `cort-v0.11.0`
**16 873 bytes**. Ningún GGUF viaja en el APK — el cerebro de 752 880 160 bytes se baja en el
almacén, y ahora también el oído.

> **Por qué la suma puede cambiar sin que cambie el APK.** El `zip` del empaquetado guarda la
> hora en las entradas de `META-INF` y de las `.so`, así que dos corridas del mismo código dan
> archivos **del mismo tamaño pero de suma distinta**. La suma que vale es la del `.sha256` que
> vive en la release, porque se publicó al pie del archivo que descargas; cualquier otro número
> que este documento cite es sólo la foto de una corrida.

Lo que hay dentro, sacado del `auditoria.txt` que la release `cort-v0.16.2` adjunta (peso real
del archivo y peso que ocupa dentro del APK):

| archivo dentro del APK | bytes reales | dentro del APK | qué es |
|---|---|---|---|
| `lib/arm64-v8a/libcortmotor.so` | 56 508 296 | 14 265 297 | el pegamento GGUF: llama.cpp b12121 + el envoltorio JNI, estático y autocontenido |
| `lib/arm64-v8a/libvosk.so` | 10 042 800 | 3 253 940 | el reconocedor español |
| `classes.dex` | 829 588 | — | las 28 clases Java de CORT |
| `lib/arm64-v8a/libjnidispatch.so` | 168 176 | 42 418 | el puente JNA que llama a Vosk |
| `assets/cerebros.json` | 1 891 | — | los tres GGUF ofrecidos, con peso y suma medidos |
| `assets/oido.json` | 867 | — | la ficha de la descarga del oído: URL, 39 817 833 bytes y su SHA-256 |
| `assets/habilidades.json` | 9 770 | — | las 33 reglas y las 15 manos del cerebro nativo |
| **17 entradas** | **67 583 790 descomprimido** | **17 982 662 el APK** | |

Lo que **ya no está** en esa lista es el modelo de español (39 817 833 bytes) y todo lo de
`armeabi-v7a`: se bajan o se compilan aparte.

**`cort-v0.17.1` devuelve dos de las tres palancas, y hay que decir por qué.** Preguntada la
dueña por el peso con el número delante, contestó *«tiene que pesar más, no importa»* y pidió
el modelo y las dos ABIs dentro:

* **El modelo de español vuelve a `assets/motor/`** (`CORT_OIDO_DENTRO=1` es el default; `=0`
  devuelve el paquete delgado). El motivo no es estética sino de arranque: la cara del PC tiene
  que oír desde el primer uso, y un teléfono que abre su interfaz y dicta por internet —porque
  alguien no pulsó «Bajar el oído»— es exactamente la queja que abrió esta fase. `Motor.java`
  mira primero el archivo del almacén (le comprueba la suma y no desarma el del APK otra vez),
  así que el que ya lo tenía bajado no paga dos veces.
* **Las dos ABIs dentro** (`arm64-v8a` y `armeabi-v7a`). Lo que hace pagable la segunda es la
  palanca que **no** se revoca: las `.so` comprimidas. Medido en la corrida 42115030288,
  `libcortmotor.so` pasa de 56 508 296 a 14 265 297 bytes dentro del APK, así que los
  46 695 488 bytes de armeabi-v7a entran como ~12 MB comprimidos, no como 46 MB.
* **La cara del PC** añade sus archivos (los lista `auditoria.txt` en el bloque
  «cara del PC», con su peso real y el que ocupa dentro del APK).

El peso resultante lo publica la release con el `stat` del archivo, y `apk-movil.yml` avisa por
encima de ~120 MB: la descarga de esta casa se cortó a los 162 817 475 bytes de `cort-v0.16.1`.
Si alguna vez vuelve a cortarse, `curl -C -` reanuda la bajada, y
`CORT_ABIS="arm64-v8a"` devuelve el paquete de una sola arquitectura.

Con `extractNativeLibs="true"` el instalador descomprime las `.so` a `/data/app/…/lib` antes de
cargarlas, así que lo que se exige es lo contrario de antes: que **sí** vayan comprimidas
(`zip -9`), y `auditoria.txt` lo comprueba entrada por entrada («deflate, ok»). `resources.arsc`
sigue **sin comprimir y alineado a 4 bytes**, que es lo que Android 11+ pide para leerlo con
`mmap`; si algo de esto se rompe, el fallo es `UnsatisfiedLinkError` en el arranque y CORT se
queda mudo — por eso la suite lo fija.

Descargar y comprobar desde fuera, sin confiar en este texto:

```bash
B=https://github.com/Sandra2244/CORT/releases/download/cort-v0.16.2
curl -sL -o CORT-movil.apk.sha256 $B/CORT-movil.apk.sha256   # 81 bytes, primero
curl -sL -C - -o CORT-movil.apk   $B/CORT-movil.apk          # -C -: si se corta, sigue
sha256sum -c CORT-movil.apk.sha256
```

El `-C -` no es adorno: es exactamente el fallo que tuvo la dueña con el APK de 155,27 MB.
El navegador de Samsung también reanuda descargas, pero si el archivo final no mide lo que
anuncia la release (`17 982 662` bytes en `cort-v0.16.2`) el instalador dirá «aplicación no
instalada» **antes** de mirar la firma. En el teléfono la misma reanudación la hace CORT con
el oído y con los GGUF (`.part` + `Range`), y en los tres casos la suma se comprueba entera.

> **Arreglo del 2026-11-04, dicho aquí porque le pasó a la dueña.** Hasta este commit el
> `.sha256` se anotaba con el nombre `build/CORT-movil.apk` (el path que usa el script), así
> que `sha256sum -c` respondía *«No existe el fichero o el directorio»* aunque la suma fuera
> correcta. Ahora se anota con el nombre desnudo, y `prueba_apk.py` lo vigila.

La comparación es contra el archivo `.sha256` de la propia release, no contra un número que
este documento repita: si alguien sustituyó el APK, la suma ya no cuadra y el chequeo falla.

Y hay una segunda comprobación que **no baja los 56 MB**: GitHub calcula él mismo el SHA-256 del
archivo que almacena y lo expone en la API. Si las dos sumas coinciden, la release es
autoconsistente (lo que promete el `.sha256` es lo que está guardado):

```bash
gh api repos/Sandra2244/CORT/releases/tags/cort-v0.13.0 \
  --jq '.assets[]|select(.name=="CORT-movil.apk")|.digest'
# sha256:d4de166aae7722c5ae9d1143cb05934a81fe9c2c01eebfc711d1700a7e4f08ab   ← medido hoy
```

Medido el 2026-11-04: esa suma es idéntica a la del `.sha256` publicado. Lo que este atajo
**no** prueba es que *tu* descarga lleguen intacta; para eso está el `sha256sum -c` de arriba.

## 4. Instalarla en el Galaxy A16

1. Bajar **`CORT-movil.apk`** (o `CORT-v0.12.0.apk`, como lo nombre la release) de la release
   en el teléfono y comprobar la suma con el comando de arriba. Android avisará de que la
   fuente no es conocida: **es verdad en el sentido de que no está en ninguna tienda** —el APK
   sale de tu propio repo, firmado con la llave del repo (apartado 3)—.
2. Abrir la aplicación. **Puede funcionar sin hacer nada más**: el orbe, el registro, el dictado
   y la memoria no preguntan por ninguna IP.
3. Pedirá permiso de **micrófono**. Sin él la cara funciona igual; sólo falta «● hablar».
4. La primera vez que se pulsa ● puede tardar: el modelo se descomprime de `assets` a los datos
   de la app (una sola vez, ~90 MB ocupados) y luego se carga. La cara dice en qué punto está
   («descomprimiendo el modelo», «cargando el modelo», «Vosk listo») en vez de fingir que ya
   está, y si el APK salió delgado o la descompresión falló, dicta por el motor del aparato y
   lo dice: la línea «oído: …» cambia sola.
5. **Opcional, para tener también la cara de la PC**: en el portátil,
   `~/Escritorio/CORT/scripts/instala_cort.sh --red` (o `CORT_BIND=0.0.0.0 .venv/bin/python -u
   cort-bridge/cort_server.py`), que imprime `http://192.168.x.x:8766/`. En el teléfono: Ajustes
   → pegar esa dirección. El teléfono escribe `:8766` si se olvida el puerto y **no exige
   ninguna llave**, porque el puente de esta rama todavía no la pide.

## 4.1 El almacén de cerebros (U1): bajar el cerebro después de instalar

Instalado CORT, el teléfono **no trae ningún modelo grande dentro** y no lo va a traer nunca:
752 880 160 bytes en el APK castigarían a quien lo instala por Wi-Fi. Lo que sí trae es el
motor (`libcortmotor.so`, llama.cpp b12121 cruzado con el NDK r26d en Actions) y una pantalla
que baja los cerebros y los comprueba.

Pasos en el teléfono:

1. **Almacén de cerebros (bajar y usar)** — el botón está en la pantalla de enlace, y el chip
   `◈ cerebro …` de la cara nativa abre la misma pantalla desde cualquier otra.
2. Elegir uno de los tres que ofrece `assets/cerebros.json` y tocar **Bajar**. Van a
   `Android/data/dev.sandra.cort.movil/files/modelos`, sin compresión, y se puede cerrar la
   app: si el Wi-Fi se corta, la fila dice «a medias: X de Y MB» y **Seguir** retoma donde
   estaba (`Range`), no desde cero.
3. Al terminar, CORT **vuelve a calcular la SHA-256 del archivo entero** y la compara con la
   del catálogo. Si no cuadra, borra y lo dice. Un GGUF a medias no falla al abrir: abre y
   contesta basura, y esa es la razón de la comprobación.
4. **Usar**. La fila cambia a «abierto: … · <backends> · ya se puede probar abajo».
5. Escribir la pregunta de prueba y tocar **Probar (mide tokens/s)**: abajo salen las
   palabras y, al final, la medida de esa vuelta (`tokens=…&prepar_ms=…&gen_ms=…`).

Los tres ofrecidos, con el peso **medido el 2026-11-05** contra el árbol público de Hugging
Face y su licencia leída en la propia API del repo (`license:apache-2.0` en las dos familias):

| cerebro | bytes | puerta de RAM (el doble del archivo) |
|---|---|---|
| `qwen2.5-0.5b-instruct-q4_k_m.gguf` | 491 400 032 | 983 MB libres |
| `qwen2.5-1.5b-instruct-q2_k.gguf` | 752 880 160 | 1 506 MB libres |
| `qwen2.5-1.5b-instruct-q4_k_m.gguf` | 1 117 320 736 | 2 235 MB libres |

Y el selector de arriba de la pantalla, que es la respuesta a «que funcione como asistente
completo e integrado en el teléfono»:

* **Automático** — piensa en el teléfono si el modelo cabe en la RAM libre de *este* momento;
  si no, usa la PC/nube. La puerta es la misma medida que imprime «El aparato, medido».
* **Teléfono** — sólo el GGUF. Si no cabe, la cara lo dice con los megas que faltan en vez de
  callarse.
* **PC o nube** — el GGUF no interviene.

Las 33 reglas de `assets/habilidades.json` siguen **delante** de todo esto y eso no cambia: son
exactas y contestan en milisegundos. El cerebro GGUF entra cuando la frase no está en la tabla,
antes de preguntar a la nube, y si tampoco hay respuesta la cara propone aprender.

Lo que no se puede prometer todavía, con nombre: **los tokens por segundo en el A16**. La
generación va limitada a 120 tokens por vuelta para que una respuesta lenta se corte sola, y el
botón **Interrumpir** corta cuando la dueña se cansa. La primera medida real es suya.

## 5. Lo que tarda, y qué se ha medido de verdad

| cosa | estado |
|---|---|
| el dictado viaja por la red de la casa y se transcribe en la Classmate (modelo de 58 MB) | medido con audio sintético y `nice -19`: **22,4 s** la primera vez (cargando) y **2,8 s** con el modelo en RAM para ~2 s de habla |
| **el dictado dentro del teléfono (Vosk local)** | **sin medir**: exige el A16 en la mano. La cara imprime el tiempo de cada dictado (`ultimoDictadoMs`) para sacarlo de ahí, y `Motor.java` sólo promete los números de los archivos (39,8 MB el modelo, que ahora se baja, y 10,0 MB la biblioteca) |
| transcripción hecha, la respuesta del puente con sus reglas | 3–4 ms |
| tiempo de carga del modelo en el teléfono y RAM que ocupa | sin medir, por lo mismo |
| **el cerebro GGUF dentro del teléfono (U1)** | **sin medir**: el motor se compila en el runner (`motor-local.yml`) y la cara lo carga con `System.loadLibrary`; el primer `tokens/s` real sale del botón «Probar (mide tokens/s)» del almacén, en el A16 |
| el modelo GGUF en sí | pesos y SHA-256 **medidos** el 2026-11-05 en Hugging Face (491 400 032 / 752 880 160 / 1 117 320 736 bytes) y verificados otra vez en el teléfono al terminar la descarga |

El cuello de botella del camino viejo era la CPU de 2 núcleos de la Classmate, no el Wi-Fi. El
camino nuevo no usa esa CPU: es el teléfono quien trabaja, así que se espera que sea más
rápido, y **eso es una expectativa, no una medida**, y se dice como tal hasta el ensayo físico.

## 6. Qué no hace todavía, dicho con nombre

- **El enlace no cifra: falta TLS.** Desde F14a la ruta `/memoria/puente` **sí** la sirve esta
  rama, pero detrás de un token que viaja en el `?token=` dentro de la red local. Vale para tu
  casa; no lo abras a un Wi‑Fi público ni a internet. TLS local con llave propia es lo que
  sigue (Fase S3).
- **Sólo viajan los recuerdos.** Preferencias, lista de tareas y notas ya están escritos en el
  acuerdo de `cort-bridge/cort_enlace.py` y entran en el siguiente viaje (F14c).
- **El cerebro grande no viaja en el APK, y ahora tiene camino** (U1, apartado 4.1): el motor
  `libcortmotor.so` lo compila Actions con el NDK y los GGUF se bajan desde el almacén con su
  SHA-256 comprobada. Del artefacto del motor al APK **sólo entra el pegamento** — medido en la
  corrida 42025488743: 56 508 296 bytes en arm64-v8a y 46 695 488 en armeabi-v7a — porque va
  enlazado estático y autocontenido; las otras ocho librerías del artefacto (`libllama`,
  `libggml`, `libggml-base`, `libggml-cpu` por ABI) ya van dentro y copiarlas sumaría ~105 MB
  sin dar ninguna función. Lo que sigue **sin medir** es lo que tarda y lo que ocupa en el A16 —
  de ahí el botón de prueba. Y una cosa que no se afirma: «Ollama en Android» no es el camino que
  CORT tomó; el que funciona es llama.cpp compilado a mano, medido en 177 s de runner para las
  dos ABIs.
- **No habla sola desde el bolsillo**: no hay *wake word* en segundo plano todavía, y es la
  fase **F19d** con sus decisiones ya tomadas (reconocer «oye CORT» / «hola CORT» con el mismo
  modelo español de Vosk que ya viaja en el APK, dentro de un servicio en primer plano con su
  notificación —sin el token delante, que nunca se escribe en una bandeja—, y corte a los 5
  minutos de silencio o al apagarse la pantalla). El ● se pulsa y la baldosa del panel rápido
  también; el traje de asistente de Android (`Asistente`/`Sesiones`/`Reconocimiento`) está
  declarado y enruta, pero activarlo como asistente del sistema es una prueba de la dueña en el
  aparato.
- **La cara del PC depende del WebView del sistema.** Si falta o es demasiado viejo y la
  página no arranca, `MainActivity` vuelve a `Cara.java` y lo dice: no se queda en blanco. Es
  el navegador que trae el aparato, no algo que CORT pueda empaquetar sin subir el peso a
  otra escala (y sin AndroidX).
- **Leer la pantalla de otras apps y los sensores que faltan son F19e.** «Leer con CORT» hoy
  funciona por la intención `ACTION_PROCESS_TEXT` de Android —lee lo que la dueña selecciona,
  y eso ya está publicado en U2—; lo que no existe todavía es el **servicio de accesibilidad**
  que lee la pantalla entera sin selección (`Pantalla.java` + `res/xml/accesibilidad.xml`), y
  los paneles que necesitan a la PC tampoco viajan por el enlace: falta `PuenteWs.java`, el
  cliente WebSocket mínimo con su `mobile_auth`.
- **La cámara del teléfono sólo lee el cuadro del enlace** (F14b): decodifica y tira, ningún
  fotograma se guarda en disco y el permiso sigue sin ser obligatorio. La mirada de gestos
  (S2) corre en el PC, con su cámara.
- **Nadie lo ha instalado todavía en el A16.** Lo medido hasta hoy: el compile, la firma y la
  auditoría en el runner (release `cort-v0.16.2`, run 42115030288, verde de punta a punta,
  17 982 662 bytes = 17,15 MB) y las **210 comprobaciones** de `scripts/prueba_apk.py` que
  **esa misma corrida** ejecutó. La estructura del APK está comprobada: `.so` comprimidas con
  `extractNativeLibs="true"`, `resources.arsc` suelto y alineado, `classes.dex` de 829 588 B con
  zxing, el parlamento y las pantallas de U2 dentro, la ficha `assets/oido.json` para bajar el
  oído, y `libcortmotor.so` de 56 508 296 B arm64 (14 265 297 comprimidos). La `cort-v0.16.1`,
  con sus 162 817 475 B y 189 comprobaciones, sigue publicada y es la que se cortó al bajarla. Lo que falta de medir es el
  aparato: cuánto tarda el modelo en cargarse, cuánta RAM ocupa, cuántos `tokens/s` da, cuánto tarda
  un dictado real, si el escáner lee la pantalla de la PC a un metro y si el auricular se oye — esas
  cinco son el ensayo físico, no esto. A las cinco de la lista hay que añadir las tres de U2, y son
  igual de físicas: **si «Leer con CORT» aparece de verdad en el menú de WhatsApp** (One UI recorta
  ese menú y no hay forma de comprobarlo desde el PC), **si el saludo al encender sobrevive a la
  gestión de batería de Samsung** (contando los reinicios que se prueben) y **por dónde suena
  realmente la voz con audífonos puestos** (el `AudioTrack` con `USAGE_MEDIA` frente al
  `MODE_IN_COMMUNICATION` que se usaba antes).

- **El parlamento (F16) está publicado** en la release `cort-v0.14.0` (run 41957330147, verde):
  botón «Hablar con la PC (voz)», `Parlamento.java` con su WAV armado en memoria y su
  reproducción por el auricular — el APK se compila en el runner, en esta laptop no hay `javac`
  del SDK. Medido del lado de la PC: 3 273 ms por vuelta con el modelo cargado y 9 267 ms en la
  primera. **Lo que falta es el ensayo físico en el A16** —el de las cinco de arriba—, no el compile.
  **No levanta la PC desde el móvil** (Wake-on-LAN): medido el 4/11/2026 sin privilegios, el
  puerto de red (r8169) no anunció «Supports Wake-on» y está sin cable, y el Wi-Fi (rtl8723be)
  no trae bloque WoWLAN en `iw phy0 info`; con un cable y el permiso de red se vuelve a
  comprobar, y mientras tanto el bolsillo pide la PC despierta. **Lo que sí hace desde
  `cort-v0.15.1` es mostrar las tareas pendientes del portátil** (`Bolsillo.java` contra
  `GET /bolsillo`). Tampoco llama por su cuenta: el teléfono siempre inicia la vuelta.


## 7. Dónde está cada cosa

```
apps/android/src/dev/sandra/cort/movil/   29 clases Java y 10 860 líneas (medido el 2026-11-05
                                          en esta rama; `cort-v0.16.2` tenía 28 y 8 622).
                                          Las que importan:
    Motor.java         Vosk: descomprime el modelo del APK una vez, o lo baja si falta
                       (Range + SHA-256), escucha, corta a los 20 s y mide cada dictado
    Nexo.java          F19c: el puente del `WebView`. Lee el `type` de cada cuadro de la cara
                       del PC y lo contesta con datos del teléfono; lo que no hay sale con
                       `puente_aviso` y su motivo (equivalente android de `FALTA_EN_EL_PUENTE`)
    Bajada.java        la descarga con `Range`, `.part` y SHA-256 que comparten el oído y los
                       GGUF; sin `DownloadManager`, porque el token no viaja en una notificación
    Voz.java           la boca (TextToSpeech, es-ES como la PC) y los dos oídos; encola los
                       trozos del lector, cambia de paso y calla cuando le dicen
    MainActivity.java  permiso, y decide la cara: `assets/web/` en un WebView o `Cara.java`
                       de respaldo (donde se pega la IP, opcional)
    Cara.java          el respaldo nativo: el orbe, el registro y la línea «oído: …»
    Cerebro/Acciones   33 reglas y 15 manos locales desde assets/habilidades.json
    Recuerdos.java     SQLite del teléfono (cort.db)
    Escaner.java       la cámara leyendo el QR del enlace: YUV -> luminancia -> zxing
    Puente/Sincroniza  la ida y vuelta con el portátil (/memoria/puente, con token)
    Parlamento.java    la llamada: mantén pulsado, WAV armado en memoria, y la voz de la PC
                       vuelve por la salida que diga los audífonos, sin escribir audio
    Lectura.java       «Leer con CORT» en el menú de selección de cualquier app (U2)
    Audifonos.java     el sensor de salida: cable, Bluetooth o el auricular del teléfono
    Arranque.java      el saludo al encender, por voz y por notificación (con su límite escrito)
    Baldosa.java       la baldosa del panel rápido, que abre la escucha de un toque
    Bolsillo.java      lo pendiente de la PC, leído por el enlace (`GET /bolsillo`)
    Equipo.java        el aparato medido: la RAM libre que decide si el cerebro local cabe
    CerebroLocal.java  el cerebro GGUF en Java: la puerta de RAM, el modo (auto/local/nube) y
                       los 11 nativos que llaman a libcortmotor.so
    Cerebros.java      el almacén: catálogo, descarga con `Range`, SHA-256 al terminar, abrir
                       y medir tokens/s
    jni/cort_motor.cpp 452 líneas de C++ con la API pública de llama.cpp (el otro lado de esos
                       11 nativos)
    Asistente/Sesiones/Reconocimiento   el traje de asistente de Android
apps/android/AndroidManifest.xml          permisos, icono, servicios, el lector, la baldosa y el receptor de arranque
apps/android/web/cort-android.js          F19b: el `WebSocket` falso que habla con `Nexo.java`, la cola de 64,
                                          el `serviceWorker` neutralizado y la bandera `CORT_esAndroid`
cort-web/                                 F19a: la cara del PC tal cual — el build la copia a `assets/web/` del APK,
                                          así que en el repo hay UNA sola copia y no se desdobla
apps/android/res/drawable/ic_cort_aviso.xml  la silueta del orbe para la barra de estado y la baldosa
apps/android/res/xml/asistente.xml        a dónde apunta el asistente del sistema
apps/android/assets/habilidades.json      la tabla de frases del cerebro nativo
apps/android/assets/cerebros.json         los tres GGUF ofrecidos, con su peso y su suma medidos
apps/android/deps.txt                     qué se baja y con qué SHA-256
apps/android/ACREDITACION.md              licencias pieza por pieza y qué NO va dentro
apps/android/compilar.sh                  aapt2 + javac + d8 + zip(-0) + zipalign(-p) + apksigner
.github/workflows/motor-local.yml         el motor llama.cpp/NDK, sus sumas y el gate de los 11 nativos
cort-bridge/cort_server.py                `POST /mic` (dictado suelto), `POST /parlamento`
                                          (la llamada: oído de la PC, voz de vuelta al oído)
                                          y `GET /bolsillo` (lo pendiente, con la máquina medida)
cort-bridge/cort_voz.py                   la voz de la PC: espeak-ng y Piper es_ES (1,90× / 2,55×)
scripts/prueba_apk.py                     comprobaciones sin red: manifiesto, Java, sums, guiones
                                          (corren en cada compilación de Actions; su número lo
                                          imprime la propia suite y la release lo copia)
.github/workflows/apk-movil.yml           la compilación y sus medidas
```

> **Ojo con el nombre, porque hay dos CORT en este repo.** La rama `main` lleva otra línea
> (la del cerebro en Java y su `apps/apk/compilar.sh`, con releases `v0.1…v0.17` publicadas en
> octubre). Esta carpeta `apps/android` es la línea del puente Python y la interfaz JARVIS
> rediseñada, que es la que corre en la PC de la casa y la que se etiqueta `cort-vX.Y.Z`.
> Desde F12 las dos se parecen más (esta rama también es nativa), pero **siguen siendo dos
> aplicaciones distintas**: paquetes distintos (`dev.sandra.cort` y `dev.sandra.cort.movil`),
> workflows distintos y ficheros distintos, así que en el teléfono conviven y no se pisan.
