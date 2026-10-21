#!/usr/bin/env bash
# scripts/llave-nueva.sh — fabrica EN TU PC la llave con la que se firma el APK,
# y te deja listos los dos valores que hay que pegar como secreto en GitHub.
#
# Para qué sirve, en una frase: mientras el pipeline no tenga una llave fija,
# cada Release firma con una llave distinta, y para Android una firma distinta es
# otra aplicación — o sea, actualizar el CORT del teléfono obliga a **desinstalar**
# y se van el permiso del micrófono, el de los avisos y la dirección del PC que
# escribiste a mano. Con este secreto la llave es siempre la misma y las
# actualizaciones se instalan **encima**.
#
# Por qué se hace en tu PC y no en el pipeline: el repo es público, así que la
# llave no puede vivir ni un commit ni un artefacto de la Release. Aquí se genera
# y se queda en tu carpeta personal; al repo sólo viaja el secreto, que es
# privado y sólo lo ven las ejecuciones de Actions.
#
# Uso:
#   bash scripts/llave-nueva.sh              # deja los archivos en ~/
#   bash scripts/llave-nueva.sh /ruta/carpeta
#
# Lo que produce (NUNCA se sube al repo):
#   cort-llave.jks       la llave (por si la quieres guardar en un USB)
#   cort-llave.b64       la misma llave en base64 -> secreto CORT_APK_KEYSTORE_B64
#   cort-llave.pass      su contraseña             -> secreto CORT_APK_KEYSTORE_PASS
#
# Después, en el navegador:
#   github.com/Sandra2244/CORT → Settings → Secrets and variables → Actions
#   → New repository secret, y creas los dos con el CONTENIDO de esos archivos.
#   `apps/apk/llave.sh` ya los mira primero: si existen, manda el secreto sobre
#   la caché de Actions y ésa es la última vez que hace falta desinstalar.
set -euo pipefail

CARPETA="${1:-$HOME}"
mkdir -p "$CARPETA"
case "$CARPETA" in
  */CORT|*/CORT/*) echo "⚠  esa carpeta está dentro del repo; pon otra (por defecto ~/)"; exit 1 ;;
esac

LLAVE="$CARPETA/cort-llave.jks"
B64="$CARPETA/cort-llave.b64"
PASS="$CARPETA/cort-llave.pass"

if [ -e "$LLAVE" ]; then
  echo "ya existe $LLAVE: no la toco (cambiarla = volver a desinstalar el teléfono)."
  echo "si de verdad quieres otra, borra ese archivo y repite."
  exit 1
fi

# La misma receta que `apps/apk/llave.sh` usa en el runner: RSA 2048, treinta
# años de validez y una sola entrada (`-alias CORT`), para que `apksigner` la
# encuentre sin preguntar. Contraseña de almacén y de clave iguales:
# `compilar.sh` firma con `--ks-pass pass:…` y `--key-pass pass:…` con la misma.
nueva="$( (openssl rand -hex 8 2>/dev/null || printf '%s' "$(date +%s%N)") | cut -c1-16 )"
keytool -genkeypair -keystore "$LLAVE" -alias CORT \
    -keyalg RSA -keysize 2048 -validity 10950 \
    -storepass "$nueva" -keypass "$nueva" \
    -dname "CN=CORT, OU=asistente local, O=local" >/dev/null

printf '%s' "$nueva" > "$PASS"
chmod 600 "$LLAVE" "$PASS"
base64 -w0 "$LLAVE" > "$B64" 2>/dev/null || base64 < "$LLAVE" | tr -d '\n' > "$B64"
chmod 600 "$B64"

# Y se comprueba aquí mismo: si `keytool` no puede relistarlo, el secreto no
# va a servir de nada.
keytool -list -keystore "$LLAVE" -storepass "$nueva" >/dev/null
huella="$(keytool -list -keystore "$LLAVE" -storepass "$nueva" -alias CORT -v 2>/dev/null \
          | grep -m1 -i 'SHA256' | awk '{print $NF}' | tr -d ':' | tr 'A-Z' 'a-z')"

echo
echo "llave hecha en $LLAVE  (${#nueva} caracteres de contraseña)"
echo "  huella del certificado: ${huella:-"(keytool no la imprimió; saldrá en el -firma.txt de la Release)"}"
echo "                        — es la que tiene que aparecer en CORT-IA-*-firma.txt"
echo "                          la primera Release que use estos secretos."
echo
echo "Pégalos como secretos del repo (Settings ▸ Secrets and variables ▸ Actions):"
echo "  CORT_APK_KEYSTORE_B64   ← el contenido de  $B64"
echo "  CORT_APK_KEYSTORE_PASS  ← el contenido de  $PASS"
echo
echo "En una terminal, para seleccionarlos y copiarlos:"
echo "  xclip -selection clipboard < $B64      # y pegas en el valor del secreto"
echo "  cat $PASS                               # lo copias a mano"
echo
echo "Mientras no existan, el pipeline sigue firmando con la llave de su caché,"
echo "que cambia entre Releases: cada cambio de llave = una desinstalación."
