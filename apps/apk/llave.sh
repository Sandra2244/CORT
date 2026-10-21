#!/usr/bin/env bash
# La llave con la que se firma el APK del teléfono — una sola, en todas las Releases.
#
# Por qué existe este archivo: cada run de `compilar.sh` generaba su propia llave
# desechable, y para Android una firma distinta es otra
# aplicación. Eso significaba que **cada actualización obligaba a desinstalar**,
# y al desinstalar se va el permiso del micrófono, el de los avisos y la dirección
# del PC que la dueña escribió a mano. Este helper hace que la llave sea siempre
# la misma, en este orden:
#
#   1. `CORT_APK_KEYSTORE_B64` (+ `CORT_APK_KEYSTORE_PASS`) — el secreto del repo.
#      Manda sobre todo lo demás: es la forma permanente, y la única que sobrevive
#      aunque se borre la caché de Actions.
#   2. `$CORT_KEYSTORE_DIR/cort.keystore` (+ `pass.txt`) — la llave que el propio
#      pipeline guardó la primera vez en la caché (`actions/cache`, paso
#      `cort-apk-keystore-v1` de `build.yml`). Con esto ya no hay que tocar nada.
#   3. Ninguna de las dos: se genera una llave nueva **dentro de esa carpeta**, de
#      modo que el siguiente run la encuentra en la caché.
#
# El detalle medido (que antes se decía mal): la caché de `actions/cache` vive
# **en el `ref` que la creó**, y cada etiqueta es otro `ref`. O sea, con el camino
# 2 la llave se repite entre runs de una misma etiqueta, pero la Release siguiente
# no la ve y vuelve a tocar desinstalar. La única llave de verdad permanente es el
# secreto del repo (camino 1); se monta una vez en el portátil con
# `bash scripts/llave-nueva.sh` y se pegan sus dos secretos.
#
# Deja definidas cuatro variables para que el que llame escriba la verdad en
# `firma.txt`: `LLAVE`, `LLAVE_PASS`, `LLAVE_ORIGEN`, `LLAVE_ACTUALIZA`.
#
# Uso (desde la raíz del repo o desde `apps/apk/`):
#   source apps/apk/llave.sh && preparar_llave
#
# La carpeta vive en `apps/apk/keystore/`, que está en `.gitignore`: la llave
# NUNCA se sube al repo, porque el repo es público y con esa llave cualquiera
# podría firmar actualizaciones de su CORT.

# La carpeta es la de este script (`apps/apk/keystore`), absoluta y sin depender
# del `cd` en el que esté el que llama: `compilar.sh` trabaja dentro de
# `apps/apk/`, pero el workflow invoca desde la raíz del repo.
_AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORT_KEYSTORE_DIR="${CORT_KEYSTORE_DIR:-$_AQUI/keystore}"

preparar_llave() {
    if [ -n "${CORT_APK_KEYSTORE_B64:-}" ]; then
        LLAVE="${TMPDIR:-/tmp}/cort-firma.keystore"
        printf '%s' "$CORT_APK_KEYSTORE_B64" | base64 -d > "$LLAVE"
        if [ -z "${CORT_APK_KEYSTORE_PASS:-}" ]; then
            echo "falta CORT_APK_KEYSTORE_PASS: hay keystore pero no su contraseña"; return 1
        fi
        LLAVE_PASS="$CORT_APK_KEYSTORE_PASS"
        LLAVE_ORIGEN="la llave del secreto CORT_APK_KEYSTORE_B64 del repo"
        LLAVE_ACTUALIZA="sí: se puede instalar encima del anterior"
        return 0
    fi

    if [ -f "$CORT_KEYSTORE_DIR/cort.keystore" ]; then
        LLAVE="$CORT_KEYSTORE_DIR/cort.keystore"
        if [ -n "${CORT_APK_KEYSTORE_PASS:-}" ]; then
            LLAVE_PASS="$CORT_APK_KEYSTORE_PASS"
        elif [ -f "$CORT_KEYSTORE_DIR/pass.txt" ]; then
            LLAVE_PASS="$(cat "$CORT_KEYSTORE_DIR/pass.txt")"
        else
            echo "la caché trajo el keystore pero no su contraseña: se regenera"
            rm -f "$CORT_KEYSTORE_DIR/cort.keystore"
            preparar_llave
            return $?
        fi
        LLAVE_ORIGEN="la llave fija de la caché de Actions ($CORT_KEYSTORE_DIR)"
        LLAVE_ACTUALIZA="sí: se puede instalar encima del anterior"
        return 0
    fi

    # Ni secreto ni caché: se crea la llave definitiva y se deja en la carpeta que
    # el workflow cachea, para que la proxima vez esto no vuelva a pasar.
    mkdir -p "$CORT_KEYSTORE_DIR" || { echo "no se puede crear $CORT_KEYSTORE_DIR"; return 1; }
    chmod 700 "$CORT_KEYSTORE_DIR" 2>/dev/null || true
    LLAVE="$CORT_KEYSTORE_DIR/cort.keystore"
    # 16 hex = 8 bytes de entropía; `keytool` exige 6+ caracteres y el JDK del
    # runner no trae algoritmo por defecto (medido en runs viejos).
    LLAVE_PASS="$( (openssl rand -hex 8 2>/dev/null || echo "cort$(date +%s)") | cut -c1-16)"
    printf '%s' "$LLAVE_PASS" > "$CORT_KEYSTORE_DIR/pass.txt"
    chmod 600 "$CORT_KEYSTORE_DIR/pass.txt" 2>/dev/null || true
    keytool -genkeypair -keystore "$LLAVE" -alias CORT \
        -keyalg RSA -keysize 2048 -validity 10950 \
        -storepass "$LLAVE_PASS" -keypass "$LLAVE_PASS" \
        -dname "CN=CORT, OU=asistente local, O=local" >/dev/null
    LLAVE_ORIGEN="una llave nueva, generada en este run y guardada en $CORT_KEYSTORE_DIR (caché del repo)"
    LLAVE_ACTUALIZA="sí a partir de la Próxima actualización: la de ahora pide desinstalar una vez"
}

# El run deja la huella de la llave como anotación del check-run: es lo único que
# se ve sin sesión (los logs de Actions dan 403), y comparando dos Releases se
# sabe si la caché aguantó.
#   anotar_llave <apk> [ruta-de-apksigner]
anotar_llave() {
    local apk="$1" signer="${2:-apksigner}" dig
    [ -x "$signer" ] || signer=apksigner
    dig="$("$signer" verify --print-certs "$apk" 2>/dev/null \
            | grep -m1 'SHA-256 digest' | awk '{print $NF}')"
    [ -n "$dig" ] || dig="(no se pudo leer la huella)"
    echo "::notice::llave del APK $dig · $LLAVE_ORIGEN · actualizar encima: $LLAVE_ACTUALIZA"
}
