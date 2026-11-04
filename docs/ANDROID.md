# CORT en el teléfono (Android) — qué es, qué necesita y qué no hace

**Autora:** Askher Vargas y Sandra Lopez · soporte: `Sandrasofialopezgomez3@gmail.com` ·
`Carlosa3325@gmail.com`. **Licencia:** MIT (ver `LICENSE`).

---

## 1. Qué es exactamente

Una aplicación que abre la interfaz de CORT **corriendo en tu PC de la casa**. No hay
servidor en internet, no hay cuenta, no hay nube: el teléfono es una ventana y un micrófono,
y el puente vive en la Classmate.

```
teléfono (WebView + botón ● hablar)
   │  http://IP_CASA:8766      ← la interfaz
   ├─ ws://IP_CASA:8765/ws      ← las órdenes y las respuestas
   └─ POST /mic  (WAV 16 kHz)   ← lo que tú digas, sólo mientras pulsas
             ↓
        el puente de la PC: reglas locales → Ollama si cabe → reja → acción → verificación
```

Todo lo que CORT sabe de ti (`memoria.json`, notas, lista) sigue estando en el PC. Si apagas
la PC, el teléfono no sabe nada: no hay copia en el teléfono.

## 2. Por qué una APK y no la web instalable (PWA)

Medido, no opinado:

- El puente sirve la interfaz por **http** en la red local (no hay certificado).
- Chrome/WebView sólo dan `getUserMedia` (micrófono) y el service worker de instalación a
  **orígenes seguros**. `http://192.168.x.x` no lo es.
- Con `https` sí se podría (el puente ya acepta `CORT_TLS=certificado,clave`), pero un
  certificado válido exige un nombre de dominio público, y eso es sacar la red de tu casa a
  internet. No se hizo.

Así que el cliente nativo resuelve las dos cosas: instala la interfaz sin necesitar service
worker y **graba el audio él mismo**, con el permiso del sistema, y se lo manda al puente.

## 3. Cómo se compila

**No se compila en esta máquina, y se dice por qué:** la Classmate tiene OpenJDK 21 sólo
*runtime* (`javac` no está), y no tiene Gradle, ni SDK de Android, ni `adb`. Prometer un APK
"hecho en casa" sería mentira. Se compila en GitHub Actions con el workflow
`.github/workflows/apk-movil.yml`, que corre `apps/android/compilar.sh`.

El método es el que ya está probado en la otra línea del repo (la de `main`, que publica
`CORT-v0.17.0.apk` desde octubre): **sin Gradle y sin AndroidX**, con las cuatro herramientas
que el runner de Ubuntu trae preinstaladas —

1. `aapt2 compile` + `aapt2 link` sobre `AndroidManifest.xml` y `res/`, con
   `--min-sdk-version 26 --target-sdk-version 34` y el `versionCode` derivado de la versión
   (`0.11.0` → `1100`, que es lo que hace que Android lo tome como actualización);
2. `javac --release 11` contra `android.jar` (la combinación `-source/-target` +
   `-bootclasspath` está prohibida desde target 9);
3. `d8` para el dex, `zipalign` y `apksigner`;
4. peso en bytes, MB y **SHA-256** impresos en el log, y si un paso falla su final sale como
   `::error::` **annotation del check-run**, que sí es pública (las logs de Actions de un
   repo privado no).

El proyecto **no declara ninguna dependencia externa**: sólo `android.*` y `org.json`, que
vienen con el SDK. No hay nada de terceros que pueda cambiar después de publicado.

**La firma — medido el 2026-11-04 en el run 41787218390.** El secreto `CORT_APK_KEYSTORE_B64`
**sí está montado** en el repo (subido el 2026-10-21 por la otra línea y compartido por las
dos), así que `compilar.sh` firmó con la llave de la autora y **el APK se instala encima del
anterior sin desinstalar**. El log lo dice él mismo: `llave: la del repo`. La huella del
certificado quedó publicada en `CORT-v0.11.0-firma.txt`: `faabef468f3ae04fdfab9659d6a051c453d6ded7b965468c9c3b85caffa31977`
(SHA-256 del certificado, información pública porque vive dentro del APK). Si algún día se
quita el secreto, el script vuelve a generar una llave desechable y entonces sí hay que
desinstalar la versión anterior; el propio `firma.txt` de cada release dice en una línea en
qué caso estás, en vez de esconderse en el log.

**Peso y comprobación.** El APK publicado pesa **16 873 bytes (0,02 MB)** y su SHA-256 es
`bc384b621439e9f16ccaa3d55a1f8e67ab6664d3f9ea05c15a9ee7f71f8f4012`; dentro van sólo
`AndroidManifest.xml`, el vector del orbe, `resources.arsc`, `classes.dex` (15 120 bytes) y
el bloque `META-INF` de la firma. La compilación completa tardó **22–25 s** en el runner
(`ubuntu-24.04`, build-tools 37.0.0, platform android-37.2) y el `versionCode` derivado de
`0.11.0` salió como `1100`, que es lo que Android usa para decidir si es actualización.
Descargar y comprobar desde fuera, sin confiar en este texto:

```bash
B=https://github.com/Sandra2244/CORT/releases/download/cort-v0.11.0
curl -sL -o CORT-v0.11.0.apk      $B/CORT-v0.11.0.apk
curl -sL -o CORT-v0.11.0.apk.sha256 $B/CORT-v0.11.0.apk.sha256
sha256sum -c CORT-v0.11.0.apk.sha256
```

