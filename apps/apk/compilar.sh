#!/usr/bin/env bash
# Compila el APK de CORT con las herramientas que el runner de GitHub Actions ya
# trae: `aapt2`, `javac`, `d8`, `zipalign`, `apksigner`. Sin Gradle y sin
# Capacitor: la dueña tiene un portátil de 1,8 GiB donde un `gradle build` la
# congeló (medido), así que este script **no se ejecuta nunca en el portátil** —
# corre en el pipeline y el artefacto se sube a la Release.
#
# Es el mismo método con el que está hecho el APK original del teléfono: `aapt2`
# para los recursos, `d8` para el dex, `zipalign` + `apksigner` para firmar. Lo
# que Gradle orquesta por detrás se hace aquí a la vista. Desde el 2.3.0 el
# proyecto es además **mixto Java + Kotlin**, otra vez igual que el original:
# `Oido.java` (el oído offline) está escrito en Kotlin y se compila con
# `kotlinc` descargado en el propio pipeline. Ver el bloque de Kotlin abajo.
#
# Uso:  bash apps/apk/compilar.sh [versión-del-apk]
#        (por defecto la que lleve escrito APK_VERSION arriba)
# Salida: apps/apk/build/CORT.apk y build/firma.txt
#
# La firma: la resuelve `apps/apk/llave.sh` en este orden — secreto
# `CORT_APK_KEYSTORE_B64` del repo, la llave guardada en la caché de Actions
# (`apps/apk/keystore`, paso `Cachear la llave de firma` de `build.yml`), o una
# nueva que se deja en esa carpeta para que el siguiente run la reencuentre.
# Con la misma llave en todas las Releases el APK **se actualiza instalando
# encima**; con llaves distintas hay que desinstalar, y al desinstalar se van los
# permisos concedidos y la dirección del PC. Cada run escribe cuál usó en
# `firma.txt`, que viaja al lado del APK, porque los registros de Actions no son
# públicos.
set -euo pipefail
cd "$(dirname "$0")"

# La entrega «todo en uno»: UN solo APK con la cara embebida, el reproductor con
# su `MediaSession`, los avisos leídos en voz, el modo juego, el MV con letra, el
# mando del aparato (volumen, linterna, alarma, temporizador, abrir apps, voces
# del TTS, memoria en SQLite, cerebro en la nube, atuendos) y —desde el 2.3.0—
# el oído y la voz que viven DENTRO del teléfono.
#
# El 2.2.0 añadió el cerebro ancho: `Razon` responde cuentas, porcentajes,
# unidades y fechas sin portátil ni nube; la tabla de frases pasa a 33 generadas
# por `scripts/habilidades.py` (283 frases, cada una probada en el JDK);
# `Aparato` y `Sentidos` dan el entorno real por el puente, y la cámara pide su
# permiso en vez de fallar en silencio. `docs/INSTALAR-APK.md` explica el error
# de instalación que da al saltar de 1.x a 2.x: es la llave de firma distinta,
# no el APK roto.
#
# El 2.3.0 es la ronda del peso CON función: `Oido` (Kotlin) con Vosk y su
# modelo de español de 39.817.833 B, `Habla` con los avisos sonoros del propio
# CORT, y los `.so` de `apps/apk/motor.sh` empaquetados a mano. Ahí están los
# ~45 MB que faltaban, no en relleno.
#
# El 2.3.1 no añade funciones: es la ronda de **que se pueda instalar**. La dueña
# reportó que Google/Play Protect le bloquea el APK. Antes de tocar nada se MIDIO
# el `CORT-IA-2.3.0.apk` publicado (bajado y leído byte a byte): sale con firma
# v1+v2+v3, certificado RSA 2048 vigente hasta 2056 y `resources.arsc` sin
# comprimir y alineado. O sea: el APK no está roto, es el aviso de Google a
# cualquier app con certificado auto-firmado y fuera de Play. Lo que sí se puede
# hacer desde aquí es (1) no dejar ningún esquema de firma al azar del `minSdk` y
# (2) que cada Release publique la auditoría de instalabilidad, para poder
# comprobar el archivo que llega al teléfono en vez de suponerlo. La guía de
# toques por mensaje está en `docs/BLOQUEO-PLAY-PROTECT.md`.
#
# El 2.4.0 es la ronda del **cerebro de casa y las reglas**. Tres funciones nuevas,
# todas con su prueba antes de firmar:
#
# · `Ollama.java` — el teléfono habla con el Ollama del PC por Wi-Fi (buscar, listar,
#   bajar con su barra, borrar, y pensar con ese modelo: `usa` escribe las cuatro
#   claves que lee `Nube`, así que la respuesta llega con `de:"casa"`, sin clave y
#   sin internet). Ollama NO cabe dentro del APK: es un servidor en Go que pide
#   Linux; lo que va dentro es su cliente. Cero permisos nuevos —el barrido de la
#   red sale de `NetworkInterface`, no de `WifiInfo`.
# · La terminal **ampliada en el teléfono** (`terminalTelefono`): la pantalla Código
#   manda las órdenes por el puente (volumen, linterna, apps, avisos, modelos) y, si
#   no hay portátil, el `Mente` del teléfono contesta con sus propios cerebros. El
#   eco de todo se lee en la misma consola.
# · `automatiza.js` — las reglas «cuando X, entonces Y» (hoja Equipo · 8), con las
#   señales que ya existen: su frase, el aviso nuevo `{type:"aviso"}` que manda
#   `.Avisos`, el auricular, la batería y la hora. El motor es puro y se prueba con
#   node (45 comprobaciones); lo que no puede hacer, lo dice la propia hoja: las
#   reglas se cumplen mientras CORT está en pantalla.
# · En 2.8.0 llega el **aviso de bajada**: cuando el modelo termina —o cuando se
#   corta— sale una notificación normal de `NotificationManager` (canal
#   `cort-modelos`), así que la hoja de Modelos se puede cerrar y el teléfono se
#   puede bloquear. Lo pone `Timbre.java`, fichero nuevo, y NO `Ollama.java`: ese se
#   compila y se prueba en el portátil con el JDK (`scripts/prueba-mente.sh`), donde
#   un `NotificationManager` de verdad no existe, y ahí entra su gemelo de papel.
#   Cero permisos nuevos: `POST_NOTIFICATIONS` ya estaba desde el reproductor, y
#   seguir metiendo superficie en el manifiesto es lo que rechazaba Play Protect.
# · En 2.9.0 la bajada del teléfono se vuelve de fiar (F13): `descarga()` hace un
#   `GET /api/version` ANTES de abrir `POST /api/pull` —un PC dormido se cortaba en
#   90 s con un timeout mudo; ahora son ~3 s con un aviso que nombra `OLLAMA_HOST`—,
#   el progreso se **suma por `digest`** (antes la última capa ganaba y la barra
#   quedaba quieta: eso era el «no descarga los modelos»), hay `cancela()` que cierra
#   la corriente bloqueada por el puente de siempre (`mente({que:'ollama',
#   accion:'cancela'})`), y mientras baja otro modelo se rechaza la segunda orden.
#   Cero permisos y cero métodos nuevos en el puente: la cancelación entra por la
#   acción que ya existedía, así que el manifiesto del `nucleo` no se toca.
# · En 2.10.0 se cierra el lote F12 + F14–F17: la voz responde con ducking y teclas
#   del sistema (F12), el diccionario único de ~91 intenciones / 736 frases (F14),
#   la música por nombre con listas y ecualizador (F15), el despertador propio con
#   canción, nota y rutina (F16) y la cara vestida —orbe de 16 canales, burbuja
#   1.1.4 arrastrable y agua con freno— (F17). Cero permisos nuevos y ningún
#   cambio en el contrato de cinco argumentos para hablar.
APK_VERSION="${APK_VERSION:-2.10.0}"   # desde aquí sale UN SOLO APK: este
VERSION="${1:-$APK_VERSION}"

