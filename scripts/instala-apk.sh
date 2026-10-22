#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# instala-apk.sh — baja el APK más reciente y, si hay teléfono delante, lo
# instala ENCIMA del anterior; si algo falla, dice en español qué falla y qué
# hacer. Nace de una frase de la dueña: «sale error al instalar».
#
# Por qué un script y no «púlsalo en el teléfono»: el error de Android suele ser
# un párrafo técnico sin traducción, y la causa real casi siempre se puede saber
# de antemano con la firma del APK. Medido con `keytool -printcert -jarfile`
# sobre los APKs ya publicados (2026-10-21):
#
#   CORT-IA-2.1.0.apk  fa:ab:ef:46…  ← la llave estable del secreto del repo
#   CORT-IA-2.0.0.apk  fa:ab:ef:46…  ← la MISMA: 2.0 → 2.1 se instala encima
#   CORT-IA-1.1.4.apk  eb:d6:25:04…  ← DISTINTA (llave de un solo uso)
#   CORT-v0.17.0.apk   52:70:15:47…  ← DISTINTA (la del APK original)
#   CORT-IA-1.1.0.apk  sin firma v1 legible (sólo v2/v3)
#
# Conclusión, y es la que explica el «sale error»: un teléfono que aún tenga un
# 1.x, o el APK original, NO puede recibir un 2.x instalando encima. Android
# llama a eso `INSTALL_FAILED_UPDATE_INCOMPATIBLE` y sólo se quita desinstalando
# esa vez. Desde el 2.0.0 la llave ya no cambia, así que es un costo único.
#
# Uso:
#   bash scripts/instala-apk.sh                 # baixa el último y te dice cómo
#   bash scripts/instala-apk.sh ~/Descargas/CORT-IA-2.1.0.apk   # instala ése
#   bash scripts/instala-apk.sh --tel           # fuerza `adb install -r`
#
# Con `adb` (si algún día lo instalas) el teléfono tiene que estar conectado con
# «Depuración USB» activa; sin `adb`, este script deja el .apk en el portátil y
# escribe los tres pasos del teléfono. No inventa resultados: si no puede mirar,
# lo dice.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO="${CORT_REPO:-Sandra2244/CORT}"
API="https://api.github.com/repos/${REPO}/releases/latest"
CARPETA="${HOME}/Descargas"
[ -d "$CARPETA" ] || CARPETA="${HOME}"
QUIETO=${QUIETO:-0}

dice() { [ "$QUIETO" = 1 ] || echo "$@"; }
rojo() { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }

