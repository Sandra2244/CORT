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

# Arquitecturas que se empaquetan. Desde `cort-v0.17.1` el default son LAS DOS:
# `arm64-v8a` (el Galaxy A16 de la dueña) y `armeabi-v7a` (cualquier teléfono de
# 32 bits), porque ella lo eligió con estas palabras: «tiene que pesar más, no
# importa». El costo está medido, no estimado: `libcortmotor.so` pesa
# 56 508 296 bytes en arm64 y 46 695 488 en armeabi-v7a, y con las `.so`
# comprimidas (`extractNativeLibs="true"` + `zip -9`, medido en la corrida
# 42115030288) la segunda añade unos 12 MB al APK.
# Para volver al paquete de una sola ABI —el que se bajaba en ~40 KB/s sin
# cortarse— se compila con `CORT_ABIS="arm64-v8a"`.
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

# -- 1. Las dependencias, descargadas y comprobadas ----------------------------
# Cada línea de deps.txt es `nombre|sha256|url`. Se baja a un temporal, se le
# calcula la suma y sólo entonces pasa a su sitio: así un corte de red a medias
# no deja nunca un archivo a medio verificar dentro del APK.
MOTOR=0
DELGADO=0
# Si el modelo de español viaja dentro del APK o se baja en el almacén. Desde
# `cort-v0.17.1` el default es DENTRO (`CORT_OIDO_DENTRO=0` lo saca). La variable
# se usa en la auditoría, así que tiene que existir también en la compilación delgada.
OIDO_EN_APC=0
if [ "${CORT_SIN_MOTOR:-0}" = "1" ]; then
    DELGADO=1
    echo "CORT_SIN_MOTOR=1: se compila el APK DELGADO, sin oído local (el teléfono dictará por el motor de Android)"
fi

# El escáner del QR (zxing) se baja siempre: el enlace con la PC no depende del oído,
# y un APK delgado que no sabe leer el cuadro sería dos pasos para atrás.
while IFS='|' read -r NOMBRE SHA URL; do
    case "$NOMBRE" in ''|'#'*) continue ;; esac
    if [ "$DELGADO" = "1" ] && [ "$NOMBRE" != "zxing-core-3.5.3.jar" ]; then
        continue
    fi
    # El modelo de español SÍ entra en el APK desde `cort-v0.17.1`, y por eso
    # también se baja: la cara del PC dentro del teléfono tiene que oír sin que
    # nadie pulse «Bajar el oído» primero (el servicio de escucha de F19d arranca
    # con la pantalla apagada y no tiene con quién discutir una descarga).
    # `CORT_OIDO_DENTRO=0` devuelve el empaquetado delgado de `cort-v0.16.2`.
    if [ "${CORT_OIDO_DENTRO:-1}" != "1" ] && [ "$NOMBRE" = "vosk-model-small-es-0.42.zip" ]; then
        continue
    fi
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