# ── LA VARIEDAD LIGERA (`APK_SIN_OIDO=1`) ────────────────────────────────────
# La dueña reportó el 2026-10-22: «aplicación bloqueada para proteger tu
# dispositivo» con el 2.4.1, pero el `1.1.4` — que es mío, misma forma de firmar
# y **los mismos permisos gordos** (`MANAGE_EXTERNAL_STORAGE`,
# `SYSTEM_ALERT_WINDOW`, `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`, medidos entrada por
# entrada en su `AndroidManifest.xml`) — se le instala bien. Entonces el aviso
# **no** es de permisos ni de llave: queda como sospechoso lo único que pesa de
# verdad en el 2.x, que son los 45,7 MB del oído (`libvosk.so` +
# `libjnidispatch.so` + JNA + el modelo de español dentro del APK). Para saberlo
# con una sola prueba hace falta un APK **idéntico en todo lo demás y sin ese
# bulto**: con esta bandera el `aapt2`, el `javac`, el `d8`, el manifiesto, la cara
# y la llave son los mismos; lo que no se mete son las `.so`, las clases de
# Vosk/JNA en el dex y el ZIP del modelo. CORT arranca igual y el oído dice
# `sin-modelo` — que ya estaba previsto en `Oido.kt` y en la hoja Equipo —, así que
# escucha con el reconocedor del sistema. NO es una trampa: la Release sube los dos
# archivos y cada `-firma.txt` declara cuál de las dos variedades es.
#
# **Y la hipótesis de este bloque cayó**: ella probó los dos el 2026-10-22 y «los dos
# fallan, Play Protect sigue bloqueando». El peso no era. Lo que queda en pie es lo
# que se midió después leyendo los manifiestos binarios — ver el bloque del PERFIL
# abajo —, y por eso la 2.5 sube la variedad ligera **y** los dos perfiles.
SIN_OIDO="${APK_SIN_OIDO:-0}"

SDK="${ANDROID_HOME:-}"
[ -n "$SDK" ] || SDK="${ANDROID_SDK_ROOT:-}"
if [ -z "$SDK" ] && [ -d /usr/local/lib/android/sdk ]; then
    SDK=/usr/local/lib/android/sdk