La comparación es contra el archivo `.sha256` de la propia release, no contra un número que
este documento repita: si alguien sustituyó el APK, la suma ya no cuadra y el chequeo falla.

## 4. Instalarla en el Galaxy A16

1. **En la PC**, abrir el puente a la red local (una vez):
   ```bash
   ~/Escritorio/CORT/scripts/instala_cort.sh --red
   # o sin reinstalar:
   cd ~/Escritorio/CORT && CORT_BIND=0.0.0.0 .venv/bin/python -u cort-bridge/cort_server.py
   ```
   El puente imprime su dirección: `a la red local: http://192.168.x.x:8766/`. Apunta esa IP.
2. Bajar **`CORT-v0.11.0.apk`** de la release en el teléfono. Android avisará de que la fuente
   no es conocida: **es verdad en el sentido de que no está en ninguna tienda** —el APK sale de
   tu propio repo, firmado con la llave del repo (apartado 3)—. Acepta sólo si el archivo viene
   de ahí y **compara el SHA-256** con el `.sha256` que publica la misma release antes de abrirlo.
3. Abrir la aplicación. La primera vez pregunta dónde está CORT: escribe la dirección del
   paso 1 (`http://192.168.x.x:8766/index.html`). Se guarda en el teléfono.
4. Pedirá permiso de **micrófono**. Sin él la interfaz funciona igual; sólo falta «● hablar».

## 5. El botón «● hablar», y por qué tarda lo que tarda

Mantén y suelta no: **pulsa una vez para empezar, otra para terminar** (así se puede usar
con el pulgar y no depende de mantener la presión, que en pantalla táctil es lo que se cae).
Hasta 20 segundos; si te pasas, corta y sube lo grabado.

Números medidos con `scripts/prueba_mic_telefono.py` (audio sintético, sin teléfono de por
medio, `nice -19` en la Classmate):

| estado | round trip |
|---|---|
| primera subida (Vosk cargando el modelo de 58 MB) | 22,4 s |
| con el modelo ya en RAM | 2,8 s para ~2 s de habla |

Eso es la transcripción; después el puente contesta con sus reglas en 3–4 ms. **El cuello de
botella es esta CPU de 2 núcleos, no el teléfono ni el Wi-Fi.** Con el cerebro encendido
(Ollama) habría que sumarle su tiempo, y aquí no cabe: se dice con la cifra, no se esconde.

## 6. Qué no hace todavía, dicho con nombre

- **No hay emparejamiento ni clave** (fase S3). Quien esté en tu Wi‑Fi y sepa la IP puede
  abrir la misma página y darle órdenes al puente. Con `--red` eso es real: es la comodidad
  de usarlo desde la cama a cambio de la red abierta de tu casa. La puerta de verdad es
  token + TLS, y está pendiente.
- **No habla por el altavoz del teléfono**: CORT sintetiza en la PC, y en esta laptop no
  hay altavoz físico (`auto_null`), así que el audio sale por donde salga en el PC
  (HDMI o dongle USB). El micrófono del teléfono sí entra.
- **No hay notificaciones ni "ok CORT" en segundo plano.** Sin servicio que escuche
  siempre, la app hace de escucha mientras esté abierta.
- **La cámara del teléfono no se usa.** La mirada (S2) corre en el PC con su cámara.
- **Nadie la ha instalado todavía en el A16.** Lo medido es el compile+firma en el runner y la
  ruta `/mic` con audio sintético (7/7); el trayecto completo audio-real-del-teléfono → Vosk →
  respuesta sigue pendiente de su prueba física, y ahí se verá si el botón, el permiso y la
  dirección del puente se comportan en la mano y no en la prueba.

## 7. Dónde está cada cosa

```
apps/android/src/dev/sandra/cort/movil/MainActivity.java   WebView, ajuste de
    dirección, botón de habla, WAV y subida a /mic
apps/android/AndroidManifest.xml                           dos permisos: INTERNET
    y RECORD_AUDIO; `usesCleartextTraffic` para http en la red de casa
apps/android/res/                                          icono vectorial, colores y rótulo
apps/android/compilar.sh                                   aapt2 + javac + d8 + zipalign + apksigner
cort-bridge/cort_server.py                                 ruta `POST /mic` (recibe, transcribe,
    y borra el WAV)
.github/workflows/apk-movil.yml                            la compilación y sus medidas
```

> **Ojo con el nombre, porque hay dos CORT en este repo.** La rama `main` lleva otra línea
> (la del cerebro en Java y su `apps/apk/compilar.sh`, con releases `v0.1…v0.17` y `v0.2.x-demo`
> publicadas en octubre). Esta carpeta `apps/android` es la línea del puente Python y la interfaz
> JARVIS rediseñada, que es la que corre en la PC de la casa y la que se etiqueta `cort-vX.Y.Z`.
> Los dos APK se llaman distinto (`CORT.apk` y `CORT-v0.11.0.apk`), se compilan con workflows
> distintos para no pisarse y **tienen paquetes distintos** (`dev.sandra.cort` y
> `dev.sandra.cort.movil`), así que en el teléfono conviven como dos aplicaciones separadas y no
> se actualiza una por encima de la otra.
