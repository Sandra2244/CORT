#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# prueba-oido.sh — el oído propio del APK, probado DE VERDAD antes de publicar.
#
# `Oido.kt` llama a `org.vosk.Model`, a `AudioRecord` y a un desempaque de 60 MB.
# Las dos primeras no se ven más que en un teléfono… salvo por dos cosas:
#
#   · `vosk.jar` es el MISMO Java en Android y en escritorio, y el `vosk.jar` de
#     escritorio (`com.alphacephei:vosk`) trae `linux-x86-64/libvosk.so` dentro:
#     el mismo compilado C que el `libvosk.so` del AAR de Android. Así que el
#     modelo de español carga y reconoce AQUÍ.
#   · `apps/apk/prueba/papeles` tiene los gemelos de papel de `AudioRecord`,
#     `StatFs`, `Context` y `AssetManager`, y el de `AudioRecord` deja meter
#     muestras a mano (`ALIMENTAR`) o imitar el micrófono robado (`CODIGO_DE_READ`).
#
# Con las dos cosas, `PruebaOido.kt` ejercita el bucle entero: desempaca el
# modelo, lo carga, escucha silencio, escucha señal, le quitan el micro a mitad,
# cancela y se queda sin sitio. Siete comprobaciones que en el pipeline de
# `javac` eran imposibles.
#
# Uso:  bash scripts/prueba-oido.sh
#       JAVA_MEM=256m bash scripts/prueba-oido.sh
# En GitHub Actions corre después de `motor.sh`, que ya dejó los `.jar` y el
# modelo. En el portátil baja a `~/.cache/cort-motor` lo que falte.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."
RAIZ=$(pwd)
APK=$RAIZ/apps/apk
T=/tmp/cort-oido
MEM="${JAVA_MEM:-256m}"
# `kotlinc` precarga todas las clases de los `.jar` antes de empezar y con 168 MB
# revienta (`OutOfMemoryError` en `ClassPreloadingUtils`, medido en el portátil de
# 1,8 GiB). El compilador va por un lado y la prueba, que carga un modelo de
# 60 MB, por otro: se pueden poner techos distintos.
MEM_KOTLINC="${KOTLIN_MEM:-320m}"
CACHE="${MOTOR_CACHE_DIR:-$HOME/.cache/cort-motor}"
# `motor.sh` hace `cd "$(dirname "$0")"` (se va a `apps/apk`), así que una caché
# RELATIVA —como la que pasa el pipeline, `apps/apk/motor-cache`— le llegaría como
# `apps/apk/apps/apk/motor-cache` y bajaría 53 MB a un sitio que nadie mira. Se
# vuelve absoluta aquí, que es el único lugar donde se puede arreglar sin tocar
# el script del motor.
case "$CACHE" in /*) ;; *) CACHE="$RAIZ/$CACHE" ;; esac

MODO="${1:-todo}"          # `compilar` = sólo tipo-checkeo (sin montones ni modelo)

# 1 · las piezas: los `.jar` del AAR de Android (compilar) y los de escritorio
#     (ejecutar con el `libvosk.so` de linux dentro).
mkdir -p "$CACHE" "$T"
if [ -f "$APK/build/motor/jar/vosk.jar" ]; then
    JAR_VOSK="$APK/build/motor/jar/vosk.jar"; JAR_JNA="$APK/build/motor/jar/jna.jar"
else
    echo "== motor: sin build/motor, se baixa a la caché"
    bash "$APK/motor.sh" "$CACHE" >/dev/null 2>&1 || true
    mkdir -p "$APK/build/motor/jar"
    [ -f "$APK/build/motor/jar/vosk.jar" ] || { mkdir -p "$T/aar"; unzip -o -q "$CACHE/vosk.aar" classes.jar -d "$T/aar" && cat "$T/aar/classes.jar" > "$APK/build/motor/jar/vosk.jar"; }
    [ -f "$APK/build/motor/jar/jna.jar" ] || { mkdir -p "$T/aar2"; unzip -o -q "$CACHE/jna.aar" classes.jar -d "$T/aar2" && cat "$T/aar2/classes.jar" > "$APK/build/motor/jar/jna.jar"; }
    JAR_VOSK="$APK/build/motor/jar/vosk.jar"; JAR_JNA="$APK/build/motor/jar/jna.jar"
fi

MODELO_ZIP="$(ls "$APK"/assets/motor/*.zip 2>/dev/null | head -1 || true)"
[ -n "$MODELO_ZIP" ] || MODELO_ZIP="$(ls "$CACHE"/vosk-model-small-es-0.42.zip 2>/dev/null | head -1 || true)"
if [ -z "$MODELO_ZIP" ] && [ "$MODO" != compilar ]; then
    bash "$APK/motor.sh" "$CACHE" || { echo "no se pudo bajar el modelo"; exit 1; }
    MODELO_ZIP="$CACHE/vosk-model-small-es-0.42.zip"
fi

# Para ejecutar hace falta el `vosk` de escritorio (con su `.so` de linux) y el
# `jna` normal. Son 27 MB: sólo si de verdad se van a correr las pruebas.
ESCRITORIO="$CACHE/vosk-0.3.45.jar"
JNA_JAR="$CACHE/jna-5.13.0.jar"
if [ "$MODO" != compilar ] && [ ! -f "$ESCRITORIO" ]; then
    curl --fail --silent --show-error --location --retry 3 --max-time 600 \
         -o "$ESCRITORIO.part" https://repo1.maven.org/maven2/com/alphacephei/vosk/0.3.45/vosk-0.3.45.jar
    mv "$ESCRITORIO.part" "$ESCRITORIO"
fi
if [ "$MODO" != compilar ] && [ ! -f "$JNA_JAR" ]; then
    curl --fail --silent --show-error --location --retry 3 --max-time 300 \
         -o "$JNA_JAR.part" https://repo1.maven.org/maven2/net/java/dev/jna/jna/5.13.0/jna-5.13.0.jar
    mv "$JNA_JAR.part" "$JNA_JAR"
fi

# 2 · `kotlinc`: el del pipeline (`$KOTLIN_DIR` en compilar.sh) o el de la caché.
KOTLIN_DIR="${KOTLIN_DIR:-$HOME/.cache/cort-kotlin}"
KOTLINC="$KOTLIN_DIR/kotlinc/bin/kotlinc"
if [ ! -x "$KOTLINC" ]; then
    echo "== kotlin: se baixa kotlin-compiler-1.9.24 (sólo para comprobar, no para el APK)"
    mkdir -p "$KOTLIN_DIR"
    curl --fail --silent --show-error --location --retry 3 --max-time 900 \
         -o /tmp/kotlinc.zip https://github.com/JetBrains/kotlin/releases/download/v1.9.24/kotlin-compiler-1.9.24.zip
    unzip -q -o /tmp/kotlinc.zip -d "$KOTLIN_DIR"; rm -f /tmp/kotlinc.zip
fi
[ -x "$KOTLINC" ] || { echo "no hay kotlinc en $KOTLIN_DIR"; exit 1; }

# 3 · los gemelos de papel, con javac (orden o módulo del JDK, según el portátil)
si_javac() {
  if command -v javac >/dev/null 2>&1; then javac "$@"
  else java -Xmx"$MEM" -m jdk.compiler/com.sun.tools.javac.Main "$@"; fi
}
rm -rf "$T/out"; mkdir -p "$T/out"
PAPELES="$(find "$APK/prueba/papeles" -name '*.java')"
# shellcheck disable=SC2086
si_javac -encoding UTF-8 -d "$T/out" $PAPELES
echo "== papel: $(echo "$PAPELES" | wc -l) gemelos compilados"

# 4 · el Kotlin del APK + la prueba, contra los `.class` del papel y los `.jar` reales
FUENTES_K="$(find "$APK/src" -name '*.kt' | sort)"
[ -n "$FUENTES_K" ] || { echo "no hay .kt en apps/apk/src: nada que comprobar"; exit 0; }
CP="$T/out:$JAR_VOSK:$JAR_JNA:$KOTLIN_DIR/kotlinc/lib/kotlin-stdlib.jar"
mkdir -p "$T/kt"
set +e
"$KOTLINC" -J-Xmx"$MEM_KOTLINC" -jvm-target 11 -classpath "$CP" -d "$T/kt" \
    $FUENTES_K "$APK/prueba/PruebaOido.kt" 2>&1 | tee "$T/kotlin.log"
st=${PIPESTATUS[0]}
set -e
if [ $st -ne 0 ] || grep -qE ': ?error:|^e: ' "$T/kotlin.log"; then
    echo "FALLO: kotlinc no pasó el Kotlin del APK"; grep -E ': ?error:|^e: ' "$T/kotlin.log" | head -20
    exit 1
fi
echo "== kotlin: $(echo "$FUENTES_K" | wc -l) archivos y PruebaOido.kt compilan contra el org.vosk real"
[ "$MODO" = compilar ] && { echo "OIDO OK (sólo tipos, sin ejecutar): MODO=compilar"; exit 0; }

# 5 · el modelo en su sitio de papel, y a correr
mkdir -p "$T/activos/motor" "$T/archivos"
[ -f "$T/activos/motor/$(basename "$MODELO_ZIP")" ] || cp "$MODELO_ZIP" "$T/activos/motor/"
set +e
java -Xmx"$MEM" -cp "$T/kt:$T/out:$ESCRITORIO:$JNA_JAR:$KOTLIN_DIR/kotlinc/lib/kotlin-stdlib.jar" \
     com.cort.ia.PruebaOido "$T/activos" "$T/archivos" > "$T/prueba.log" 2>&1
st=$?
set -e
cat "$T/prueba.log"
if [ $st -ne 0 ]; then
    echo "FALLO: la prueba del oído salió con $st"
    exit $st
fi