fi
[ -n "$SDK" ] || { echo "falta ANDROID_HOME: este script corre en el pipeline, no en el portátil"; exit 1; }

# `versionCode` es el número con el que Android decide si esto **es una
# actualización** o hay que desinstalar para meterlo. Se deriva de la versión con
# `MA*10000 + MI*100 + PA`: 1.0.2 → 10002, 2.0.0 → 20000; algo que no sea
# `X.Y.Z` vuelve a 1. Con esa fórmula 2.3.1 (20301) queda por delante del 2.3.0
# (20300) y del 2.2.0 (20200), así que se instala ENCIMA sin desinstalar (con la
# misma llave de `llave.sh`).
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
    # El runner de GitHub Actions trae el SDK preinstalado; si la imagen alguna
    # vez no lo trae, `sdkmanager` (también viene) descarga lo mínimo. Ni Gradle
    # ni AndroidX: no hacen falta para un `aapt2` + `javac` + `d8`.
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
# La sonda del taller NO viaja. `ui/sonda-carita.html` se abre en el navegador del
# portátil contra el servidor de la cara; dentro del teléfono no tiene quién la abra,
# porque la cara es un `WebView` sin barra de direcciones, y son 26.424 B sobre los
# 1.658.269 B del `nucleo-ligero` (el 1,6 % del envase). Como arriba se copia `ui/.`
# entero —que es lo que hace que `css/apps.css` viaje sin que nadie lo anuncie—, la
# sonda se saca aquí con un patrón y no con una lista de nombres: la regla de la casa
# es ningún byte que no haga algo en el aparato.
find assets/ui -maxdepth 1 -name 'sonda-*.html' -delete
echo "cara embebida: $(find assets/ui -type f | wc -l) archivos, $(du -sh assets/ui | cut -f1)"

# -- El oído propio: Vosk, JNA y su modelo de español ------------------------
# Todo lo que mide, baja y coloca `apps/apk/motor.sh` (pesos y huellas verificados
# ahí dentro). Si la descarga o la comprobación de tamaño falla, ESTE BUILD SE PARA,
# y ya no hay salida: desde la ronda 2.3 `CortNative.java` llama a `Oido` y
# `AndroidManifest` lleva las `.so`, así que un APK sin el motor **no compila** — no
# es que salga peor, es que no sale. Una Release que anunciara «oído sin nube» sin
# el motor dentro habría sido una mentira escrita en el nombre de la versión, y lo
# mismo vale al revés: se prefiere una Run roja y la Release vieja en pie antes que
# un instalador que promete lo que no trae.
bash motor.sh "${MOTOR_CACHE:-motor-cache}"
[ -f build/motor/jar/vosk.jar ] || { echo "motor.sh no dejó build/motor/jar/vosk.jar"; exit 1; }
[ -f build/motor/lib/arm64-v8a/libvosk.so ] || { echo "motor.sh no dejó las .so de arm64-v8a"; exit 1; }
[ -f "assets/motor/$(cat build/motor/modelo-nombre.txt).zip" ] || { echo "falta el modelo en assets/motor"; exit 1; }
HAY_MOTOR=1

# `HAY_MOTOR` dice si los `.jar` están para COMPILAR (hacen falta incluso en la
# variedad ligera: `Oido.kt` se compila contra ellos). `META_MOTOR` dice si el motor
# **viaja dentro del APK**: con `APK_SIN_OIDO=1` se quitan las `.so`, el ZIP del
# modelo y las clases de Vosk/JNA del dex, y no queda ni un rastro del subsistema.
# Así la prueba de Play Protect es de una sola variable: mismo manifiesto, misma
# llave, misma cara, y lo único que cambia es el bulto nativo.
META_MOTOR=1
if [ "$SIN_OIDO" = "1" ]; then
    META_MOTOR=0
    ENTRO="$(du -sb assets/motor | cut -f1)"
    rm -rf assets/motor
    echo "variedad LIGERA: fuera el modelo ($ENTRO B) y fuera las .so del motor"
fi

# -- El icono es EL DE SIEMPRE: se saca del APK original de la dueña ------------
# Desde `v0.2.11-demo` sólo existe este APK, así que tiene que parecerse al que
# ella tiene en el cajón de aplicaciones: mismo anillo, mismo fondo casi negro.
# `base/CORT-IA-1.1.0.apk` guarda el icono adaptativo real — `ic_launcher.png`
# (el plano, 48/72/96/144/192 px por densidad), `ic_launcher_round.png` y
# `ic_launcher_foreground.png` (432 px en xxxhdpi, con alpha) —, y el fondo del
# adaptativo se midió en la propia imagen: `#02040A`.
#
# El plan B (`scripts/marca.py`, el anillo dibujado con código) se queda por si
# algún día el `base/` no viene en el checkout: el pipeline no se tira.
if [ -f base/CORT-IA-1.1.0.apk ]; then
    rm -rf build-iconos
    mkdir -p build-iconos
    if unzip -o -q base/CORT-IA-1.1.0.apk 'res/mipmap-*-v4/*.png' -d build-iconos; then
        Hay_Anillo=0
        for d in mdpi hdpi xhdpi xxhdpi xxxhdpi; do
            src="build-iconos/res/mipmap-$d-v4"
            [ -d "$src" ] || continue
            mkdir -p "res/mipmap-$d"
            for n in ic_launcher ic_launcher_round ic_launcher_foreground; do
                if [ -f "$src/$n.png" ]; then
                    cp "$src/$n.png" "res/mipmap-$d/$n.png"
                    [ "$n" = "ic_launcher_foreground" ] && Hay_Anillo=1
                fi
            done
        done
        if [ "$Hay_Anillo" = "1" ]; then
            # El XML del icono adaptativo del base APK está en AXML binario (no se
            # puede copiar como texto), así que se escribe su equivalente: fondo de
            # color + el foreground original recortado por la máscara del sistema.
            mkdir -p res/mipmap-anydpi-v26 res/values
            for nombre in ic_launcher ic_launcher_round; do
                cat > "res/mipmap-anydpi-v26/$nombre.xml" <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@mipmap/ic_launcher_foreground" />