# ── el motivo traducido: una línea por cada código que Android puede dar ──────
traduce() {
  local salida=$1
  # Un patrón de `case` con espacios va ENTRE COMILLAS: sin ellas bash lo parte y
  # el script muere en tiempo de análisis, que es el peor sitio para enterarse.
  case "$salida" in
    *Success*|*success*)
      verde "Instalado. Es el mismo CORT de antes, actualizado por encima." ;;
    *INSTALL_FAILED_UPDATE_INCOMPATIBLE*)
      rojo "El CORT instalado en el teléfono se firmó con OTRA llave."
      dice "  Es el caso de siempre al saltar de un 1.x (o del APK original) a un 2.x."
      dice "  Se quita una sola vez: Ajustes ▸ Aplicaciones ▸ CORT ▸ Desinstalar,"
      dice "  y vuelve a instalar este .apk. De 2.0.0 en adelante la llave ya no cambia,"
      dice "  así que las actualizaciones siguientes sí entran encima."
      dice "  OJO: desinstalar borra lo que CORT recuerda de ese teléfono (perfil, claves"
      dice "  y notas). Apunta antes tu clave de Groq si la pusiste ahí." ;;
    *INSTALL_FAILED_OLDER_SDK*)
      rojo "Este APK pide un Android más nuevo que el del teléfono."
      dice "  El suelo del APK es Android 8 (API 26). Mira Ajustes ▸ Acerca del teléfono." ;;
    *INSTALL_FAILED_VERSION_DOWNGRADE*)
      rojo "El teléfono ya tiene un CORT MÁS nuevo."
      dice "  No hace falta instalar: desinstala el nuevo si quieres volver, o usa el que hay." ;;
    *INSTALL_FAILED_INSUFFICIENT_STORAGE*)
      rojo "No cabe: falta sitio libre en el teléfono." ;;
    *INSTALL_PARSE_FAILED_NOT_APK*|*INSTALL_FAILED_INVALID_APK*|*zip*|"*central directory"*)
      rojo "El archivo está incompleto o roto (la descarga se cortó)."
      dice "  Vuelve a bajarlo con el mismo script; si pesa menos de lo que anuncia la"
      dice "  Release, no es el archivo entero." ;;
    *INSTALL_PARSE_FAILED_NO_CERTIFICATES*|"*signing failed*"|"*does not match"*|*signature*)
      rojo "APK sin firmar o con firma inválida: este no es un archivo publicado."
      dice "  Carga siempre el .apk de la Release de ${REPO}." ;;
    *PERMISSION_DENIED*|"*not granted*"|"*unknown sources*"|*INSTALL_FAILED_ABORTED*)
      rojo "El teléfono no dejó instalar apps de fuera del Play Store."
      dice "  Permite «instalar apps desconocidas» para el explorador de archivos (o para"
      dice "  CORT) en Ajustes ▸ Aplicaciones ▸ Instalar apps desconocidas, y reintenta." ;;
    "device offline"*|"*no permissions"*|*unauthorized*)
      rojo "El teléfono no habla por USB."
      dice "  Acepta el cuadro «Permitir depuración USB» en la pantalla del teléfono." ;;
    *"not yet valid"*|*"certificate not valid"*|*"Certificado"*|*"certificate has expired"*)
      rojo "Android rechaza el certificado de firma — y casi siempre es la HORA del teléfono."
      dice "  El certificado de CORT empieza a ser válido el 2026-10-21 11:19 GMT (medido en"
      dice "  su propio META-INF/CORT.RSA). Si el móvil marca una fecha anterior, el instalador"
      dice "  lo ve «aún no válido» y el fallo parece de seguridad pero es del reloj:"
      dice "  Ajustes ▸ Sistema ▸ Fecha y hora ▸ automática, y reintenta." ;;
    *"Play Protect"*|*"not optimized"*|*"may harm"*|*"unrecognized"*)
      rojo "Es el aviso de Google a cualquier app auto-firmada que no está en Play."
      dice "  No es un defecto del APK: con la hoja -firma.txt al lado se ve que va firmado"
      dice "  v1+v2+v3, con resources.arsc alineado y el certificado vigente hasta 2056."
      dice "  La tabla de qué pulsar según la frase exacta está en docs/BLOQUEO-PLAY-PROTECT.md."
      dice "  Por adb, que es justamente lo que estamos haciendo, ese aviso no aparece." ;;
    *)
      rojo "Android contestó algo que no conozco:"
      dice "$salida" ;;
  esac
}

# ── ¿hay `adb` y hay teléfono? ────────────────────────────────────────────────
con_adb() { command -v adb >/dev/null 2>&1; }
hay_telefono() { [ -n "$(adb devices 2>/dev/null | awk 'NR>1 && $2=="device"')" ]; }

instalar_por_adb() {
  local apk=$1
  dice "== instalando $(basename "$apk") por adb (encima del anterior, sin borrar datos)"
  local salida; salida=$(adb install -r "$apk" 2>&1) || true
  traduce "$salida"
  case "$salida" in *Success*|*success*) return 0 ;; *) return 1 ;; esac
}

# ── el camino normal: la Release más reciente ─────────────────────────────────
destino=${1:-}
case "$destino" in
  --tel)
    con_adb || { rojo "No hay adb en este portátil. Instala Android platform-tools si"
                 rojo "quieres instalar por USB; sin él, usa el teléfono."; exit 2; }
    ;;
esac

if [ -n "${destino:-}" ] && [ -f "$destino" ]; then
  APK=$destino
  dice "== usando el APK que me diste: $APK"
