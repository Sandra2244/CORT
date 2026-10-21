#!/usr/bin/env bash
# Compila el APK de CORT con las herramientas que el runner de GitHub Actions ya
# trae: `aapt2`, `javac`, `d8`, `zipalign`, `apksigner`. Sin Gradle, sin AndroidX,
# sin Capacitor: la dueña tiene un portátil de 1,8 GiB donde un `gradle build` la
# congeló (medido), así que este script **no se ejecuta nunca en el portátil** —
# corre en el pipeline y el artefacto se sube a la Release.
#
# Uso:  bash apps/apk/compilar.sh [versión-del-apk]
#        (por defecto la que lleve escrito APK_VERSION arriba)
# Salida: apps/apk/build/CORT.apk y build/firma.txt
#
# La firma: si el repo tiene el secreto `CORT_APK_KEYSTORE_B64` (el keystore en
# base64) se firma con esa llave y el APK se **actualiza instalando encima**. Sin
# secreto el runner genera una llave desechable, y entonces hay que desinstalar
# el anterior: cada run lo cuenta en `firma.txt`, que viaja al lado del APK,
# porque los registros de Actions no son públicos.
set -euo pipefail
cd "$(dirname "$0")"

APK_VERSION="${APK_VERSION:-1.2.1}"
VERSION="${1:-$APK_VERSION}"

SDK="${ANDROID_HOME:-}"
[ -n "$SDK" ] || SDK="${ANDROID_SDK_ROOT:-}"
if [ -z "$SDK" ] && [ -d /usr/local/lib/android/sdk ]; then
    SDK=/usr/local/lib/android/sdk
fi
[ -n "$SDK" ] || { echo "falta ANDROID_HOME: este script corre en el pipeline, no en el portátil"; exit 1; }