</adaptive-icon>
XML
            done
            cat > res/values/colores-icono.xml <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#02040A</color>
</resources>
XML
            # `ic_launcher_round` también necesita su PNG donde no haya XML que lo
            # sustituya: si el original no lo trae, se usa el cuadrado y listo.
            for d in mdpi hdpi xhdpi xxhdpi xxxhdpi; do
                if [ -d "res/mipmap-$d" ] && [ ! -f "res/mipmap-$d/ic_launcher_round.png" ]; then
                    cp "res/mipmap-$d/ic_launcher.png" "res/mipmap-$d/ic_launcher_round.png"
                fi
            done
            echo "icono: el anillo original del base APK, 5 densidades + adaptativo"
        else
            echo "icono: el base APK no trae foreground, se dibuja con marca.py"
        fi
    fi
    if [ ! -f res/mipmap-xxxhdpi/ic_launcher_foreground.png ]; then
        rm -rf res/mipmap-* res/mipmap-anydpi-v26 res/values/colores-icono.xml
        python3 - <<'PY'
import pathlib
import sys
sys.path.insert(0, "../../scripts")
from marca import render, encode_png
for carpeta, dim in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96),
                     ("xxhdpi", 144), ("xxxhdpi", 192)):
    d = pathlib.Path("res") / f"mipmap-{carpeta}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "ic_launcher.png").write_bytes(encode_png(dim, render(dim)))
    (d / "ic_launcher_round.png").write_bytes(encode_png(dim, render(dim)))
print("iconos de marca generados (5 densidades, plan B)")
PY
    fi
    rm -rf build-iconos
else
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
    (d / "ic_launcher_round.png").write_bytes(encode_png(dim, render(dim)))
print("iconos de marca generados (5 densidades): no está base/CORT-IA-1.1.0.apk")
PY
fi

rm -rf build/obj build/apk
mkdir -p build/obj build/apk

# -- El PERFIL del manifiesto (`APK_PERFIL=completo|nucleo`) ------------------
# Ronda 2.5. La bisección de la 2.4.2 mató la hipótesis del peso: los dos APK de
# aquella ronda se bloquearon igual, y el `LIGERO` no llevaba ni `.so` ni modelo.
# Medido el 2026-10-22 en este portátil, leyendo el `AndroidManifest.xml` binario
# (la charca de cadenas UTF-16) de los tres APK que hay en el mismo disco:
#
#   APK                      usa-perm  servicios BIND_*  se instala
#   CORT-IA-1.1.0 (el de ella)   13            0            sí
#   CORT-IA-1.1.4 (el mío)       13            0            sí
#   CORT-IA-2.4.2-ligero         24          5 (`BIND_VOICE_INTERACTION`,
#                                  `BIND_SPEECH_RECOGNIZER`, `BIND_NOTIFICATION_
#                                  LISTENER_SERVICE`, `BIND_QUICK_SETTINGS_TILE`)   no
#
# Y las cuatro Gordas que se señalaban (`MANAGE_EXTERNAL_STORAGE`,
# `SYSTEM_ALERT_WINDOW`, `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`,
# `READ_EXTERNAL_STORAGE`) están en los TRES: no son la diferencia. Lo que el 1.1.4
# no declara y el 2.4.2 sí son los cinco servicios privilegiados, las acciones
# `ACTION_ASSIST`/`ACTION_VOICE_COMMAND` y el trío `CALL_PHONE` + `READ_CONTACTS` +
# `READ_CALENDAR`. Ese paquete es, literalmente, cómo describen los clasificadores
# automáticos un troyano de accesibilidad.
#
# `perfil.py` corta esas regiones y clava la meta-datos `com.cort.ia.PERFIL`, así
# que el teléfono prueba UNA sola variable: `nucleo` es la misma CORT de siempre con
# la superficie del 1.1.4 (21 permisos normales, CERO servicios privilegiados), y
# `completo` es lo que ya está publicado. Con `nucleo` no hay que elegir un recorte
# a mano ni romper nada: lo que la cara no puede ofrecer, lo dice `capacidades()`.
PERFIL="${APK_PERFIL:-completo}"
MANIFIESTO="build/manifest-$PERFIL.xml"
python3 perfil.py --perfil "$PERFIL" --salida "$MANIFIESTO" || exit 1

