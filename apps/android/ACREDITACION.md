# De dónde sale cada pieza de este APK

Lo que viaja dentro de `CORT-movil.apk`, con su licencia **leída antes de usarla**
y no supuesta. La regla de la casa: un archivo ajeno se baja, se lee y entonces
se usa; y si trae una suma publicada, esa suma se fija en `deps.txt` para que el
build se caiga el día que el archivo cambie sin que nadie avise.

| Pieza | Qué hace en CORT | Versión | Licencia (dónde está escrita) | Suma fijada |
|---|---|---|---|---|
| `libvosk.so` (AAR `com.alphacephei:vosk-android`) | El oído: convierte el habla en texto **dentro del teléfono**, sin red. | 0.3.75 | Apache-2.0, declarada en el POM publicado (`vosk-android-0.3.75.pom`, nodo `<licenses>`). | `ab2f8b91…c4adfad` |
| `libjnidispatch.so` + `classes.jar` (AAR `net.java.dev.jna:jna`) | El puente que llama a la biblioteca nativa desde Java; es lo que usa Vosk. | 5.14.0 | LGPL-2.1-or-later, declarada en el POM publicado (`jna-5.14.0.pom`). Se enlaza como biblioteca dinámica estándar: el código de CORT no modifica ni redistribuye fuentes de JNA. | `81a8b9af…dfab380` (comprobada además contra el `.aar.sha1` que publica Maven Central) |
| `vosk-model-small-es-0.42.zip` (**no viaja en el APK**; se baja desde Almacén) | El modelo de español: 39 817 833 bytes. El teléfono lo descarga una vez y le comprueba esta misma suma antes de montarlo; dentro del APK sólo viaja su ficha (`assets/oido.json`, 867 B). | 0.42 | Apache-2.0, en la fila del modelo de la lista oficial de modelos de Alpha Cephei (`alphacephei.com/vosk/models`), que también publica su precisión: 16,02 % de error de palabra en *cv test*, 16,72 % en *mtedx test* y 11,21 % en *mls*. **Cifras del fabricante, no medidas por nosotras.** | `09b23988…c6511f` |
| `libcortmotor.so` (compilada en Actions; se empaqueta **sólo arm64-v8a** y comprimida) | El cerebro: llama.cpp cruzado con el NDK de Google, con el pegamento JNI de CORT (`apps/android/jni/cort_motor.cpp`) enlazado **estático y autocontenido** dentro. | llama.cpp b12121 · NDK r26d | MIT, declarada en el propio `LICENSE` del fuente que se baja y se verifica por SHA-256 en `motor-local.yml` (medido el 2026-11-05 contra la API de GitHub: `spdx_id: MIT` de `ggml-org/llama.cpp`). El pegamento JNI es autoría nuestra y usa sólo la API pública de `llama.h`. | fuente fijado: `0b6fbcaa…` (el tarball completo, en `motor-local.yml`) |
| `qwen2.5-*-instruct-*.gguf` (**no viaja en el APK**) | Los cerebros que la dueña baja desde el almacén: 0,5B q4_K_M (491 400 032 B), 1,5B q2_k (752 880 160 B) y 1,5B q4_K_M (1 117 320 736 B). | Qwen2.5-Instruct | Apache-2.0, leída el 2026-11-05 en la API de Hugging Face de `Qwen/Qwen2.5-0.5B-Instruct-GGUF` y `Qwen/Qwen2.5-1.5B-Instruct-GGUF` (las dos con la etiqueta `license:apache-2.0`). Cada archivo se vuelve a sumar en el teléfono y se tira si su SHA-256 no es la fijada en `assets/cerebros.json`. | las tres sumas, en `assets/cerebros.json`, medidas contra el árbol público de HF |
| `zxing-core-3.5.3.jar` (332 entradas, todas `.class`) | El visor: lee el QR que pinta la PC para enlazar la memoria (F14b). Sólo decodifica QR, del frame de la cámara. | 3.5.3 | Apache-2.0, declarada en el propio `META-INF/MANIFEST.MF` del jar (`Bundle-License`) y en su POM. Se leyó antes de fijarlo: no trae `.so`, ni recursos, ni `META-INF/services`, y su `Require-Capability` pide JavaSE 1.8. | `8d8064c1…09fd82` (corroborada contra la `.sha1` que publica Maven Central: `ca134921…1a9c4b`) |
| La cara web del orbe (`cort-web/`) | La interfaz que el teléfono abre cuando el puente de la PC está en la red. | — | MIT, sobre el andamio de `JARVIS` de TechEnClair (MIT), rediseñado. Ver `cort-web/PROCEDENCIA.md` y `LICENSE` en la raíz del repo. | — |
| El cuerpo nativo del teléfono (`src/dev/sandra/cort/movil/*.java`) | La cara, el orbe, la memoria en SQLite, las manos del aparato y ahora el oído. | — | Autoría de Sandra: Askher Vargas y Sandra Lopez (2026), MIT. | — |

## Lo que **no** está en este APK

* Los servicios de Google ni `play-services-*`: el dictado local no los usa. Si
  el modelo falta, el respaldo es el reconocedor que el aparato ya traiga, que es
  decisión del teléfono, no de CORT.
* Ningún modelo de lenguaje generativo **dentro del APK**, aunque ya hay motor para
  abrirlos (U1). Los GGUF se bajan desde la pantalla «Almacén de cerebros» al carbajo
  de la app y con su SHA-256 comprobada. Es una decisión y no un olvido: 752 880 160
  bytes en el APK castigarían a quien lo instala por Wi-Fi, y el catálogo de modelos
  cambia más deprisa que el código.
* Nadie envía audio a internet en el modo local. `Motor.java` abre el micrófono,
  lo pasa por `libvosk.so` y tira el PCM al terminar. La única conexión de red que
  hay en ese archivo es la descarga del modelo de español, y la URL viene fijada en
  `assets/oido.json` (no en el código), con la suma comprobada antes de montar nada:
  si el archivo no cuadra con `09b23988…c6511f` se borra y no se usa.

## Cómo se reproducen estas sumas

Desde la carpeta `apps/android`, con las herramientas de siempre:

```bash
while IFS='|' read -r N SHA U; do
  case "$N" in ''|'#'*) continue ;; esac
  curl -fL -o "$N" "$U" && printf '%s  %s\n' "$SHA" "$N" | sha256sum -c -
done < deps.txt
```

Eso descarga, comprueba y nada más: instala el pipeline, no la máquina de la
dueña. Los `.so` y los `classes.jar` se sacan de los AAR con `unzip` dentro del
propio build (`compilar.sh`, paso 1).