if [ "$DELGADO" = "0" ]; then
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
    # U1: el cerebro GGUF. `libcortmotor.so` no se compila aquí (esta máquina y este
    # runner no tienen NDK): la compila `motor-local.yml` con el NDK r26d de Google y
    # su artefacto se baja a `vendor/motor/<abi>/`. Si no está, el APK sale sin motor y
    # `CerebroLocal.hayLibreria()` lo dice en la pantalla — no se finge un cerebro que
    # no va, y tampoco se corta una compilación por falta de una corrida ajena.
    MOTOR_JARVIS=0
    for ABI in $ABIS; do
        mkdir -p "build/stage/lib/$ABI"
        # Sólo `libcortmotor.so`, no `*.so`. Medido en la corrida 42025488743 del
        # motor: el artefacto pesa 208 125 998 bytes repartidos en 10 librerías, de
        # las cuales 8 son las compartidas que el CMake de llama.cpp produce de
        # paso (libllama, libggml, libggml-base, libggml-cpu por cada ABI). El
        # pegamento de CORT va enlazado ESTÁTICO y autocontenido — `motor-local.yml`
        # se niega a publicar si en su DT_NEEDED queda `libllama|libggml` — así que
        # aquellas ocho sobran: meterlas costaría ~105 MB más de APK por cero
        # funcionales. Lo que sí va es esta, con sus 56 508 296 (arm64) y
        # 46 695 488 bytes (armeabi).
        for FICHERO in vendor/motor/"$ABI"/libcortmotor.so; do
            [ -e "$FICHERO" ] || continue
            cp "$FICHERO" "build/stage/lib/$ABI/"
            MOTOR_JARVIS=1
            echo "  .so del motor -> $ABI: $(basename "$FICHERO") ($(stat -c%s "$FICHERO") bytes)"
        done
    done
    if [ "$MOTOR_JARVIS" = "0" ]; then
        echo "aviso: no hay libcortmotor.so en vendor/motor/: este APK se compila SIN cerebro GGUF"
    fi

    HAY_NATIVAS=0
    if [ -n "$(find build/stage/lib -name '*.so' -type f 2>/dev/null)" ]; then HAY_NATIVAS=1; fi
    # El modelo de español (39 817 833 bytes) vuelve a entrar en el APK desde
    # `cort-v0.17.1`, porque la escucha en segundo plano no puede empezar por una
    # descarga que nadie pidió. `assets/oido.json` sigue fijando URL, peso y suma
    # para el camino contrario —el del teléfono que ya lo tenía bajado de
    # `cort-v0.16.2`—, y `Motor.java` mira primero el archivo del almacén: si está
    # y cuadra, no se desarma el del APK.
    if [ -f vendor/vosk-android-0.3.75/classes.jar ] \
       && [ -f vendor/jna-5.14.0/classes.jar ] \
       && [ "$HAY_NATIVAS" = "1" ]; then
        if [ "${CORT_OIDO_DENTRO:-1}" = "1" ] && [ -f vendor/vosk-model-small-es-0.42.zip ]; then
            mkdir -p build/recursos/assets/motor
            cp vendor/vosk-model-small-es-0.42.zip build/recursos/assets/motor/
            OIDO_EN_APC=1
        else
            OIDO_EN_APC=0
        fi
        MOTOR=1
    else
        echo "::error::faltó algo del oído (vosk, jna o las .so) y no se puede prometer un dictado local"
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

# -- 2b. La cara de la PC dentro del teléfono ---------------------------------
# Desde `cort-v0.17.1` el APK empaqueta `cort-web/` —el mismo `index.html`, el
# mismo orbe de three.js y los mismos paneles que serve `cort.py --lan` en el
# portátil— en `assets/web/`, y `Nexo.java` lo abre en un `WebView` propio con
# `cort-android.js` como puente. La dueña lo pidió con estas palabras: «necesito
# que sea la copia exacta de la versión de PC incluyendo sus funciones». No es un
# parecido: son los mismos archivos, medidos abajo, y los mismos números.
#
# Qué se copia y qué no, y por qué:
#   `index.html`, `manifest.webmanifest`, `cort-sw.js`  -> la página y su ficha
#   `cort/`   -> la interfaz de CORT (mock, orbe, UI, estilos, vendor de Leaflet)
#   `assets/` -> el bundle de React y su CSS, SIN los `*.orig` (copia de trabajo
#               de una edición anterior: `main-s6G6kMTO.js.orig` pesa 453 154
#               bytes y ningún navegador los pide nunca)
#   `iconos/` -> el logo del manifest y del HUD
#   `wallpapers/` -> la galería del panel de fondo (38 referencias en index.html)
#   `demo/`, `*.md`, `index.html.orig` -> NO: desarrollo y documentación, la
#               página no los carga y en el APK serían peso por peso.
CARA=0
CARA_ARCHIVOS=0
CARA_BYTES=0
WEB="${CORT_WEB_DIR:-../../cort-web}"
if [ -f "$WEB/index.html" ]; then
    mkdir -p build/recursos/assets/web
    cp "$WEB/index.html" "$WEB/manifest.webmanifest" "$WEB/cort-sw.js" build/recursos/assets/web/
    for D in cort assets iconos wallpapers; do
        [ -d "$WEB/$D" ] || continue
        mkdir -p "build/recursos/assets/web/$D"
        cp -a "$WEB/$D/." "build/recursos/assets/web/$D/"
    done
    find build/recursos/assets/web -name '*.orig' -delete
    # El puente Java viaja como primer archivo de la cara: `Nexo.java` inyecta su
    # `<script>` justo detrás de `<head>` cuando sirve `index.html`, y tiene que
    # ser el primero porque `cort-mock.js` guarda `window.WebSocket` en su línea 25.
    cp web/cort-android.js build/recursos/assets/web/cort-android.js
    CARA_ARCHIVOS="$(find build/recursos/assets/web -type f | wc -l)"
    CARA_BYTES="$(du -sb build/recursos/assets/web | cut -f1)"
    if [ "$CARA_ARCHIVOS" -lt 20 ]; then
        echo "::error::la cara de la PC sale con $CARA_ARCHIVOS archivos; algo del 'cort-web' no se copió"
        exit 1
    fi
    CARA=1
    echo "cara del PC empaquetada: $CARA_ARCHIVOS archivos · $CARA_BYTES bytes"