# -- Recursos y manifiesto ---------------------------------------------------
"$BT/aapt2" compile --dir res -o build/obj/res.zip
"$BT/aapt2" link -o build/apk/sin-alinear.apk \
    -I "$PLAT/android.jar" \
    --manifest "$MANIFIESTO" \
    -A assets \
    --min-sdk-version 26 --target-sdk-version 34 \
    --version-code "$CODE" --version-name "$VERSION" \
    build/obj/res.zip --auto-add-overlay

# -- Kotlin: la pata nueva, con el método del APK original -------------------
# `Oido` (el oído offline) está escrito en Kotlin porque **el 1.1.0 de la dueña
# también lo está**: sus cuatro `classes*.dex` arrastraban 3.986 cadenas
# `kotlin` y 919.207 B de runtime Kotlin (medido entrada por entrada). La
# diferencia entre los 1.815.389 B de aquel y los ~998.000 B de este 2.2.0 no
# era compresión ni funciones quitadas: era ese runtime. Compilar como él compila
# —Kotlin+Java sobre `d8`, sin Capacitor ni AndroidX— es lo que ella pidió, y no
# cuesta cambiar el cuerpo que ya funciona: `kotlinc` acepta fuentes `.java` en
# el mismo lote y sabe compilarlos contra los `.kt`.
#
# La versión va FIJA (K2/1.9.24, la línea LTS con la que se construye la
# mayoría de apps de Android hoy) y el zip se cachea en Actions. Si algún día no
# se puede bajar, `MOTOR=off` y el Kotlin se omite: el pipeline avisa en vez de
# callarse.
KOTLIN_VERSION="${KOTLIN_VERSION:-1.9.24}"
KOTLIN_DIR="${KOTLIN_DIR:-$HOME/.cache/cort-kotlin}"
FUENTES_KOTLIN="$(find src -name '*.kt' | sort)"
if [ -n "$FUENTES_KOTLIN" ]; then
    if ! ls "$KOTLIN_DIR"/kotlinc/bin/kotlinc >/dev/null 2>&1; then
        echo "kotlin: bajando kotlin-compiler-$KOTLIN_VERSION.zip (~87 MB, sólo en el runner)"
        curl --fail --silent --show-error --location --retry 3 --max-time 900 \
             -o /tmp/kotlin.zip \
             "https://github.com/JetBrains/kotlin/releases/download/v$KOTLIN_VERSION/kotlin-compiler-$KOTLIN_VERSION.zip"
        mkdir -p "$KOTLIN_DIR"
        unzip -q -o /tmp/kotlin.zip -d "$KOTLIN_DIR"
        rm -f /tmp/kotlin.zip
    fi
    KOTLINC="$KOTLIN_DIR/kotlinc/bin/kotlinc"
    CP_KOTLIN="$PLAT/android.jar"
    [ "$HAY_MOTOR" = "1" ] && CP_KOTLIN="$CP_KOTLIN:build/motor/jar/vosk.jar:build/motor/jar/jna.jar"
    mkdir -p build/obj-kotlin
    # `-Xjvm-default=all` y `-no-stdlib` no: la stdlib hace falta en el dex, y es
    # justamente el runtime que el original arrastraba. `kotlinc` la deja en
    # `kotlin-stdlib.jar` y abajo se dexa junto a las clases.
    { "$KOTLINC" -J-Xmx1024m -jvm-target 11 -language-version 1.9 \
        -classpath "$CP_KOTLIN" -d build/obj-kotlin $FUENTES_KOTLIN || true; } 2>&1 | tee /tmp/kotlin.log
    # `kotlinc` no sale con código distinto de cero si el pipe lo tapa, y además
    # escribe el error con dos formatos según la versión (`Archivo.kt:1:1: error:`
    # y el viejo `e: Archivo.kt: (1, 1): ...`). Se miran los dos en el log en vez
    # de fiarse del estado del pipe.
    if grep -qE ': ?error:|^e: ' /tmp/kotlin.log; then
        echo "kotlin: hay errores de compilación, se para el build"; grep -E ': ?error:|^e: ' /tmp/kotlin.log | head -20; exit 1
    fi
    [ -n "$(find build/obj-kotlin -name '*.class')" ] || { echo "kotlin: no salió ningún .class"; exit 1; }
    echo "kotlin: $(find build/obj-kotlin -name '*.class' | wc -l) clases de $(echo "$FUENTES_KOTLIN" | tr '\n' ' ')"
    HAY_KOTLIN=1
else
    HAY_KOTLIN=0
    echo "kotlin: no hay fuentes .kt en apps/apk/src"
fi

