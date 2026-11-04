#!/usr/bin/env bash
# Compila el APK del teléfono: **la app completa, con su oído dentro**.
#
# Método (el mismo de siempre, y por las mismas razones medidas): `aapt2`,
# `javac`, `d8`, `zipalign` y `apksigner`, que el runner de GitHub Actions trae
# preinstalados. Sin Gradle y sin AndroidX: en la Classmate de 1,8 GiB un
# `gradle build` la congeló, y en este portátil ni siquiera hay `javac` (OpenJDK
# 21 sólo runtime). Este script **no se ejecuta nunca en el portátil** — corre en
# el pipeline y el artefacto se sube a la Release.
#
# Qué cambió con respecto al APK de 21 140 bytes: hasta aquí el teléfono era una
# ventana abierta al puente de la PC, y por eso no pesaba nada. Desde F12 el APK
# lleva dentro `libvosk.so`, `libjnidispatch.so` y el modelo español de 39,8 MB,
# así que CORT oye, habla, maneja el aparato y recuerda **sin IP, sin servidor y
# sin portátil encendido**. El puente sigue siendo opcional: si la PC está
# publicada, la cara del WebView se monta encima.
#
# Las dependencias no se inventan ni se bajan "las que haya": `deps.txt` fija
# nombre, URL y SHA-256 de cada una, y el build se cae si la suma no coincide.
# Con `CORT_SIN_MOTOR=1` se complica el APK delgado (sin oído local) para probar
# el resto, y el archivo de auditoría lo dice.
#
# Requiere ANDROID_HOME (el runner lo trae puesto). Salida: build/CORT-movil.apk
set -euo pipefail
cd "$(dirname "$0")"

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [ -z "$SDK" ] && [ -d /usr/local/lib/android/sdk ]; then SDK=/usr/local/lib/android/sdk; fi
[ -n "$SDK" ] || { echo "falta ANDROID_HOME: este script corre en el pipeline, no en el portátil"; exit 1; }