# `versionCode` es el número con el que Android decide si esto **es una
# actualización** o hay que desinstalar para meterlo. Se deriva de la versión:
# 1.2.0 → 1200, 1.2.3 → 1203; algo que no sea `X.Y.Z` vuelve a 1.
case "$VERSION" in
    [0-9]*.[0-9]*.[0-9]*)
        IFS=. read -r MA MI PA <<<"$VERSION"
        CODE=$(( 10#$MA * 10000 + 10#$MI * 100 + 10#$PA ))
        ;;
    *) CODE=1 ;;
esac
[ "$CODE" -ge 1 ] || CODE=1

BT="$( { ls -d "$SDK"/build-tools/*/ 2>/dev/null || true; } | sort -V | tail -1)"
PLAT="$( { ls -d "$SDK"/platforms/*/ 2>/dev/null || true; } | sort -V | tail -1)"
if [ -z "$BT" ] || [ -z "$PLAT" ]; then
    # El runner de GitHub Actions trae el SDK preinstalado; si la imagen alguna vez
    # no lo trae, `sdkmanager` (también viene) descarga lo mínimo. Ni Gradle ni
    # AndroidX: no hacen falta para un `aapt2` + `javac` + `d8`.
    CMDL="$( { ls -d "$SDK"/cmdline-tools/*/bin 2>/dev/null || true; } | head -1)"
    [ -n "$CMDL" ] || { echo "ni SDK ni sdkmanager: el runner cambió de imagen"; exit 1; }
    yes | "$CMDL/sdkmanager" --licenses >/dev/null 2>&1 || true
    "$CMDL/sdkmanager" "platforms;android-34" "build-tools;34.0.0"
    BT="$( { ls -d "$SDK"/build-tools/*/ 2>/dev/null || true; } | sort -V | tail -1)"
    PLAT="$( { ls -d "$SDK"/platforms/*/ 2>/dev/null || true; } | sort -V | tail -1)"
fi
echo "build-tools: $(basename "$BT") · platform: $(basename "$PLAT") · APK $VERSION (código $CODE)"

# -- La cara del teléfono ES la cara del PC ----------------------------------
# `ui/` es la interfaz de este repo (once ventanas, modelos de Ollama,
# optimizador, voz y gestos). Viaja dentro del APK en `assets/ui/` y el WebView
# la sirve bajo `https://cort.local` cortando cada petición en
# `shouldInterceptRequest`. Se copia **aquí**, en el pipeline: el APK siempre
# lleva la interfaz del commit que se etiquetó, y en el portátil no se corre
# ningún `npm` ni ningún `vite` (no hacen falta: la cara son archivos sueltos).
rm -rf assets/ui
mkdir -p assets/ui
[ -f ../../ui/index.html ] || { echo "no está ui/index.html: el repo cambió de forma"; exit 1; }
cp -r ../../ui/. assets/ui/
echo "cara embebida: $(find assets/ui -type f | wc -l) archivos, $(du -sh assets/ui | cut -f1)"

# -- El icono se dibuja con el código de la propia marca (scripts/marca.py) ---
# Nada de assets binarios inventados a mano: el PNG sale del mismo anillo que el
# logo del README y del instalador, y `encode_png` es zlib de la biblioteca base.
python3 - <<'PY'
import pathlib
import sys
# `compilar.sh` ya cambió al directorio `apps/apk`: la marca vive dos niveles arriba.
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

# -- Recursos y manifiesto ---------------------------------------------------
"$BT/aapt2" compile --dir res -o build/obj/res.zip
"$BT/aapt2" link -o build/apk/sin-alinear.apk \
    -I "$PLAT/android.jar" \
    --manifest AndroidManifest.xml \
    -A assets \
    --min-sdk-version 26 --target-sdk-version 34 \
    --version-code "$CODE" --version-name "$VERSION" \
    build/obj/res.zip --auto-add-overlay

# -- El Java (una actividad y el traje de asistente, sin AndroidX) ----------
# `--release 11` con `android.jar` en el classpath y `-encoding UTF-8` porque el
# manifiesto y los mensajes están en español con tildes. `javac` es la única
# prueba que existe de las firmas de `VoiceInteractionSession.onShow` y compañía:
# un `@Override` con una firma que no está en la plataforma no compila.
javac --release 11 -encoding UTF-8 -classpath "$PLAT/android.jar" \
    -d build/obj $(find src -name '*.java')
"$BT/d8" --release --lib "$PLAT/android.jar" --output build/apk \
    $(find build/obj -name '*.class')

# `aapt2 link` ya armó el APK con los recursos; el dex se añade dentro, que es lo
# que Gradle hace por detrás y aquí se hace a la vista.
(cd build/apk && zip -q -j sin-alinear.apk classes*.dex)

# -- Alinear y firmar -------------------------------------------------------
"$BT/zipalign" -f 4 build/apk/sin-alinear.apk build/apk/alineado.apk

if [ -n "${CORT_APK_KEYSTORE_B64:-}" ]; then
    printf '%s' "$CORT_APK_KEYSTORE_B64" | base64 -d > build/cort.keystore
    KS_PASS="${CORT_APK_KEYSTORE_PASS:-}"
    [ -n "$KS_PASS" ] || { echo "hay keystore pero falta CORT_APK_KEYSTORE_PASS"; exit 1; }
    echo "firmando con la llave del repo (el APK se puede actualizar instalando encima)"
else
    # La contraseña tiene 6+ caracteres porque `keytool` lo exige, y hace falta
    # nombrar el algoritmo porque el JDK del runner no trae uno por defecto
    # (medido en runs viejos: "Password too short" y "-keyalg must be specified").
    # Nada de esto es un secreto: la llave vive y muere en el runner.
    keytool -genkeypair -keystore build/cort.keystore -alias cort \
        -keyalg RSA -keysize 2048 \
        -storepass cortapk -keypass cortapk -validity 3650 \
        -dname "CN=CORT, OU=prototipo local, O=local"
    KS_PASS="cortapk"
    echo "firmando con una llave desechable (hay que desinstalar el APK anterior)"
fi

"$BT/apksigner" sign --ks build/cort.keystore \
    --ks-pass pass:"$KS_PASS" --key-pass pass:"$KS_PASS" \
    --out build/CORT.apk build/apk/alineado.apk
"$BT/apksigner" verify build/CORT.apk

# -- Con qué llave salió firmado (se sube a la Release como prueba pública) --
{
    echo "APK de CORT $VERSION (versionCode $CODE), paquete com.cort.ia"
    echo "cara embebida: ui/ de este commit ($(git rev-parse --short HEAD 2>/dev/null || echo '?'))"
    if [ -n "${CORT_APK_KEYSTORE_B64:-}" ]; then
        echo "llave: la del repo (se puede instalar encima de la versión anterior)"
    else
        echo "llave: desechable (hay que desinstalar la versión anterior)"
    fi
    "$BT/apksigner" verify --print-certs build/CORT.apk
} > build/firma.txt
cat build/firma.txt

ls -l build/CORT.apk
echo "APK listo: build/CORT.apk"