# -- El Java (la actividad, el puente y el cerebro, sin AndroidX) ------------
# `--release 11` con `android.jar` en el classpath y `-encoding UTF-8` porque el
# manifiesto y los mensajes están en español con tildes. `javac` es la única
# prueba que existe de las firmas de `VoiceInteractionSession.onShow` y compañía:
# un `@Override` con una firma que no está en la plataforma no compila. Lo mismo
# vale para `org.vosk.*`: si `Oido.kt` llamara un método que no está en el AAR,
# `kotlinc` lo pararía contra el `classes.jar` real de arriba.
CP_JAVA="$PLAT/android.jar"
[ "$HAY_KOTLIN" = "1" ] && CP_JAVA="$CP_JAVA:build/obj-kotlin:$KOTLIN_DIR/kotlinc/lib/kotlin-stdlib.jar"
[ "$HAY_MOTOR" = "1" ] && CP_JAVA="$CP_JAVA:build/motor/jar/vosk.jar:build/motor/jar/jna.jar"
javac --release 11 -encoding UTF-8 -classpath "$CP_JAVA" \
    -d build/obj $(find src -name '*.java')

# -- El dex: clases propias + motor + runtime Kotlin -------------------------
D8_ENTRADAS="$(find build/obj -name '*.class')"
[ "$HAY_KOTLIN" = "1" ] && D8_ENTRADAS="$D8_ENTRADAS $(find build/obj-kotlin -name '*.class')"
D8_JARS=""
[ "$META_MOTOR" = "1" ] && D8_JARS="build/motor/jar/vosk.jar build/motor/jar/jna.jar"
# `kotlin-stdlib-jdk7/jdk8` y `annotations` van también: el `classes.dex` del
# original los contenía y omitirlos es la clase de `NoClassDefFoundError` que
# sólo aparece al ejecutar, nunca al compilar.
[ "$HAY_KOTLIN" = "1" ] && D8_JARS="$D8_JARS $(ls "$KOTLIN_DIR"/kotlinc/lib/kotlin-stdlib.jar \
    "$KOTLIN_DIR"/kotlinc/lib/kotlin-stdlib-jdk7.jar "$KOTLIN_DIR"/kotlinc/lib/kotlin-stdlib-jdk8.jar \
    "$KOTLIN_DIR"/kotlinc/lib/annotations-13.0.jar 2>/dev/null | tr '\n' ' ')"
"$BT/d8" --release --min-api 26 --lib "$PLAT/android.jar" --output build/apk \
    $D8_ENTRADAS $D8_JARS

# `aapt2 link` ya armó el APK con los recursos; el dex se añade dentro, que es lo
# que Gradle hace por detrás y aquí se hace a la vista.
(cd build/apk && zip -q -j sin-alinear.apk classes*.dex)

# -- Las librerías nativas del oído ------------------------------------------
# Con `android:extractNativeLibs="true"` (así está en el manifiesto) Android
# saca los `.so` al instalar, así que pueden ir comprimidos y el APK pesa menos
# en la descarga. `zip -q -r` conserva la ruta `lib/<abi>/`, que es lo único que
# mira el cargador del sistema para `System.loadLibrary("vosk")` y para el
# `libjnidispatch.so` con el que JNA habla con él.
if [ "$META_MOTOR" = "1" ]; then
    (cd build/motor && zip -q -r ../apk/sin-alinear.apk lib)
    echo "motor: .so empaquetados -> $(unzip -l build/apk/sin-alinear.apk | grep -c 'lib/')"
fi

# -- Alinear y firmar -------------------------------------------------------
"$BT/zipalign" -f 4 build/apk/sin-alinear.apk build/apk/alineado.apk

# La llave: la misma de siempre, resuelta por `llave.sh` (secreto del repo ▸
# caché de Actions ▸ generar una nueva y guardarla allí). Antes cada run firmaba
# con una llave desechable, y eso obligaba a desinstalar para actualizar.
# shellcheck source=apps/apk/llave.sh
source llave.sh
preparar_llave || { echo "no se pudo preparar la llave de firma"; exit 1; }
echo "firmando con $LLAVE_ORIGEN — actualizar instalando encima: $LLAVE_ACTUALIZA"

# -- Los TRES esquemas de firma, pedidos a la fuerza -------------------------
# Por qué: `apksigner` no pregunta, decide. Con `minSdkVersion 26` la firma v1
# (la carpeta `META-INF/` de toda la vida) viene **desactivada por defecto**, y
# la v3 sólo se activa sola con `minSdk >= 28`. Eso deja un APK atado a que el
# `apksigner` del runner tenga los defaults de siempre. Medido sobre el
# `CORT-IA-2.3.0.apk` publicado —bajado y leído byte a byte en el portátil, no
# deducido—: sí salió con v1 (`META-INF/CORT.RSA`), v2 (`0x7109871a`) y v3
# (`0xf05368c0`). Aun así se piden explícitos, porque la v1 es la única que
# cualquier herramienta corriente puede leer (`keytool -printcert -jarfile`, el
# explorador con el que Play Protect mira el archivo, y `docs/INSTALAR-APK.md`
# se escribió con esa lectura). Ningún esquema extra cambia la llave, así que
# instalar encima del 2.3.0 sigue valiendo.
#
# La sonda existe porque estas banderas dependen de la versión de las
# build-tools: si el runner cambiara de imagen y no las conociera, un `sign` con
# argumento desconocido daría rojo y aquí no se fabrican banderas a ciegas.
ESQUEMAS=""
for bander in --v1-signing-enabled --v2-signing-enabled --v3-signing-enabled; do
    if "$BT/apksigner" sign --help 2>&1 | grep -q -- "$bander"; then
        ESQUEMAS="$ESQUEMAS $bander true"
    else
        echo "aviso: este apksigner no conoce $bander; se firma con sus defaults"
    fi