VERSION="${1:-0.12.0}"
# versionCode derivado de la versión (0.12.0 -> 1200): es el número con el que
# Android decide si esto es una actualización o hay que desinstalar el anterior.
case "$VERSION" in
    [0-9]*.[0-9]*.[0-9]*)
        IFS=. read -r MA MI PA <<<"$VERSION"
        CODE=$(( 10#$MA * 10000 + 10#$MI * 100 + 10#$PA )) ;;
    *) CODE=1 ;;
esac
[ "$CODE" -ge 1 ] || CODE=1

# Arquitecturas que se empaquetan. `arm64-v8a` es el Galaxy A16 de la dueña;
# `armeabi-v7a` cubre los teléfonos viejos. No se meten x86 ni x86_64: suman
# 20 MB para un emulador que aquí no se usa, y el tamaño del APK se ve en la
# lista de aplicaciones del teléfono.
ABIS="${CORT_ABIS:-arm64-v8a armeabi-v7a}"

# El `|| true` dentro de la sustitución no es decoración: con `pipefail` un `ls`
# que no encuentra el globo devuelve 2 y `set -e` mataría el script antes de la
# guarda de vacío. Medido en la otra línea, en su primer run.
BT="$( { ls -d "$SDK"/build-tools/*/ 2>/dev/null || true; } | sort -V | tail -1)"
PLAT="$( { ls -d "$SDK"/platforms/*/ 2>/dev/null || true; } | sort -V | tail -1)"
if [ -z "$BT" ] || [ -z "$PLAT" ]; then
    CMDL="$( { ls -d "$SDK"/cmdline-tools/*/bin 2>/dev/null || true; } | head -1)"
    [ -n "$CMDL" ] || { echo "ni SDK ni sdkmanager: el runner cambió de imagen"; exit 1; }
    yes | "$CMDL/sdkmanager" --licenses >/dev/null 2>&1 || true
    "$CMDL/sdkmanager" "platforms;android-34" "build-tools;34.0.0"
    BT="$( { ls -d "$SDK"/build-tools/*/ 2>/dev/null || true; } | sort -V | tail -1)"
    PLAT="$( { ls -d "$SDK"/platforms/*/ 2>/dev/null || true; } | sort -V | tail -1)"
fi
echo "build-tools: $(basename "$BT") · platform: $(basename "$PLAT") · versión: $VERSION (code $CODE) · abis: $ABIS"
command -v unzip >/dev/null || { echo "falta unzip: sin él no se abre un AAR"; exit 1; }
command -v curl  >/dev/null || { echo "falta curl: sin él no se baja el modelo"; exit 1; }

rm -rf build
mkdir -p build/obj build/apk vendor build/stage build/recursos

# -- 1. Las dependencias del oído, descargadas y comprobadas -------------------
# Cada línea de deps.txt es `nombre|sha256|url`. Se baja a un temporal, se le
# calcula la suma y sólo entonces pasa a su sitio: así un corte de red a medias
# no deja nunca un archivo a medio verificar dentro del APK.
MOTOR=0
if [ "${CORT_SIN_MOTOR:-0}" = "1" ]; then
    echo "CORT_SIN_MOTOR=1: se compila el APK DELGADO, sin oído local (el teléfono dictará por el motor de Android)"
else
    while IFS='|' read -r NOMBRE SHA URL; do
        case "$NOMBRE" in ''|'#'*) continue ;; esac
        if [ -z "$SHA" ] || [ -z "$URL" ]; then
            echo "::error::deps.txt mal escrito en la línea '$NOMBRE'"; exit 1
        fi
        DESTINO="vendor/$NOMBRE"
        if [ -f "$DESTINO" ] && printf '%s  %s\n' "$SHA" "$DESTINO" | sha256sum -c --status -; then
            echo "ya bajada y comprobada: $NOMBRE"
            continue
        fi
        echo "descargando $NOMBRE"
        curl -fsSL --retry 3 --max-time 900 -o "$DESTINO.tmp" "$URL"
        if ! printf '%s  %s\n' "$SHA" "$DESTINO.tmp" | sha256sum -c -; then
            echo "::error::$NOMBRE no cuadra con la suma fijada en deps.txt"
            echo "::error::esperada $SHA"
            echo "::error::recibida $(sha256sum "$DESTINO.tmp" | cut -d' ' -f1)"
            rm -f "$DESTINO.tmp"
            exit 1
        fi
        mv "$DESTINO.tmp" "$DESTINO"
        echo "verificada: $NOMBRE ($(stat -c%s "$DESTINO") bytes)"
    done < deps.txt

    # Desarmar los AAR: `classes.jar` va al `javac` y a `d8`; las `.so` van al
    # APK en `lib/<abi>/`, que es el sitio donde Android las busca.
    for AAR in vosk-android-0.3.75 jna-5.14.0; do
        if [ -f "vendor/$AAR.aar" ] && [ ! -d "vendor/$AAR" ]; then
            mkdir -p "vendor/$AAR"
            unzip -o -q "vendor/$AAR.aar" -d "vendor/$AAR"
        fi
    done
    for ABI in $ABIS; do
        mkdir -p "build/stage/lib/$ABI"
        for AAR in vosk-android-0.3.75 jna-5.14.0; do
            for FICHERO in vendor/"$AAR"/jni/"$ABI"/*.so; do
                [ -e "$FICHERO" ] || continue
                cp "$FICHERO" "build/stage/lib/$ABI/"
                echo "  .so -> $ABI: $(basename "$FICHERO") ($(stat -c%s "$FICHERO") bytes)"
            done
        done
    done
    HAY_NATIVAS=0
    if [ -n "$(find build/stage/lib -name '*.so' -type f 2>/dev/null)" ]; then HAY_NATIVAS=1; fi
    if [ -f vendor/vosk-android-0.3.75/classes.jar ] \
       && [ -f vendor/jna-5.14.0/classes.jar ] \
       && [ -f vendor/vosk-model-small-es-0.42.zip ] \
       && [ "$HAY_NATIVAS" = "1" ]; then
        mkdir -p build/recursos/assets/motor
        cp vendor/vosk-model-small-es-0.42.zip build/recursos/assets/motor/
        MOTOR=1
    else
        echo "::error::faltó algo del oído (vosk, jna, las .so o el modelo) y no se puede prometer un dictado local"
        exit 1
    fi
fi

# -- 2. Los recursos y el manifiesto ------------------------------------------
# `assets/` del repo (la tabla de frases del cerebro nativo) más, si toca, el
# modelo dentro de `assets/motor/`. `aapt2 link -A` es lo que los mete en el APK;
# sin esa bandera el teléfono abre con la boca vacía. Se copia el *contenido*
# (`assets/.`) y no la carpeta: si no, saldría `assets/assets/`.
mkdir -p build/recursos/assets
cp -a assets/. build/recursos/assets/

"$BT/aapt2" compile --dir res -o build/obj/res.zip
"$BT/aapt2" link -o build/apk/sin-alinear.apk \
    -I "$PLAT/android.jar" \
    --manifest AndroidManifest.xml \
    -A build/recursos/assets \
    --min-sdk-version 26 --target-sdk-version 34 \
    --version-code "$CODE" --version-name "$VERSION" \
    build/obj/res.zip --auto-add-overlay

# -- 3. El Java ----------------------------------------------------------------
# `--release 11`: la combinación `-source/-target` + `-bootclasspath` está
# prohibida desde target 9 (medido en la otra línea con el JDK del runner).
# Los `classes.jar` de Vosk y JNA van al classpath para `javac` (que sólo necesita
# las firmas) y como entrada de programa para `d8` (que los convierte en dex).
CLASSPATH="$PLAT/android.jar"
if [ "$MOTOR" = "1" ]; then
    CLASSPATH="$CLASSPATH:vendor/vosk-android-0.3.75/classes.jar:vendor/jna-5.14.0/classes.jar"
fi
javac --release 11 -classpath "$CLASSPATH" \
    -d build/obj $(find src -name '*.java')

D8_ENTRADAS="$(find build/obj -name '*.class')"
if [ "$MOTOR" = "1" ]; then
    "$BT/d8" --release --min-api 26 --lib "$PLAT/android.jar" --output build/apk \
        vendor/vosk-android-0.3.75/classes.jar \
        vendor/jna-5.14.0/classes.jar \
        $D8_ENTRADAS
else
    "$BT/d8" --release --min-api 26 --lib "$PLAT/android.jar" --output build/apk $D8_ENTRADAS
fi

(cd build/apk && zip -q -j sin-alinear.apk classes*.dex)

# -- 4. Las bibliotecas nativas, sin comprimir y alineadas ---------------------
# Con `android:extractNativeLibs="false"` el sistema carga el `.so` **desde el
# propio APK**, sin copiarlo a datos. Para eso el archivo tiene que estar
# almacenado (método 0, ni deflate) y alineado a página: `zip -0` y
# `zipalign -p`. Sin una de las dos, `System.loadLibrary("vosk")` falla con
# `UnsatisfiedLinkError` y el oído cae al motor de Android en silencio.
if [ -d build/stage/lib ] && [ -n "$(find build/stage/lib -name '*.so' -type f 2>/dev/null)" ]; then
    (cd build/stage && zip -q -X -0 ../apk/sin-alinear.apk $(find lib -type f))
    "$BT/zipalign" -f -p 4 build/apk/sin-alinear.apk build/apk/alineado.apk
else
    "$BT/zipalign" -f 4 build/apk/sin-alinear.apk build/apk/alineado.apk
fi

# -- 5. La firma ---------------------------------------------------------------
# La llave: con el secreto `CORT_APK_KEYSTORE_B64` el APK se puede actualizar
# instalando encima. Sin secreto se genera una llave desechable —y entonces cada
# Release pide desinstalar la anterior, que se dice aquí y en la release, no
# escondido en el log. La contraseña larga y `-keyalg` explícito son dos golpes
# medidos en la otra línea (keytool exige 6+ caracteres y el JDK del runner no
# trae algoritmo por defecto).
if [ -n "${CORT_APK_KEYSTORE_B64:-}" ]; then
    printf '%s' "$CORT_APK_KEYSTORE_B64" | base64 -d > build/cort.keystore
    KS_PASS="${CORT_APK_KEYSTORE_PASS:-}"
    [ -n "$KS_PASS" ] || { echo "hay keystore pero falta CORT_APK_KEYSTORE_PASS"; exit 1; }
    echo "firmando con la llave del repo"
else
    keytool -genkeypair -keystore build/cort.keystore -alias cort \
        -keyalg RSA -keysize 2048 \
        -storepass cortapk -keypass cortapk -validity 3650 \
        -dname "CN=CORT, OU=prototipo local, O=local"
    KS_PASS="cortapk"
    echo "firmando con una llave desechable (hay que desinstalar el APK anterior)"
fi

"$BT/apksigner" sign --ks build/cort.keystore \
    --ks-pass pass:"$KS_PASS" --key-pass pass:"$KS_PASS" \
    --out build/CORT-movil.apk build/apk/alineado.apk
"$BT/apksigner" verify build/CORT-movil.apk

# -- 6. La auditoría: qué salió y cuánto pesa ---------------------------------
# Todo lo que se afirma de este APK en el README o en la Release sale de aquí,
# con números medidos sobre el archivo final y no de memoria.
BYTES="$(stat -c%s build/CORT-movil.apk)"
MB="$(awk "BEGIN{printf \"%.2f\", $BYTES/1048576}")"
{
    echo "APK móvil de CORT $VERSION (versionCode $CODE)"
    echo "peso: $BYTES bytes ($MB MB)"
    if [ "$MOTOR" = "1" ]; then
        echo "oído: Vosk dentro del APK (modelo español pequeño, sin red)"
    else
        echo "oído: el motor de voz del aparato (APK delgado, CORT_SIN_MOTOR=1)"
    fi
    echo "arquitecturas: $ABIS"
    if [ -n "${CORT_APK_KEYSTORE_B64:-}" ]; then
        echo "llave: la del repo (se instala encima de la versión anterior)"
    else
        echo "llave: desechable (hay que desinstalar la versión anterior)"
    fi
    echo
    echo "== badging =="
    "$BT/aapt2" dump badging build/CORT-movil.apk 2>/dev/null \
        | grep -E "^package|versionCode|^sdkVersion|^targetSdkVersion|uses-permission|^application-label|^launchable" || true
    echo
    echo "== firma =="
    "$BT/apksigner" verify --print-certs build/CORT-movil.apk
    echo
    echo "== contenido (los 12 archivos que más pesan) =="
    unzip -l build/CORT-movil.apk | sort -n | tail -13
    echo
    echo "== comprobaciones de estructura =="
    if "$BT/zipalign" -c 4 build/CORT-movil.apk >/dev/null 2>&1; then
        echo "alineado a 4: ok"
    else
        echo "alineado a 4: FALLÓ"
    fi
    python3 - build/CORT-movil.apk <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
for nombre in ("lib/arm64-v8a/libvosk.so", "lib/arm64-v8a/libjnidispatch.so"):
    try:
        info = z.getinfo(nombre)
    except KeyError:
        print(nombre + ": no está en el APK")
        continue
    print(nombre + ": %d bytes · %s" % (info.file_size,
          "SIN COMPRIMIR (ok)" if info.compress_type == 0 else "comprimido (mal)"))
arsc = z.getinfo("resources.arsc")
print("resources.arsc: %d bytes · %s" % (arsc.file_size,
      "SIN COMPRIMIR (ok)" if arsc.compress_type == 0 else "comprimido (Android 11 lo pide suelto)"))
tot = sum(i.file_size for i in z.infolist())
print("entradas: %d · descomprimido suma %d bytes" % (len(z.infolist()), tot))
PY
} > build/auditoria.txt
cat build/auditoria.txt

{
    echo "APK móvil de CORT $VERSION (versionCode $CODE)"
    if [ -n "${CORT_APK_KEYSTORE_B64:-}" ]; then
        echo "llave: la del repo (se instala encima de la versión anterior)"
    else
        echo "llave: desechable (hay que desinstalar la versión anterior)"
    fi
    "$BT/apksigner" verify --print-certs build/CORT-movil.apk
} > build/firma.txt

echo "peso: $BYTES bytes ($MB MB)"
# El nombre que se anota es el **desnudo**. Medido en el run 41881069892: con
# `sha256sum build/CORT-movil.apk` el archivo quedaba como
# `…  build/CORT-movil.apk`, y al bajar el APK suelto de la release
# `sha256sum -c` respondía «No existe el fichero o el directorio» aunque la suma
# fuera buena. La dueña comprueba así, según el propio README: el `-c` tiene que
# funcionar sin tener que reescribir el archivo a mano.
(cd build && sha256sum CORT-movil.apk) | tee build/CORT-movil.apk.sha256
echo "APK listo: build/CORT-movil.apk"
