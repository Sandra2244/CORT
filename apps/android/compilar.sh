#!/usr/bin/env bash
# Compila el APK del teléfono sobre el puente de esta rama (el de la PC).
#
# Mismo método que ya está probado en la otra línea del repo: `aapt2`, `javac`,
# `d8`, `zipalign` y `apksigner`, que el runner de GitHub Actions trae
# preinstalados. **Sin Gradle y sin AndroidX**, por dos razones medidas: en la
# Classmate de 1,8 GiB un `gradle build` la congeló, y aquí ni siquiera hay
# `javac` (OpenJDK 21 sólo runtime), así que este script no se ejecuta nunca en
# el portátil — corre en el pipeline y el artefacto se sube a la Release.
#
# Requiere ANDROID_HOME (el runner lo trae puesto). Salida: build/CORT-movil.apk
set -euo pipefail
cd "$(dirname "$0")"

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [ -z "$SDK" ] && [ -d /usr/local/lib/android/sdk ]; then SDK=/usr/local/lib/android/sdk; fi
[ -n "$SDK" ] || { echo "falta ANDROID_HOME: este script corre en el pipeline, no en el portátil"; exit 1; }

VERSION="${1:-0.11.0}"
# versionCode derivado de la versión (0.11.0 -> 1100): es el número con el que
# Android decide si esto es una actualización o hay que desinstalar el anterior.
case "$VERSION" in
    [0-9]*.[0-9]*.[0-9]*)
        IFS=. read -r MA MI PA <<<"$VERSION"
        CODE=$(( 10#$MA * 10000 + 10#$MI * 100 + 10#$PA )) ;;
    *) CODE=1 ;;
esac
[ "$CODE" -ge 1 ] || CODE=1

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
echo "build-tools: $(basename "$BT") · platform: $(basename "$PLAT") · versión: $VERSION (code $CODE)"

rm -rf build
mkdir -p build/obj build/apk

"$BT/aapt2" compile --dir res -o build/obj/res.zip
"$BT/aapt2" link -o build/apk/sin-alinear.apk \
    -I "$PLAT/android.jar" \
    --manifest AndroidManifest.xml \
    --min-sdk-version 26 --target-sdk-version 34 \
    --version-code "$CODE" --version-name "$VERSION" \
    build/obj/res.zip --auto-add-overlay

# `--release 11`: la combinación `-source/-target` + `-bootclasspath` está
# prohibida desde target 9 (medido en la otra línea con el JDK del runner).
javac --release 11 -classpath "$PLAT/android.jar" \
    -d build/obj $(find src -name '*.java')
"$BT/d8" --release --lib "$PLAT/android.jar" --output build/apk \
    $(find build/obj -name '*.class')

(cd build/apk && zip -q -j sin-alinear.apk classes*.dex)
"$BT/zipalign" -f 4 build/apk/sin-alinear.apk build/apk/alineado.apk

# La firma: con el secreto `CORT_APK_KEYSTORE_B64` el APK se puede actualizar
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

{
    echo "APK móvil de CORT $VERSION (versionCode $CODE)"
    if [ -n "${CORT_APK_KEYSTORE_B64:-}" ]; then
        echo "llave: la del repo (se instala encima de la versión anterior)"
    else
        echo "llave: desechable (hay que desinstalar la versión anterior)"
    fi
    "$BT/apksigner" verify --print-certs build/CORT-movil.apk
} > build/firma.txt
cat build/firma.txt

BYTES="$(stat -c%s build/CORT-movil.apk)"
echo "peso: $BYTES bytes ($(awk "BEGIN{printf \"%.2f\", $BYTES/1048576}") MB)"
sha256sum build/CORT-movil.apk | tee build/CORT-movil.apk.sha256
echo "APK listo: build/CORT-movil.apk"
