#!/usr/bin/env bash
# Rempaqueta el APK del teléfono: el **cuerpo es el APK original de CORT**
# (`apps/apk/base/CORT-IA-1.1.0.apk`, 1,8 MB, Kotlin + 4 dex + su icono de
# anillo adaptativo) y lo único que se cambia es la **interfaz que lleva
# dentro**: `assets/ui/`, que se sustituye por `ui/` de este commit (las once
# ventanas, incluidas 10 · Modelos y 11 · Optimizar). Después hay que volver a
# alinear y volver a firmar, porque tocar un entry rompe la firma anterior.
#
# Por qué por-binario y no desde el código: el proyecto Android que generó ese
# APK (Gradle + Capacitor, con su `app/build.gradle` y sus `.kt`) **no está en
# este repo**; lo que está es el binario que la dueña instaló en el teléfono.
# Recompilar desde cero ese cuerpo exigiría ese proyecto. Meterle la cara nueva
# encima no: `zip` + `zipalign` + `apksigner`, y eso lo trae el runner.
#
# Se comprobó antes de escribir este script (diff real contra los assets del
# binario): `android-bridge.js`, `voice.js`, `orb.js`, `gestures.js`,
# `windows.js` y `vendor/three.module.js` son byte a byte los mismos; sólo
# cambian `hud.js`, `index.html`, `hud.css` e `icons.js`. El puente nativo que
# usa la cara (`CortNative.listen/stopListening/bgStatus/setBackground/
# keepAwake`) tampoco cambió, así que el Kotlin de dentro sigue entendiendo el
# JavaScript nuevo.
#
# Uso:   rempaquetar.sh [versión-salida]     (por defecto 1.1.1)
# Salida: apps/apk/build/CORT-IA-<versión>.apk  +  build/CORT-IA-<versión>-firma.txt
#
# La llave: igual que `compilar.sh`. Con el secreto `CORT_APK_KEYSTORE_B64` del
# repo se firma con esa llave y el APK se actualiza encima; sin secreto se
# genera una desechable, y entonces **hay que desinstalar el anterior** (para
# Android una firma distinta es otra aplicación). Se dice en `firma.txt`, que
# viaja al lado del APK en la Release.
set -euo pipefail
# El script vive en `apps/apk/` y las rutas de abajo (`apps/apk/base/…`, `ui`)
# están escritas **desde la raíz del repo**, así que se sube dos niveles: con uno
# solo te quedas en `apps/` y el primer `ls` busca `apps/apps/apk/base` — así
# cayó el run 39504821879, medido por annotation.
cd "$(dirname "$0")/../.."

VERSION="${1:-1.1.1}"
RAIZ="$(pwd)"
BASE="$RAIZ/apps/apk/base/CORT-IA-1.1.0.apk"
# `SALIDA` va absoluta **a propósito**: el trabajo se hace dentro de un
# `mktemp -d` y, con ruta relativa, `apksigner --out` escribiría dentro del
# directorio temporal (que el `trap` borra) en vez de en `apps/apk/build/`.
SALIDA="$RAIZ/apps/apk/build/CORT-IA-${VERSION}.apk"
CARA="$RAIZ/ui"

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [ -z "$SDK" ] && [ -d /usr/local/lib/android/sdk ]; then
    SDK=/usr/local/lib/android/sdk
fi
BT="$( { ls -d "$SDK"/build-tools/*/ 2>/dev/null || true; } | sort -V | tail -1)"
[ -n "$BT" ] || { echo "falta el SDK de Android (zipalign/apksigner): esto corre en el pipeline"; exit 1; }
export PATH="$BT:$PATH"

command -v zip       >/dev/null || { echo "falta zip"; exit 1; }
command -v zipalign  >/dev/null || { echo "falta zipalign en $BT"; exit 1; }
command -v apksigner >/dev/null || { echo "falta apksigner en $BT"; exit 1; }
[ -f "$BASE" ]        || { echo "no está la base: $BASE"; exit 1; }
[ -f "$CARA/index.html" ] || { echo "no está la interfaz: $CARA/index.html"; exit 1; }
mkdir -p apps/apk/build

TRABAJO="$(mktemp -d)"
trap 'rm -rf "$TRABAJO"' EXIT

# 1 · Copiar el cuerpo original y meterle la cara de este commit.
cp "$BASE" "$TRABAJO/CORT.apk"
mkdir -p "$TRABAJO/assets"
cp -r "$CARA" "$TRABAJO/assets/ui"

cd "$TRABAJO"
# La firma vieja (v1 vive en META-INF/*.SF|*.RSA|MANIFEST.MF) tiene que salir
# antes de la nueva o el instalador de Android ve dos firmas y rechaza el APK.
zip -q -d CORT.apk 'META-INF/*' >/dev/null 2>&1 || true
zip -q -d CORT.apk 'assets/ui/*' >/dev/null 2>&1 || true
zip -q -X -r CORT.apk assets/ui

# 2 · Alinear (obligatorio antes de firmar con v2/v3) y firmar.
zipalign -f 4 CORT.apk alineado.apk

COCO="$TRABAJO/cort.keystore"
if [ -n "${CORT_APK_KEYSTORE_B64:-}" ]; then
    echo "$CORT_APK_KEYSTORE_B64" | base64 -d > "$COCO"
    PASS="${CORT_APK_KEYSTORE_PASS:?con CORT_APK_KEYSTORE_B64 hace falta CORT_APK_KEYSTORE_PASS}"
    ORIGEN="la llave del secreto CORT_APK_KEYSTORE_B64"
    ACTUALIZA="sí: se puede instalar encima del anterior"
else
    keytool -genkeypair -keystore "$COCO" -storepass cort-tmp -alias CORT \
            -keyalg RSA -keysize 2048 -validity 30 \
            -dname "CN=CORT, OU=prototipo local, O=local" >/dev/null
    PASS="cort-tmp"
    ORIGEN="una llave desechable de este run"
    ACTUALIZA="no: hay que desinstalar la versión anterior"
fi
apksigner sign --ks "$COCO" --ks-pass pass:"$PASS" \
    --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
    --out "$SALIDA" alineado.apk
apksigner verify --print-certs "$SALIDA" >/dev/null

cd "$RAIZ"
{
    echo "APK del teléfono ${VERSION} (paquete com.cort.ia)"
    echo "cuerpo:  el APK original CORT-IA-1.1.0, sin recompilar (el proyecto Gradle que lo generó no está en este repo)"
    echo "cara:    ui/ de este commit, metida en assets/ui/ ($(find "$CARA" -type f | wc -l) archivos, $(du -sh "$CARA" | cut -f1) sin comprimir)"
    echo "firma:   $ORIGEN — actualizar instalando encima: $ACTUALIZA"
    echo "tamaño:  $(stat -c %s "$SALIDA") bytes"
    apksigner verify --print-certs "$SALIDA"
} > "apps/apk/build/CORT-IA-${VERSION}-firma.txt"

echo "== rempaquetado: $(ls -l "$SALIDA" | awk '{print $5" bytes"}')  (base $(stat -c %s "$BASE") bytes)"
python3 - "$SALIDA" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
n = z.namelist()
ui = [x for x in n if x.startswith('assets/ui/')]
print('   entradas:', len(n), '· dex:', sum(1 for x in n if x.endswith('.dex')),
      '· assets/ui:', len(ui), '(%d KB sin comprimir)' % (sum(z.getinfo(x).file_size for x in ui)//1024))
print('   icono original conservado:', sum(1 for x in n if 'mipmap' in x), 'archivos')
PY