else
  dice "== buscando el último APK publicado en ${REPO}"
  json=$(curl -sL -m 30 "$API") || { rojo "No pude leer la Release (sin red)."; exit 1; }
  etiqueta=$(echo "$json" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("tag_name",""))')
  url=$(echo "$json" | python3 -c '
import json,sys
d=json.load(sys.stdin)
for a in d.get("assets",[]):
    if a["name"].endswith(".apk") and "asistente" not in a["name"]:
        print(a["browser_download_url"]); break
')
  peso=$(echo "$json" | python3 -c '
import json,sys
d=json.load(sys.stdin)
for a in d.get("assets",[]):
    if a["name"].endswith(".apk") and "asistente" not in a["name"]:
        print(a["size"]); break
')
  [ -n "$url" ] || { rojo "La Release ${etiqueta} no trae APK."; exit 1; }
  APK="$CARPETA/$(basename "$url")"
  dice "   Release: $etiqueta · anunciada $((peso)) bytes"
  dice "   bajando a $APK"
  curl -L -m 300 "$url" -o "$APK"
  real=$(stat -c%s "$APK")
  if [ "$real" != "$peso" ]; then
    rojo "Descarga incompleta: $real bytes de $peso. Reintenta."
    exit 1
  fi
  verde "Descargado entero: $real bytes."
  # La hoja de firma que publica el propio CI: peso real, llave y si se puede
  # instalar encima. Se descarga con el mismo nombre y `-firma.txt`.
  firma_url=$(echo "$json" | python3 -c '
import json,sys
d=json.load(sys.stdin)
for a in d.get("assets",[]):
    if a["name"].endswith("-firma.txt"):
        print(a["browser_download_url"]); break
')
  if [ -n "$firma_url" ]; then
    curl -sL -m 30 "$firma_url" -o "${APK%.apk}-firma.txt" &&
      dice "== hoja de firma publicada: ${APK%.apk}-firma.txt"
    # Y además del peso, el sha256. Desde el `2.3.1` la hoja lleva la auditoría
    # leída sobre el APK final, renglón `sha256: <64 hex>`: comparar ese valor con
    # el archivo que acabas de bajar distingue «el APK está mal hecho» de «la
    # descarga se corrompió por el camino», que es justo la duda que aparece cuando
    # Play Protect se queja. El peso ya se comprobó arriba, byte a byte.
    esperado=$( { grep -m1 -oE 'sha256: [0-9a-f]{64}' "${APK%.apk}-firma.txt" || true; } \
                | awk '{print $2}')
    if [ -n "$esperado" ]; then
      real_sha=$(sha256sum "$APK" | awk '{print $1}')
      if [ "$real_sha" = "$esperado" ]; then
        verde "sha256 coincide con la hoja: $real_sha"
        dice "   (o sea: el archivo es idéntico al que salió del compilador;"
        dice "    si el teléfono lo bloquea, no es defecto del APK → docs/BLOQUEO-PLAY-PROTECT.md)"
      else
        rojo "sha256 DISTINTO: el tuyo es $real_sha y la hoja anuncia $esperado."
        rojo "Ese archivo no es el publicado: no lo instales, vuelve a bajarlo."
        exit 1
      fi
    else
      dice "   (la hoja de esta Release no trae sha256: es anterior al 2.3.1)"
    fi
  fi
fi

if con_adb && hay_telefono; then
  instalar_por_adb "$APK"
else
  dice ""
  dice "== no hay teléfono por USB$(con_adb || echo ' (tampoco hay adb en el portátil)')"
  dice "   Lleva el archivo al teléfono (cable, WhatsApp a ti misma, o el enlace de la"
  dice "   Release: https://github.com/${REPO}/releases/latest) y ábrelo con el"
  dice "   explorador de archivos. Android lo instala sin configurar nada más."
  dice ""
  dice "   Si sale un error al instalar, mira la tabla de docs/INSTALAR-APK.md;"
  dice "   en nueve de diez casos es que el CORT viejo se firmó con otra llave y hay"
  dice "   que desinstalar ese CORT UNA vez."
  dice ""
  dice "   Y si el que salta es un AVISO de Google («Play Protect no reconoce esta"
  dice "   app», «puede dañar tu dispositivo», Chrome no deja descargar el .apk), eso"
  dice "   NO es un fallo del APK: es el aviso que Google da a cualquier app"
  dice "   auto-firmada fuera de Play. docs/BLOQUEO-PLAY-PROTECT.md tiene la tabla"
  dice "   de qué pulsar según la frase exacta, por marca de teléfono."
fi
