# De dónde sale cada pieza de este APK

Lo que viaja dentro de `CORT-movil.apk`, con su licencia **leída antes de usarla**
y no supuesta. La regla de la casa: un archivo ajeno se baja, se lee y entonces
se usa; y si trae una suma publicada, esa suma se fija en `deps.txt` para que el
build se caiga el día que el archivo cambie sin que nadie avise.

| Pieza | Qué hace en CORT | Versión | Licencia (dónde está escrita) | Suma fijada |
|---|---|---|---|---|
| `libvosk.so` (AAR `com.alphacephei:vosk-android`) | El oído: convierte el habla en texto **dentro del teléfono**, sin red. | 0.3.75 | Apache-2.0, declarada en el POM publicado (`vosk-android-0.3.75.pom`, nodo `<licenses>`). | `ab2f8b91…c4adfad` |
| `libjnidispatch.so` + `classes.jar` (AAR `net.java.dev.jna:jna`) | El puente que llama a la biblioteca nativa desde Java; es lo que usa Vosk. | 5.14.0 | LGPL-2.1-or-later, declarada en el POM publicado (`jna-5.14.0.pom`). Se enlaza como biblioteca dinámica estándar: el código de CORT no modifica ni redistribuye fuentes de JNA. | `81a8b9af…dfab380` (comprobada además contra el `.aar.sha1` que publica Maven Central) |
| `vosk-model-small-es-0.42.zip` (dentro de `assets/motor/`) | El modelo de español: 39 817 833 bytes. Es la mayor parte del peso del APK. | 0.42 | Apache-2.0, en la fila del modelo de la lista oficial de modelos de Alpha Cephei (`alphacephei.com/vosk/models`), que también publica su precisión: 16,02 % de error de palabra en *cv test*, 16,72 % en *mtedx test* y 11,21 % en *mls*. **Cifras del fabricante, no medidas por nosotras.** | `09b23988…c6511f` |
| La cara web del orbe (`cort-web/`) | La interfaz que el teléfono abre cuando el puente de la PC está en la red. | — | MIT, sobre el andamio de `JARVIS` de TechEnClair (MIT), rediseñado. Ver `cort-web/PROCEDENCIA.md` y `LICENSE` en la raíz del repo. | — |
| El cuerpo nativo del teléfono (`src/dev/sandra/cort/movil/*.java`) | La cara, el orbe, la memoria en SQLite, las manos del aparato y ahora el oído. | — | Autoría de Sandra: Askher Vargas y Sandra Lopez (2026), MIT. | — |

## Lo que **no** está en este APK

* Los servicios de Google ni `play-services-*`: el dictado local no los usa. Si
  el modelo falta, el respaldo es el reconocedor que el aparato ya traiga, que es
  decisión del teléfono, no de CORT.
* Cualquier modelo de lenguaje generativo: el cerebro GGUF dentro del teléfono es
  la fase siguiente (F13) y todavía no existe.
* Nadie envía audio a internet en el modo local. `Motor.java` abre el micrófono,
  lo pasa por `libvosk.so` y tira el PCM al terminar; no hay una sola llamada de
  red en ese camino. Lo verificable es el código: en `Motor.java` no se importa
  `java.net` ni `HttpURLConnection`.

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