else
    # Sin cara no hay release: `Nexo.hayCaraEmbebida()` mentira en el arranque y
    # la dueña volvería a ver la `Cara.java` nativa, que es exactamente la queja
    # que abrió esta fase. El `delgado` también la lleva: el oído no tiene nada
    # que ver con los archivos de la interfaz.
    echo "::error::no está $WEB/index.html: el APK saldría sin la cara del PC y el teléfono mostraría la cara nativa"
    exit 1
fi

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
CLASSPATH="$PLAT/android.jar:vendor/zxing-core-3.5.3.jar"
# Una sola llamada a `d8`: dos llamadas escribirían `classes.dex` dos veces y la segunda
# traería las clases de la app repetidas (`d8` lo castiga con "Type is already defined").
OIDO=()
if [ "$MOTOR" = "1" ]; then
    CLASSPATH="$CLASSPATH:vendor/vosk-android-0.3.75/classes.jar:vendor/jna-5.14.0/classes.jar"
    OIDO=(vendor/vosk-android-0.3.75/classes.jar vendor/jna-5.14.0/classes.jar)
fi
javac --release 11 -classpath "$CLASSPATH" \
    -d build/obj $(find src -name '*.java')

D8_ENTRADAS="$(find build/obj -name '*.class')"
"$BT/d8" --release --min-api 26 --lib "$PLAT/android.jar" --output build/apk \
    vendor/zxing-core-3.5.3.jar "${OIDO[@]}" $D8_ENTRADAS

(cd build/apk && zip -q -j sin-alinear.apk classes*.dex)

# -- 4. Las bibliotecas nativas, comprimidas ----------------------------------
# Con `android:extractNativeLibs="true"` (manifiesto) el instalador saca las
# `.so` a `/data/app/~~…/lib` antes de cargarlas, y eso permite que viajen con
# deflate. Antes era al revés: `false` obligaba a método 0 + `zipalign -p` y
# por eso el APK de `cort-v0.16.1` pesaba 162 817 475 bytes casi byte por byte
# del contenido, con 103 203 784 de los dos pegamentos GGUF sin comprimir. La
# dueña lo bajó, quedó cortado y Samsung dijo «aplicación no instalada».
#
# Lo que NO cambia: el `.so` del motor sigue dentro del APK. Android 10+ (y el
# target 34 de aquí lo hereda) se niega a cargar librerías ejecutables desde la
# carpeta de datos de la app, así que "bajar libcortmotor.so después" no es una
# opción disponible, por mucho que sea lo que se pediría.
if [ -d build/stage/lib ] && [ -n "$(find build/stage/lib -name '*.so' -type f 2>/dev/null)" ]; then
    (cd build/stage && zip -q -X -9 ../apk/sin-alinear.apk $(find lib -type f))
