#!/usr/bin/env bash
# Compila el APK de CORT con las herramientas que el runner de GitHub Actions ya
# trae: `aapt2`, `javac`, `d8`, `zipalign`, `apksigner`. Sin Gradle, sin AndroidX,
# sin Capacitor: la dueña del proyecto tiene un portátil de 1,8 GiB donde un
# `gradle build` la congeló (medido), así que este script **no se ejecuta nunca
# en el portátil** — corre en el pipeline y el artefacto se sube a la Release.
#
# Requiere ANDROID_HOME (el runner lo trae puesto). Salida: build/CORT.apk.
#
# La firma: si el repo tiene el secreto `CORT_APK_KEYSTORE_B64` (el keystore en
# base64) firma con esa llave y el APK se puede **actualizar** instalando encima.
# Sin secreto se genera uno desechable, y entonces cada Release pide desinstalar
# el anterior — es honesto para un prototipo y se dice en apps/apk/README.md en
# vez de esconderse en el log.
set -euo pipefail
cd "$(dirname "$0")"

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:?falta ANDROID_HOME: este script corre en el pipeline, no en el portátil}}"
# Versión visible del APK: `compilar.sh 0.13.0`. La etiqueta `v0.13.0` del
# pipeline la pasa sin la `v`; el default es para cuando se dispara a mano.
VERSION="${1:-0.13.0}"
BT="$(ls -d "$SDK"/build-tools/* 2>/dev/null | sort -V | tail -1)"
PLAT="$(ls -d "$SDK"/platforms/* 2>/dev/null | sort -V | tail -1)"
if [ -z "$BT" ] || [ -z "$PLAT" ]; then
    # El runner de GitHubActions trae el SDK preinstalado; si la imagen alguna
    # vez no lo trae, `sdkmanager` (también viene) descarga lo mínimo. No se
    # instala Gradle ni AndroidX: no hacen falta para un `aapt2` + `javac` + `d8`.
    CMDL="$(ls -d "$SDK"/cmdline-tools/*/bin 2>/dev/null | head -1)"
    [ -n "$CMDL" ] || { echo "ni SDK ni sdkmanager: el runner cambió de imagen"; exit 1; }
    yes | "$CMDL/sdkmanager" --licenses >/dev/null 2>&1 || true
    "$CMDL/sdkmanager" "platforms;android-34" "build-tools;34.0.0"
    BT="$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)"
    PLAT="$(ls -d "$SDK"/platforms/* | sort -V | tail -1)"
fi
echo "build-tools: $(basename "$BT") · platform: $(basename "$PLAT") · versión: $VERSION"

# -- El icono se dibuja con el código de la propia marca (scripts/marca.py) ---
# Nada de assets binarios inventados a mano: la firma PNG de este icono está
# probada en `test_marca.py`, y la forma del anillo es la que ya valida la suite.
python3 - <<'PY'
import pathlib
import sys
# `compilar.sh` ya cambió al directorio `apps/apk`: la marca vive dos niveles
# arriba, en `scripts/marca.py`.
sys.path.insert(0, "../../scripts")
from marca import render, encode_png
for carpeta, dim in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96),
                    ("xxhdpi", 144), ("xxxhdpi", 192)):
    d = pathlib.Path("res") / f"mipmap-{carpeta}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "ic_launcher.png").write_bytes(encode_png(dim, render(dim)))
print("iconos de marca generados (5 densidades)")
PY

rm -rf build
mkdir -p build/obj build/apk

# -- Recursos y manifiesto -----------------------------------------------------
"$BT/aapt2" compile --dir res -o build/obj/res.zip
"$BT/aapt2" link -o build/apk/sin-alinear.apk \
    -I "$PLAT/android.jar" \
    --manifest AndroidManifest.xml \
    --min-sdk-version 26 --target-sdk-version 34 \
    --version-code 1 --version-name "$VERSION" \
    build/obj/res.zip --auto-add-overlay

# -- El Java (una actividad, sin AndroidX) ------------------------------------
javac -source 11 -target 11 -bootclasspath "$PLAT/android.jar" \
    -d build/obj $(find src -name '*.java')
"$BT/d8" --release --lib "$PLAT/android.jar" --output build/apk \
    $(find build/obj -name '*.class')

# `aapt2 link` ya armó el APK con los recursos; el dex se añade dentro, que es
# lo que Gradle hace por detrás y aquí se hace a la vista.
(cd build/apk && zip -q -j sin-alinear.apk classes*.dex)

# -- Alinear y firmar ----------------------------------------------------------
"$BT/zipalign" -f 4 build/apk/sin-alinear.apk build/apk/alineado.apk

if [ -n "${CORT_APK_KEYSTORE_B64:-}" ]; then
    printf '%s' "$CORT_APK_KEYSTORE_B64" | base64 -d > build/cort.keystore
    KS_PASS="${CORT_APK_KEYSTORE_PASS:-}"
    [ -n "$KS_PASS" ] || { echo "hay keystore pero falta CORT_APK_KEYSTORE_PASS"; exit 1; }
    echo "firmando con la llave del repo (el APK se puede actualizar instalando encima)"
else
    keytool -genkeypair -keystore build/cort.keystore -alias cort \
        -storepass cort -keypass cort -validity 3650 \
        -dname "CN=CORT, OU=prototipo local, O=local" >/dev/null
    KS_PASS="cort"
    echo "firmando con una llave desechable (hay que desinstalar el APK anterior)"
fi

"$BT/apksigner" sign --ks build/cort.keystore \
    --ks-pass pass:"$KS_PASS" --key-pass pass:"$KS_PASS" \
    --out build/CORT.apk build/apk/alineado.apk
"$BT/apksigner" verify build/CORT.apk
ls -l build/CORT.apk
echo "APK listo: build/CORT.apk"