done
echo "esquemas pedidos:${ESQUEMAS:- (ninguno explícito)}"

# `set -u` no molesta aquí: `ESQUEMAS` se parte en palabras a propósito, y son
# banderas fijas escritas arriba, no rutas que alguien pueda llenar con espacios.
# shellcheck disable=SC2086
"$BT/apksigner" sign $ESQUEMAS --ks "$LLAVE" \
    --ks-pass pass:"$LLAVE_PASS" --key-pass pass:"$LLAVE_PASS" \
    --out build/CORT.apk build/apk/alineado.apk

# `verify --verbose` es el que dice QUÉ esquemas quedaron, no sólo si pasa. Su
# salida va a `build/verificacion.txt` y de ahí a `firma.txt`: sin sesión en
# GitHub los registros de Actions dan 403, así que lo que no viaje con el APK no
# existe. El `verify` sin `|| true`: si la firma no cuadra, el run tiene que
# ponerse rojo antes de publicar nada.
"$BT/apksigner" verify --verbose build/CORT.apk | tee build/verificacion.txt

# -- Auditoría de instalabilidad ---------------------------------------------
# La pregunta de la dueña ahora es «Play Protect no me deja instalarlo». Para
# poder responder con medidas en vez de con opiniones, cada Release se audita a
# sí misma sobre lo que Android y Play Protect miran de verdad, y el resultado se
# sube pegado al APK. Cada renglón se lee del archivo final:
#   * sha256   → distingue «el APK está mal» de «la descarga se cortó».
#   * recursos → desde Android 11, `resources.arsc` debe estar SIN comprimir y
#                alineado a 4; si fallara, el instalador lo tira.
#   * certificado → la firma de un auto-firmado caducado o «aún no válido» se
#                parece mucho a un bloqueo de Play Protect; la ventana se publica
#                para poder culpar al reloj del teléfono si es eso.
#   * depurable → un `android:debuggable` perdido sería un motivo real de bloqueo.
bash ../../scripts/audita-apk.sh build/CORT.apk "$BT" | tee build/auditoria.txt

# -- Cuánto pesa lo que acaba de salir ----------------------------------------
# La pregunta de la dueña fue «el APK no pesa lo que debería y lo comprimiste
# demasiado». El peso, por tanto, se mide AQUÍ y se escribe en `firma.txt` al lado
# del APK: es lo único que se puede comprobar después sin tener que fiarse de un
# número escrito a mano en el README. Dos cifras: la del archivo tal cual se
# descarga y la suma de sus entradas sin comprimir; de esas dos sale la proporción
# real de compresión, que es lo que desmonta (o confirma) la queja.
peso_apk() {
    stat -c '%s' "$1" 2>/dev/null || wc -c < "$1" | tr -d ' '
}
crudo_apk() {
    python3 - "$1" <<'PY' 2>/dev/null || unzip -l "$1" | awk 'END {print $1 + 0}'
import sys, zipfile
print(sum(i.file_size for i in zipfile.ZipFile(sys.argv[1]).infolist()))
PY
}
PESO_APK="$(peso_apk build/CORT.apk)"
CRUDO_APK="$(crudo_apk build/CORT.apk)"
ENTRADAS="$(python3 -c "import zipfile; print(len(zipfile.ZipFile('build/CORT.apk').infolist()))" 2>/dev/null || unzip -l build/CORT.apk | awk 'END{print $2}')"
PROP="$(python3 -c "p=$PESO_APK; c=$CRUDO_APK; print(f'{p / c:.2f}' if c else '?')" 2>/dev/null || echo '?')"
echo "peso medido: $PESO_APK bytes en la Release / $CRUDO_APK sin comprimir / $ENTRADAS entradas (proporción $PROP)"

# Y desglosado, porque «pesan 45 MB» sin decir de dónde salen los 45 MB es otra
# vez el número de alguien, no una medida. Cada bloque se mide EN el APK final.
# El desglose se guarda en `build/desglose.txt` y se mete en `firma.txt`: si no
# viaja con el APK, la dueña tiene que creerse 45 MB de memoria.
python3 - <<'PY' | tee build/desglose.txt
import zipfile
z = zipfile.ZipFile("build/CORT.apk")
CLASES = {".dex", ".so", ".arsc"}
def mide(pred):
    infos = [i for i in z.infolist() if pred(i)]
    return len(infos), sum(i.file_size for i in infos), sum(i.compress_size for i in infos)
def es_dex(n):     return n.endswith(".dex")
def es_so(n):      return n.startswith("lib/") and n.endswith(".so")
def es_modelo(n):  return n.startswith("assets/motor/")
def es_cara(n):    return n.startswith("assets/ui/")
def es_sonido(n):  return n.startswith("assets/sonido/")
def es_resto(i):   return not (es_dex(i.filename) or es_so(i.filename)
                               or es_modelo(i.filename) or es_cara(i.filename)
                               or es_sonido(i.filename))