fi
"$BT/zipalign" -f 4 build/apk/sin-alinear.apk build/apk/alineado.apk

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
# Los números de este archivo se leen en español: separador de miles con espacio
# y coma decimal. `numfmt --grouping` no vale porque el separador que usa depende
# del locale del runner (en Actions es coma; en la laptop, punto), así que se
# agrupa con `sed`, que no pregunta idioma.
AGRUPAR() { echo "$1" | sed -e :a -e 's/\(.*[0-9]\)\([0-9]\{3\}\)/\1 \2/;ta'; }
BYTES_GRUPO="$(AGRUPAR "$BYTES")"
MB="$(awk "BEGIN{printf \"%.2f\", $BYTES/1048576}" | tr '.' ',')"
{
    echo "APK móvil de CORT $VERSION (versionCode $CODE)"
    echo "peso: $BYTES_GRUPO bytes ($MB MB)"
    if [ "$MOTOR" = "1" ]; then
        if [ "$OIDO_EN_APC" = "1" ]; then
            echo "oído: Vosk dentro del APK (modelo español pequeño, sin red)"
        else
            echo "oído: Vosk con el modelo español bajado en el almacén (39 817 833 bytes fuera del APK)"
        fi
    else
        echo "oído: el motor de voz del aparato (APK delgado, CORT_SIN_MOTOR=1)"
    fi
    echo "visor: zxing core 3.5.3 dentro del APK (escanea el QR del enlace, F14b)" \
         "— $(stat -c%s vendor/zxing-core-3.5.3.jar) bytes fijados en deps.txt"
    echo "cara: la del PC embebida (F19) — $CARA_ARCHIVOS archivos y $(AGRUPAR "$CARA_BYTES") bytes descomprimidos en assets/web/, abiertos en el WebView por Nexo.java"
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
    python3 - build/CORT-movil.apk "$ABIS" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
# Las ABIs empaquetadas son las que pidió `compilar.sh`, no una lista fija: con
# el default nuevo (`arm64-v8a`) exigir la de 32 bits daría un "no está" falso.
for abi in sys.argv[2].split():
    for nombre in ("libvosk.so", "libjnidispatch.so", "libcortmotor.so"):
        ruta = "lib/%s/%s" % (abi, nombre)
        info = z.getinfo(ruta) if ruta in z.namelist() else None
        if info is None:
            print(ruta + ": no está en el APK")
            continue
        # Con `extractNativeLibs="true"` lo bueno es que estén comprimidas: el
        # instalador las descomprime a /data/app/…/lib y ahí el sistema las carga.
        metodo = {0: "sin comprimir", 8: "deflate"}.get(info.compress_type, "?")
        ahorrado = info.compress_type != 0 and info.compress_size < info.file_size
        print("%s: %d bytes -> %d en el APK (%s%s)" % (
            ruta, info.file_size, info.compress_size, metodo,
            ", ok" if ahorrado else ""))
arsc = z.getinfo("resources.arsc")
print("resources.arsc: %d bytes · %s" % (arsc.file_size,
      "SIN COMPRIMIR (ok)" if arsc.compress_type == 0 else "comprimido (Android 11 lo pide suelto)"))
tot = sum(i.file_size for i in z.infolist())
guard = sum(i.compress_size for i in z.infolist())
print("entradas: %d · descomprimido suma %d bytes · dentro del APK %d bytes"
      % (len(z.infolist()), tot, guard))
# Ningún GGUF viaja en el APK (decisión fija de U1: se baja en el almacén). Si un día
# alguien lo mete aquí, esta línea lo grita en la auditoría antes que en el teléfono.
gguf = [i.filename for i in z.infolist() if i.filename.lower().endswith(".gguf")]
print("gguf dentro del APK: %s" % (", ".join(gguf) if gguf else "ninguno (ok)"))
# El modelo de español vuelve dentro del APK desde `cort-v0.17.1` (la escucha en
# segundo plano no puede depender de una descarga que nadie pidió). El número de
# esta línea es el que lee la release (`apk-movil.yml`) para decir si hace falta
# bajar algo una vez instalado.
oido_zip = [i for i in z.infolist() if i.filename.startswith("assets/motor/")]
oido_ficha = z.read("assets/oido.json").decode("utf-8") if "assets/oido.json" in z.namelist() else ""
if oido_zip:
    print("modelo de español: %d bytes DENTRO del APK (el teléfono oye nada más instalar)"
          % sum(i.file_size for i in oido_zip))
else:
    import json
    peso = json.loads(oido_ficha)["bytes"] if oido_ficha else 0
    print("modelo de español: %d bytes fuera del APK (se baja en el almacén)" % peso)
print("assets/oido.json: %s" % ("%d bytes · el almacén sabe de dónde bajar el oído"
                                % len(oido_ficha.encode()) if oido_ficha
                                else "NO ESTÁ: la app no sabría de dónde bajar el oído"))
cerebros = z.read("assets/cerebros.json").decode("utf-8") if "assets/cerebros.json" in z.namelist() else ""
print("assets/cerebros.json: %d bytes · %d cerebros ofrecidos"
      % (len(cerebros.encode()), cerebros.count('"id"')))
# F19: la cara de la PC. Se comprueba contra el archivo FINAL, no contra la
# carpeta de etapa: si el `aapt2 link` se hubiera comido `assets/web/` (con `-A`
# mal puesto esto es exactamente lo que pasa), el teléfono abriría la cara nativa
# y la auditoría diría "está" mirando un directorio que ya no existe.
cara = [i for i in z.infolist() if i.filename.startswith("assets/web/")]
if cara:
    print("cara del PC: %d archivos · %d bytes descomprimidos · %d bytes dentro del APK"
          % (len(cara), sum(i.file_size for i in cara), sum(i.compress_size for i in cara)))
    for necesario in ("assets/web/index.html", "assets/web/cort-android.js",
                      "assets/web/cort/cort-mock.js", "assets/web/cort/cort-ui.js",
                      "assets/web/cort/cort-orbe.js", "assets/web/manifest.webmanifest"):
        print("  %s: %s" % (necesario,
              "está (%d bytes)" % z.getinfo(necesario).file_size
              if necesario in z.namelist() else "NO ESTÁ"))
    # El bundle de React va con el hash de Vite en el nombre, así que se busca por
    # prefijo: exigir `main-s6G6kMTO.js` literal daría un "NO ESTÁ" falso la próxima
    # vez que alguien recompila la cara.
    for prefijo in ("assets/web/assets/main-", "assets/web/assets/three.module-"):
        hay = [i for i in cara if i.filename.startswith(prefijo) and i.filename.endswith(".js")]
        print("  %s*.js: %s" % (prefijo,
              "está (%d bytes)" % hay[0].file_size if hay else "NO ESTÁ"))
    sobrantes = [i.filename for i in cara if i.filename.endswith(".orig")]
    print("  copias .orig dentro de la cara: %s"
          % (", ".join(sobrantes) if sobrantes else "ninguna (ok)"))
else:
    print("cara del PC: NO ESTÁ en el APK — el teléfono mostraría Cara.java, no la interfaz del portátil")
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

echo "peso: $BYTES_GRUPO bytes ($MB MB)"
# El nombre que se anota es el **desnudo**. Medido en el run 41881069892: con
# `sha256sum build/CORT-movil.apk` el archivo quedaba como
# `…  build/CORT-movil.apk`, y al bajar el APK suelto de la release
# `sha256sum -c` respondía «No existe el fichero o el directorio» aunque la suma
# fuera buena. La dueña comprueba así, según el propio README: el `-c` tiene que
# funcionar sin tener que reescribir el archivo a mano.
(cd build && sha256sum CORT-movil.apk) | tee build/CORT-movil.apk.sha256
echo "APK listo: build/CORT-movil.apk"
