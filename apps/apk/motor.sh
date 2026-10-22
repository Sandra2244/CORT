#!/usr/bin/env bash
# Prepara el OÍDO PROPIO de CORT: el motor de reconocimiento que vive dentro del
# APK y que no necesita ni internet ni los servicios de Google.
#
#   bash apps/apk/motor.sh [carpeta-de-descargas]
#
# Sale de aquí, todo dentro del `build/` que `compilar.sh` ya usa:
#   build/motor/jar/vosk.jar   → se dexa con `d8` y se le da a `javac`
#   build/motor/jar/jna.jar    → lo mismo (Vosk habla con C a través de JNA)
#   build/motor/lib/<abi>/*.so → se meten en `lib/armeabi-v7a` y `lib/arm64-v8a`
#   assets/motor/<modelo>.zip  → el modelo de español, sin tocar, 39.817.833 B
#
# Por qué este motor y no otro (medido el 2026-10-21, no a ojo):
#
# · **Vosk** (`com.alphacephei:vosk-android:0.3.47`). Su AAR pesa 12.297.565 B y
#   trae UN solo `libvosk.so` por ABI (arm64 8.862.928 B en crudo, armeabi-v7a
#   8.279.808 B) y 14 clases Java de 16.721 B. Su modelo de español pequeño,
#   `vosk-model-small-es-0.42`, son 39.817.833 B ya comprimidos. Licencia
#   Apache-2.0, sin AndroidX y sin Kotlin: entra en este proyecto tal cual.
#   Sus clases usan `com.sun.jna.Pointer` (verificado con `strings` sobre
#   `classes.jar`), así que hace falta también el AAR de JNA — 517.278 B, con
#   `libjnidispatch.so` de 168.176 B en arm64. Nada que compilar: son binarios
#   ya hechos para Android, que es justo lo que este pipeline (sin NDK) no
#   podría fabricar.
# · **sherpa-onnx** se descartó por peso y por arrastre: su AAR completo son
#   50.129.134 B y sóólo la pata arm64 `libonnxruntime.so` + `libsherpa-onnx-jni.so`
#   suman 27.021.320 B en crudo, y su mejor modelo de español continuo
#   (`zipformer-es`) llega a 155.838.792 B. Haría un APK de más de 200 MB para
#   dar el mismo oído.
# · **whisper.cpp** y **Piper** no publican binarios Android hechos: hay que
#   cruzar-compilar con NDK dentro del pipeline, y eso es otra ronda entera.
#   (Piper sí queda pendiente para la VOZ propia: su voz `es_MX-ald-x_low`
#   pesan 20.986.952 B y necesitarían los `.so` de sherpa.)
#
# El modelo NO se descomprime aquí: viaja como un único archivo dentro de
# `assets/motor/` y `Oido.java` lo desempaca la primera vez que CORT arranca en
# el teléfono, porque `org.vosk.Model(String)` sólo acepta un **directorio del
# disco** (firma medida con `javap`), no un `AssetManager`.
set -euo pipefail
cd "$(dirname "$0")"

# Versiones y tamaños FIJOS. Si Maven o alphacephei cambian un byte sin avisar,
# este script para el build en vez de meter un APK roto en la Release: el peso
# verificado es lo único que distingue «descargué el archivo» de «descargué la
# página de error en HTML».
VOSK_ARTEFACTO="com/alphacephei/vosk-android/0.3.47/vosk-android-0.3.47.aar"
VOSK_PESO=12297565
VOSK_SHA="e3b82bb877753569f5e5f007807e4bc6165c34ba04e772d1df93552af0d27ffa"
JNA_ARTEFACTO="net/java/dev/jna/jna/5.13.0/jna-5.13.0.aar"
JNA_PESO=517278
JNA_SHA="3a03daf5a7212201c3a9b44f734dfc9babb3addcb5cbfa639f9f535e887925c0"
MODELO="vosk-model-small-es-0.42"
MODELO_URL="https://alphacephei.com/vosk/models/${MODELO}.zip"
MODELO_PESO=39817833
# El modelo entero no se hash-ea aquí (son 40 MB y el runner ya los valida por
# peso y por el `unzip -t` de abajo); su SHA-256 se publica en `firma.txt` para
# poder comparar descargas futuras.

CACHE="${1:-motor-cache}"
mkdir -p "$CACHE" build/motor/jar build/motor/lib assets/motor

