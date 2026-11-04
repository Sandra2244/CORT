# CORT {{VERSION}} — el teléfono oye, recuerda y ya se enlaza con la PC

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
| enlaces | pegar la IP a mano | QR con la cámara **o** pegar la línea, con token |
| dependencias | ninguna | Vosk 0.3.75 (Apache-2.0) · JNA 5.14.0 (LGPL-2.1+) · modelo Apache-2.0 · zxing core 3.5.3 (Apache-2.0) |

**Firmado:** {{LLAVE}} — `versionCode {{CODE}}`, huella del certificado `{{HUELLA}}…` (la misma
de las versiones anteriores, así que se instala encima: no hace falta desinstalar).

`auditoria.txt` (adjunto) es el desglose entrada por entrada, sacado del propio APK: modelo
**{{MODEL}} B**, `libvosk.so` 10 042 800 B (arm64) y 8 985 628 B (armeabi-v7a), con las
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
micrófono (sin él la cara sirve igual, sólo falta «● hablar») y permiso de cámara sólo si
pulsas «Escanear el QR». El primer dictado puede tardar: el modelo se descomprime una sola vez
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