print("desglose del peso (medido sobre el APK que acaba de salir):")
for nombre, pred in (("classes*.dex", lambda i: es_dex(i.filename)),
                     ("librerías .so", lambda i: es_so(i.filename)),
                     ("modelo del oído", lambda i: es_modelo(i.filename)),
                     ("avisos sonoros", lambda i: es_sonido(i.filename)),
                     ("cara (assets/ui)", lambda i: es_cara(i.filename)),
                     ("recursos y resto", es_resto)):
    n, crudo, apretado = mide(pred)
    print(f"   {nombre:19} {n:>4} entradas · {crudo:>12,} B en crudo · {apretado:>11,} B dentro del APK")
PY

# -- Con qué llave salió (se sube a la Release como prueba pública) --
{
    echo "APK de CORT $VERSION (versionCode $CODE), paquete com.cort.ia"
    echo "cara embebida: ui/ de este commit ($(git rev-parse --short HEAD 2>/dev/null || echo '?'))"
    echo "peso: $PESO_APK bytes comprimido / $CRUDO_APK bytes sin comprimir / $ENTRADAS entradas / proporción $PROP"
    # La auditoría del archivo final y lo que `apksigner verify --verbose` vio en
    # él. Van aquí, pegadas al peso, porque son la respuesta a «Play Protect no me
    # deja instalarlo»: si el sha256 y el peso coinciden con los de abajo, el
    # archivo de la Release es íntegro y firmado por las tres vías, y el problema
    # está en el teléfono (guía de toques: `docs/BLOQUEO-PLAY-PROTECT.md`).
    cat build/auditoria.txt
    echo "  verificación:"
    sed 's/^/   · /' build/verificacion.txt
    echo "llave: $LLAVE_ORIGEN"
    echo "actualizar instalando encima: $LLAVE_ACTUALIZA"
    # El perfil y la superficie del BINARIO ya los imprime la auditoría de arriba
    # (`manifiesto binario: N permisos · servicios privilegiados (BIND_*): M ·
    # perfil declarado: …`), leídos del APK firmado. Lo que se añade aquí es lo que
    # pidió `perfil.py`, para que las dos cosas se puedan confrontar.
    echo "perfil: $PERFIL (APK_PERFIL) — el recorte lo hace apps/apk/perfil.py sobre AndroidManifest.xml"
    if [ "$META_MOTOR" = "1" ]; then
        echo "variedad: COMPLETA — el oído offline va dentro (Vosk 0.3.47 + JNA 5.13.0 + modelo $(cat build/motor/modelo-nombre.txt))"
        echo "  sha256 del modelo: $(cat build/motor/modelo-sha256.txt)"
        echo "  .so: $(find build/motor/lib -name '*.so' | sort | tr '\n' ' ')"
        # Ojo con las comillas: dentro de `echo "…"` un acento grave es sustitución de
        # orden, así que las rutas van sin ellos.
        echo "  en el primer arranque el oído desempaca el modelo en filesDir/motor:"
        echo "  son 60.286.598 bytes sueltos (los mide Oido.kt en CRUDO_MODELO); sin sitio dice sin-sitio y no toca nada"
    else
        echo "variedad: LIGERA (APK_SIN_OIDO=1) — NO lleva el oído offline dentro"
        echo "  fuera: las cuatro .so de Vosk/JNA y el modelo de español (39.817.833 B comprimidos)"
        echo "  el oído propio dice sin-modelo en Equipo ▸ 7 · Oído y CORT escucha con el"
        echo "  reconocedor del sistema — salvo que el perfil sea nucleo, que tampoco lo"
        echo "  declara: entonces escucha con ACTION_ASSIST del sistema, si el fabricante lo usa."
        echo "  Para qué sirvió: aislar si el aviso lo dispara el bulto nativo del oído. MEDIDO"
        echo "  el 2026-10-22 con la dueña: NO. Los dos APK de la 2.4.2 se bloquearon igual."
        echo "  Lo que sí separa al 1.1.4 (se instala, 13 permisos, cero servicios BIND_*) del"
        echo "  2.4.2 (bloqueado, 28 permisos, cinco servicios privilegiados) es la superficie"
        echo "  del manifiesto, y por eso existe el perfil nucleo."
    fi
    sed 's/^/   · /' build/desglose.txt
    if [ "$HAY_KOTLIN" = "1" ]; then
        echo "lenguaje: Java + Kotlin $KOTLIN_VERSION (el método del 1.1.0: d8 y dex mixto, sin Gradle)"
    else
        echo "lenguaje: sólo Java (no se pudo montar Kotlin en este run)"
    fi
    "$BT/apksigner" verify --print-certs build/CORT.apk
} > build/firma.txt
cat build/firma.txt
anotar_llave build/CORT.apk "$BT/apksigner"

ls -l build/CORT.apk
echo "APK listo: build/CORT.apk"
