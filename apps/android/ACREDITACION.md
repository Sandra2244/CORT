# De dónde sale cada pieza de este APK

Lo que viaja dentro de `CORT-movil.apk`, con su licencia **leída antes de usarla**
y no supuesta. La regla de la casa: un archivo ajeno se baja, se lee y entonces
se usa; y si trae una suma publicada, esa suma se fija en `deps.txt` para que el
build se caiga el día que el archivo cambie sin que nadie avise.

| Pieza | Qué hace en CORT | Versión | Licencia (dónde está escrita) | Suma fijada |
|---|---|---|---|---|
| `libvosk.so` (AAR `com.alphacephei:vosk-android`) | El oído: convierte el habla en texto **dentro del teléfono**, sin red. | 0.3.75 | Apache-2.0, declarada en el POM publicado (`vosk-android-0.3.75.pom`, nodo `<licenses>`). | `ab2f8b91…c4adfad` |
| `libjnidispatch.so` + `classes.jar` (AAR `net.java.dev.jna:jna`) | El puente que llama a la biblioteca nativa desde Java; es lo que usa Vosk. | 5.14.0 | LGPL-2.1-or-later, declarada en el POM publicado (`jna-5.14.0.pom`). Se enlaza como biblioteca dinámica estándar: el código de CORT no modifica ni redistribuye fuentes de JNA. | `81a8b9af…dfab380` (comprobada además contra el `.aar.sha1` que publica Maven Central) |
| `vosk-model-small-es-0.42.zip` (**dentro del APK** desde `cort-v0.17.1`, en `assets/motor/`) | El modelo de español: 39 817 833 bytes, para que el teléfono oiga nada más instalarse sin que nadie pulse «Bajar el oído». `Motor.java` lo descomprime una vez a `filesDir/motor/` y deja marcador. Si alguien venía de `cort-v0.16.2` y ya lo tenía bajado, `Motor` usa primero ese archivo y le comprueba esta misma suma. La ficha (`assets/oido.json`, 867 B) sigue viajando con la URL, el peso y la suma para el camino contrario. | 0.42 | Apache-2.0, en la fila del modelo de la lista oficial de modelos de Alpha Cephei (`alphacephei.com/vosk/models`), que también publica su precisión: 16,02 % de error de palabra en *cv test*, 16,72 % en *mtedx test* y 11,21 % en *mls*. **Cifras del fabricante, no medidas por nosotras.** | `09b23988…c6511f` |
| `libcortmotor.so` (compilada en Actions; **las dos ABIs dentro** —`arm64-v8a` y `armeabi-v7a`— y comprimidas) | El cerebro: llama.cpp cruzado con el NDK de Google, con el pegamento JNI de CORT (`apps/android/jni/cort_motor.cpp`) enlazado **estático y autocontenido** dentro. | llama.cpp b12121 · NDK r26d | MIT, declarada en el propio `LICENSE` del fuente que se baja y se verifica por SHA-256 en `motor-local.yml` (medido el 2026-11-05 contra la API de GitHub: `spdx_id: MIT` de `ggml-org/llama.cpp`). El pegamento JNI es autoría nuestra y usa sólo la API pública de `llama.h`. | fuente fijado: `0b6fbcaa…` (el tarball completo, en `motor-local.yml`) |
| `qwen2.5-*-instruct-*.gguf` (**no viaja en el APK**) | Los cerebros que la dueña baja desde el almacén: 0,5B q4_K_M (491 400 032 B), 1,5B q2_k (752 880 160 B) y 1,5B q4_K_M (1 117 320 736 B). | Qwen2.5-Instruct | Apache-2.0, leída el 2026-11-05 en la API de Hugging Face de `Qwen/Qwen2.5-0.5B-Instruct-GGUF` y `Qwen/Qwen2.5-1.5B-Instruct-GGUF` (las dos con la etiqueta `license:apache-2.0`). Cada archivo se vuelve a sumar en el teléfono y se tira si su SHA-256 no es la fijada en `assets/cerebros.json`. | las tres sumas, en `assets/cerebros.json`, medidas contra el árbol público de HF |
| `zxing-core-3.5.3.jar` (332 entradas, todas `.class`) | El visor: lee el QR que pinta la PC para enlazar la memoria (F14b). Sólo decodifica QR, del frame de la cámara. | 3.5.3 | Apache-2.0, declarada en el propio `META-INF/MANIFEST.MF` del jar (`Bundle-License`) y en su POM. Se leyó antes de fijarlo: no trae `.so`, ni recursos, ni `META-INF/services`, y su `Require-Capability` pide JavaSE 1.8. | `8d8064c1…09fd82` (corroborada contra la `.sha1` que publica Maven Central: `ca134921…1a9c4b`) |
| La cara web (`cort-web/` → `assets/web/` dentro del APK, F19a) | La interfaz que el teléfono abre desde `cort-v0.17.1`: el mismo `index.html`, el mismo `cort-ui.js` y los mismos paneles del portátil, empaquetados en el APK y servidos por `Nexo.java` en un `WebView`. | — | MIT, sobre el andamio de `JARVIS` de TechEnClair (MIT), rediseñado. Ver `cort-web/PROCEDENCIA.md` y `LICENSE` en la raíz del repo. `demo/`, los `*.md` y las copias `*.orig` **no viajan**: la página no los pide. | — |
| `assets/three.module-*.js` (688 470 bytes medidos, dentro del bundle de la cara) | El orbe: la esfera que late, rota y habla. Es el módulo empaquetado que ya traía la demo, sin tocar. | **sin fijar** (el `REVISION` del módulo va concatenado en el código minificado y no se puede leer como número; no se escribe una versión que no hemos podido medir) | MIT, declarada en el propio archivo: su cabecera lleva `Copyright 2010-2024 Three.js Authors`. El texto del `LICENSE` bajado el 2026-11-05 de la etiqueta `r171` del repositorio de three.js y espejado en `cort-web/cort/vendor/three/LICENSE` (suma `4c40a1ef…4454`), que es la que se redistribuye dentro del APK. La cláusula de atribución se cumple con ese texto más el aviso de la cabecera, que viajan los dos. | el módulo viaja con el hash de Vite en el nombre (`three.module-DBf_OzsH.js`), que es lo que lo identifica en esta copia; el `LICENSE` espejado es el de `r171`, y el aviso de derechos del módulo (`2010-2024`) coincide con el de ese texto |
| `cort/vendor/leaflet/*` (148 KB de JS) | El mapa del panel de clima y del panel de dispositivos (F6), espejo local: **no hay CDN** en la cara. | 1.9.4 | **BSD-2-Clause**, leída el 2026-11-05 en el `LICENSE` de la etiqueta `v1.9.4` del repositorio de Leaflet y bajada a `cort-web/cort/vendor/leaflet/LICENSE` (suma `53e8dc25…d4cb`), para cumplir su propia cláusula 2 al redistribuirse en binario dentro del APK. La cabecera `@preserve` con los dos avisos de derechos va también dentro del `leaflet.js`. | `53e8dc25…d4cb` (el `LICENSE`) |
| El cuerpo nativo del teléfono (`src/dev/sandra/cort/movil/*.java`) | La cara, el orbe, la memoria en SQLite, las manos del aparato y ahora el oído. | — | Autoría de Sandra: Askher Vargas y Sandra Lopez (2026), MIT. | — |

## Lo que **no** está en este APK

* `cort-web/demo/`, los `*.md` de la cara y las copias `*.orig`
  (`main-s6G6kMTO.js.orig`, 453 154 bytes): son andamio de una edición anterior y
  documentación de desarrollo. La página no los pide nunca, y `compilar.sh` los
  borra del stage con `find … -name '*.orig' -delete`.
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
