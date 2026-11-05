# CORT en el teléfono (Android) — qué es, qué necesita y qué no hace

**Autora:** Askher Vargas y Sandra Lopez · soporte: `Sandrasofialopezgomez3@gmail.com` ·
`Carlosa3325@gmail.com`. **Licencia:** MIT (ver `LICENSE`).

---

## 1. Qué es exactamente

**Una aplicación nativa que funciona sola.** Desde `cort-v0.12.0` el teléfono no es una
ventana abierta al puente de la PC: lleva dentro la cara (el orbe y el registro), el cerebro
de frases, las manos locales, su propia memoria SQLite y **su propio oído** (Vosk con el
modelo español dentro del APK). Se apaga el portátil y CORT sigue hablando, dictando,
acordándose y obedeciendo.

```
teléfono (app nativa, Java, sin Gradle ni AndroidX)
   ├─ Motor.java   Vosk dentro del aparato  → el audio NO sale del teléfono
   ├─ Voz.java     TextToSpeech (boca) + SpeechRecognizer (respaldo del oído)
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

**Peso: esta vez medido y esta vez grande.** La release `cort-v0.15.1` pesa
**59 581 673 bytes = 56,82 MB** y su SHA-256 es la que publica su propio archivo
`CORT-movil.apk.sha256` (`03b001bdfbdd89f934dcfe5f7c2e131dc6d5e12cba92db5038c7e725b31e4741`,
run 41977159844). El anterior (`cort-v0.11.0`) pesaba
**16 873 bytes**: ×3 531, y la diferencia no es código, es el oído.

> **Por qué la suma puede cambiar sin que cambie el APK.** El `zip` del empaquetado guarda la
> hora en las entradas de `META-INF` y de las `.so`, así que dos corridas del mismo código dan
> archivos **del mismo tamaño pero de suma distinta**. La suma que vale es la del `.sha256` que
> vive en la release, porque se publicó al pie del archivo que descargas; cualquier otro número
> que este documento cite es sólo la foto de una corrida.

Lo que hay dentro, sacado del propio APK con `unzip -l` y no de este texto:

| archivo dentro del APK | bytes | qué es |
|---|---|---|
| `assets/motor/vosk-model-small-es-0.42.zip` | 39 817 833 | el modelo español, con su suma verificada dos veces |
| `lib/arm64-v8a/libvosk.so` | 10 042 800 | el reconocedor para los teléfonos modernos |
| `lib/armeabi-v7a/libvosk.so` | 8 985 628 | el mismo para teléfonos de 32 bits |
| `lib/arm64-v8a/libjnidispatch.so` | 168 176 | el puente JNA que llama a Vosk |
| `lib/armeabi-v7a/libjnidispatch.so` | 122 296 | idem, 32 bits |
| `classes.dex` | 294 056 | las 18 clases Java de CORT (5 119 líneas) |
| `assets/habilidades.json` | 9 770 | las 33 reglas y las 15 manos del cerebro nativo |
| **16 entradas, sin comprimir** | **59 458 359** | |

`extractNativeLibs="false"` exige dos cosas y `auditoria.txt` las comprueba una por una,
porque si falta una el fallo es `UnsatisfiedLinkError` en el arranque y CORT se queda mudo:
las `.so` van **almacenadas sin comprimir** (`compress_type 0`, medido sobre el APK del run) y
**alineadas a página** (`zipalign -c 4` → ok). El modelo también sale sin comprimir.

Descargar y comprobar desde fuera, sin confiar en este texto:

```bash
B=https://github.com/Sandra2244/CORT/releases/download/cort-v0.13.0
curl -sL -o CORT-movil.apk        $B/CORT-movil.apk
curl -sL -o CORT-movil.apk.sha256 $B/CORT-movil.apk.sha256
sha256sum -c CORT-movil.apk.sha256
```

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
| **el dictado dentro del teléfono (Vosk local)** | **sin medir**: exige el A16 en la mano. La cara imprime el tiempo de cada dictado (`ultimoDictadoMs`) para sacarlo de ahí, y `Motor.java` sólo promete los números de los archivos (39,8 MB el modelo, 10,0 MB la biblioteca) |
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
  SHA-256 comprobada. Lo que sigue **sin medir** es lo que tarda y lo que ocupa en el A16 — de
  ahí el botón de prueba. Y una cosa que no se afirma: «Ollama en Android» no es el camino que
  CORT tomó; el que funciona es llama.cpp compilado a mano, medido en 177 s de runner para las
  dos ABIs.
- **No habla sola desde el bolsillo**: no hay *wake word* en segundo plano. El ● se pulsa y la
  baldosa del panel rápido también; el traje de asistente de Android
  (`Asistente`/`Sesiones`/`Reconocimiento`) está declarado y enruta, pero activarlo como
  asistente del sistema es una prueba de la dueña en el aparato.
- **La cámara del teléfono sólo lee el cuadro del enlace** (F14b): decodifica y tira, ningún
  fotograma se guarda en disco y el permiso sigue sin ser obligatorio. La mirada de gestos
  (S2) corre en el PC, con su cámara.
- **Nadie lo ha instalado todavía en el A16.** Lo medido hasta hoy: el compile, la firma y la
  auditoría en el runner (release `cort-v0.15.1`, run 41977159844, verde, 59 581 673 bytes =
  56,82 MB) y las 159 comprobaciones de `scripts/prueba_apk.py` que **esa misma corrida** ejecutó.
  La estructura del APK está comprobada: `.so` sin comprimir y alineadas a página, `classes.dex` de
  798 160 B con zxing, el parlamento y las pantallas de U2 dentro, modelo de español de 39 817 833 B. Lo que falta de medir es el
  aparato: cuánto tarda el modelo en cargarse, cuánta RAM ocupa, cuánto tarda un dictado real,
  si el escáner lee la pantalla de la PC a un metro y si el auricular se oye — esas cinco son el
  ensayo físico, no esto. A las cinco de la lista hay que añadir las tres de U2, y son igual de
  físicas: **si «Leer con CORT» aparece de verdad en el menú de WhatsApp** (One UI recorta ese
  menú y no hay forma de comprobarlo desde el PC), **si el saludo al encender sobrevive a la
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
apps/android/src/dev/sandra/cort/movil/   28 clases Java, 8 622 líneas. Las que importan:
    Motor.java         Vosk dentro del APK: descomprime el modelo una vez, escucha, corta a
                       los 20 s, mide el dictado y no abre ninguna conexión
    Voz.java           la boca (TextToSpeech, es-ES como la PC) y los dos oídos; encola los
                       trozos del lector, cambia de paso y calla cuando le dicen
    MainActivity.java  permiso, cara y ajustes (donde se pega la IP, opcional)
    Cara.java          el orbe, el registro y la línea «oído: …»
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
