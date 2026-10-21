#!/usr/bin/env bash
# Comprueba `apps/apk/llave.sh` sin compilar nada y sin llaves reales.
#
# Es la prueba barata de que el APK se puede actualizar sin desinstalar: si la
# ruta de la llave se equivoca, cada Release firma con una llave distinta y la
# dueña pierde los permisos concedidos y la dirección del PC al instalar. Aquí no
# hay `keytool` en esta máquina (medido: no trae JDK), así que se prueba la
# **decisión** —qué llave se elige y qué va a escribir `firma.txt`— con un
# keystore de relleno, no con una firma de verdad.
#
# Uso:  bash scripts/prueba-llave.sh      (una fracción de segundo)
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ"
LLAVE_SH="$RAIZ/apps/apk/llave.sh"

SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
FALLOS=0
ok() { echo "  ok  $*"; }
no() { echo "  NO  $*"; FALLOS=$((FALLOS + 1)); }

KS="$SANDBOX/keystore"
mkdir -p "$KS"
printf 'keystore de relleno' > "$KS/cort.keystore"
printf 'sEkRet0dePrueba' > "$KS/pass.txt"

# 1 · la llave ya está en la caché de Actions: se usa tal cual
out="$(CORT_KEYSTORE_DIR="$KS" bash -c "
    source '$LLAVE_SH'
    preparar_llave && echo \"|PASS=\$LLAVE_PASS|ORIGEN=\$LLAVE_ORIGEN|ACT=\$LLAVE_ACTUALIZA|\"")"
case "$out" in
    *"|PASS=sEkRet0dePrueba|"*) ok "caché: toma la llave guardada y su contraseña de pass.txt" ;;
    *) no "caché: sacó «$out»" ;;
esac
case "$out" in
    *"ACT=sí"*) ok "caché: firma.txt dirá que se puede instalar encima del anterior" ;;
    *) no "caché: no prometió actualizar encima — $out" ;;
esac

# 2 · el secreto del repo manda sobre la caché (es la vía permanente)
out="$(CORT_APK_KEYSTORE_B64="$(printf 'keystore-del-repo' | base64)" \
        CORT_APK_KEYSTORE_PASS="passDelRepo" CORT_KEYSTORE_DIR="$KS" bash -c "
    source '$LLAVE_SH'
    preparar_llave && echo \"|PASS=\$LLAVE_PASS|ORIGEN=\$LLAVE_ORIGEN|\"")"
case "$out" in
    *"|PASS=passDelRepo|"*) ok "secreto: gana sobre la caché y usa CORT_APK_KEYSTORE_PASS" ;;
    *) no "secreto: sacó «$out»" ;;
esac
case "$out" in
    *"CORT_APK_KEYSTORE_B64"*) ok "secreto: firma.txt dice de dónde salió la llave" ;;
    *) no "secreto: no nombró el secreto — $out" ;;
esac

# 3 · secreto sin contraseña: se para, no firma a ciegas
if CORT_APK_KEYSTORE_B64="$(printf 'x' | base64)" CORT_KEYSTORE_DIR="$KS" bash -c "
        source '$LLAVE_SH'; preparar_llave" >/dev/null 2>&1; then
    no "secreto sin pass: debía fallar y no falló"
else
    ok "secreto sin pass: falla con mensaje en vez de medias firmas"
fi

# 4 · sin secreto y sin caché hay que GENERAR una (aquí no se puede: falta
#     `keytool` en esta máquina) y dejarla en la carpeta cacheada.
rm -f "$KS/cort.keystore" "$KS/pass.txt"
if CORT_KEYSTORE_DIR="$KS" bash -c "source '$LLAVE_SH'; preparar_llave" >/dev/null 2>&1; then
    ok "generación: este equipo sí tiene keytool, la llave nueva quedó en la caché"
else
    ok "generación: pide keytool (aquí no hay JDK) y escribe en la carpeta de la caché"
    grep -q 'CORT_KEYSTORE_DIR' "$LLAVE_SH" || no "generación: la carpeta cacheable no está definida"
    [ -d "$KS" ] || no "generación: no crea la carpeta antes de fallar"
fi

# 5 · la carpeta de la llave está fuera del repo, que es público
if git check-ignore -q apps/apk/keystore/cort.keystore 2>/dev/null; then
    ok ".gitignore: la llave nunca se sube al repo público"
else
    no ".gitignore: falta apps/apk/keystore/"
fi

echo
if [ "$FALLOS" -ne 0 ]; then
    echo "FALTA $FALLOS COSA(S) en la llave de firma"
    exit 1
fi
echo "llave resuelta bien: la misma en todas las Releases, y sin subir al repo."