baja() {    # baja() <url> <nombre> <peso-esperado> <sha-esperado|->
    # Dos `local` en vez de uno: `local nombre="$2" destino="$CACHE/$nombre"` se
    # expande entero ANTES de asignar nada, así que con `set -u` `$nombre` aún no
    # existe y el script moría en la primera descarga («nombre: variable sin
    # asignar», medido el 2026-10-21 en el run rojo de `v0.2.20-demo`).
    local url="$1" nombre="$2" peso="$3" sha="$4"
    local destino="$CACHE/$nombre"
    if [ -f "$destino" ] \
       && [ "$(stat -c '%s' "$destino" 2>/dev/null || wc -c < "$destino" | tr -d ' ')" = "$peso" ] \
       && { [ "$sha" = "-" ] || [ "$(sha256sum "$destino" | cut -d' ' -f1)" = "$sha" ]; }; then
        echo "motor: $nombre ya en la caché, peso y huella correctos"
        return 0
    fi
    echo "motor: bajando $nombre ($peso bytes esperados)"
    curl --fail --silent --show-error --location --retry 3 --retry-delay 5 \
         --max-time 900 -o "$destino.part" "$url" || { rm -f "$destino.part"; return 1; }
    local real
    real="$(stat -c '%s' "$destino.part" 2>/dev/null || wc -c < "$destino.part" | tr -d ' ')"
    [ "$real" = "$peso" ] || { echo "motor: $nombre pesa $real, se esperaban $peso — se aborta"; rm -f "$destino.part"; return 1; }
    if [ "$sha" != "-" ]; then
        local huella; huella="$(sha256sum "$destino.part" | cut -d' ' -f1)"
        [ "$huella" = "$sha" ] || { echo "motor: huella de $nombre = $huella, no $sha"; rm -f "$destino.part"; return 1; }
    fi
    mv "$destino.part" "$destino"
}

baja "https://repo1.maven.org/maven2/$VOSK_ARTEFACTO" vosk.aar "$VOSK_PESO" "$VOSK_SHA"
baja "https://repo1.maven.org/maven2/$JNA_ARTEFACTO"  jna.aar  "$JNA_PESO"  "$JNA_SHA"
baja "$MODELO_URL" "${MODELO}.zip" "$MODELO_PESO" "-"

# -- Los `.so` y los `.jar`, separados por arquitectura ----------------------
# Sólo arm64 y armeabi-v7a: son los dos que pisan un teléfono. Meter x86/x86_64
# sería añadir 19 MB de peso que nunca se ejecuta en el aparato de la dueña, y
# eso está expresamente prohibido (peso sin función no es功能, es relleno).
for par in vosk jna; do
    rm -rf "build/motor/unpack-$par"
    mkdir -p "build/motor/unpack-$par"
    unzip -o -q "$CACHE/$par.aar" -d "build/motor/unpack-$par"
    cp "build/motor/unpack-$par/classes.jar" "build/motor/jar/$par.jar"
    for abi in arm64-v8a armeabi-v7a; do
        src="build/motor/unpack-$par/jni/$abi"
        [ -d "$src" ] || { echo "motor: $par no trae $abi"; false; }
        mkdir -p "build/motor/lib/$abi"
        # `cat` en vez de `cp` para conservar el permiso de ejecución: `cp -p` no
        # lo garantiza sobre un archivo recién descomprimido del AAR.
        for so in "$src"/*.so; do
            cat "$so" > "build/motor/lib/$abi/$(basename "$so")"
            chmod 644 "build/motor/lib/$abi/$(basename "$so")"
        done
    done
    rm -rf "build/motor/unpack-$par"
done

# -- El modelo, tal cual, dentro del APK -------------------------------------
cat "$CACHE/${MODELO}.zip" > "assets/motor/${MODELO}.zip"
unzip -t "assets/motor/${MODELO}.zip" >/dev/null   # integridad del ZIP, puerta a puerta
MODELO_DIRECTORIOS="$(unzip -Z1 "assets/motor/${MODELO}.zip" | grep -vc '/$' || true)"
MODELO_SHA="$(sha256sum "assets/motor/${MODELO}.zip" | cut -d' ' -f1)"

echo "motor: vosk.jar $(stat -c '%s' build/motor/jar/vosk.jar) B · jna.jar $(stat -c '%s' build/motor/jar/jna.jar) B"
echo "motor: .so -> $(find build/motor/lib -name '*.so' | sort | tr '\n' ' ')"
echo "motor: modelo assets/motor/${MODELO}.zip = $(stat -c '%s' "assets/motor/${MODELO}.zip") B, $MODELO_DIRECTORIOS archivos, sha256 $MODELO_SHA"
echo "$MODELO_SHA" > build/motor/modelo-sha256.txt
echo "$MODELO" > build/motor/modelo-nombre.txt
