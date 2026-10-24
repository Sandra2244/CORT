#!/usr/bin/env bash
# Taller de mutaciones de F16: «despiértame a las 7 con After Dark para el examen».
#
# Por qué existe: **un verde que no puede caer no es prueba.** El sector [31] de
# `scripts/prueba-costura.py` da verde sobre el despertador, y `Prueba7` sobre
# `Despertar`. Aquí se rompe a propósito —una mutación por cada costura que se
# vigila— para exigir que el verde se ponga rojo Y que el rojo NOMBRE la
# comprobación que faltaba. Si el código roto sigue verde, la comprobación es
# decoración y la alarma volvería a sonar a la hora equivocada.
#
# Qué se rompe, en una línea: que `Despertar` siga siendo Java puro, que la hora
# tenga UN dueño, que la exactitud se pregunte y se diga, que el canal y el
# receptor sean los de alarma, que el evento llegue a la cara con guardia, que
# `Cerebro.hora` conserve la cola y que `Prueba7` siga en el bucle. Las dos
# últimas corren la suite entera: sólo ella ve que marzo devuelve el pasado o que
# «con la canción» sin nombre se convierte en una canción.
#
# Dónde se corre: en el taller, NUNCA como paso del pipeline. Trabaja sobre una
# copia de links duros en `/tmp`; rompe el link antes de tocar, así que el repo
# no se entera.
#
# Uso:  bash scripts/taller-f16.sh            (≈3 minutos)
#       bash scripts/taller-f16.sh exactitud     (sólo las que digan eso)
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TALLER="$(mktemp -d /tmp/cort-taller-f16-XXXXXX)"
trap 'rm -rf "$TALLER"' EXIT

for d in apps ui backend desktop scripts .github; do
  cp -al "$REPO/$d" "$TALLER/$d" 2>/dev/null || cp -a "$REPO/$d" "$TALLER/$d"
done

DESP="apps/apk/src/com/cort/ia/Despertar.java"
ALARMA="apps/apk/src/com/cort/ia/Alarma.java"
PUENTE="apps/apk/src/com/cort/ia/CortNative.java"
CEREBRO="apps/apk/src/com/cort/ia/Cerebro.java"
MANIFIESTO="apps/apk/AndroidManifest.xml"
TEL="ui/js/telefono.js"
P3="apps/apk/prueba/Prueba3.java"
SH="scripts/prueba-mente.sh"

CAEN=0
AGUANTAN=0
SOLO="${1:-}"
[ -n "$SOLO" ] && echo "  (filtro: sólo las mutaciones que contienen «$SOLO»)"

# reemplaza <archivo> <de> <a>: cambio exacto y comprobado (si no cambia, es que
# la mutación está mal escrita y el taller lo dice en vez de fingir que probó).
reemplaza() {
  python3 - "$TALLER/$1" "$2" "$3" <<'PY'
import pathlib, sys
p, viejo, nuevo = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
t = p.read_text(encoding="utf-8")
if viejo not in t:
    sys.exit(3)
p.write_text(t.replace(viejo, nuevo, 1), encoding="utf-8")
PY
}

muta() {  # muta <nombre> <archivo> <de> <a> [esperado]
  local nombre="$1" rel="$2" viejo="$3" nuevo="$4" espera="${5:-}"
  if [ -n "$SOLO" ] && ! printf '%s' "$nombre" | grep -qi -- "$SOLO"; then
    return 0
  fi
  rm -f "$TALLER/$rel"
  cp "$REPO/$rel" "$TALLER/$rel"
  if ! reemplaza "$rel" "$viejo" "$nuevo"; then
    echo "  ???     $nombre: el reemplazo no encontró el texto (mutación mal escrita)"
    AGUANTAN=$((AGUANTAN + 1))
    return
  fi
  local log="$TALLER/salida.log"
  if python3 "$TALLER/scripts/prueba-costura.py" > "$log" 2>&1; then
    echo "  AGUANTA $nombre: la costura dio verde con $rel roto"
    AGUANTAN=$((AGUANTAN + 1))
  elif [ -n "$espera" ] && ! grep -q -- "$espera" "$log"; then
    echo "  AGUANTA $nombre: cayó, pero no por «$espera» (la costura falló por otra cosa)"
    AGUANTAN=$((AGUANTAN + 1))
  else
    echo "  cae     $nombre: ${espera:-la costura lo vio}"
    CAEN=$((CAEN + 1))
  fi
  # Se devuelve el fichero a su sitio: la mutación siguiente tiene que medir SU
  # rotura, no la suma de todas.
  rm -f "$TALLER/$rel"; cp "$REPO/$rel" "$TALLER/$rel"
  return 0
}

# 1 · si `Despertar` deja de ser puro, `Prueba7` no lo puede compilar en el portátil
#     y la hora se vuelve a esconder en el teléfono.
muta "Despertar deja de ser puro" "$DESP" \
  'import java.text.Normalizer;' \
  'import android.content.Context;
import java.text.Normalizer;' \
  "F16 · Despertar puro"

# 2 · la hora con dos dueños: `Alarma` trae su propio `Pattern`. Dos parsers pueden
#     decidir dos horas distintas para la misma frase.
muta "un segundo parser en Alarma" "$ALARMA" \
  '    static final int POSPONE_MIN = 5;' \
  '    static final int POSPONE_MIN = 5;
    static final java.util.regex.Pattern OTRA_HORA =
            java.util.regex.Pattern.compile("\\\\d");' \
  "F16 · dueño de la hora"

# 3 · se promete el minuto exacto sin red: el `catch (SecurityException` se cambia
#     por otra excepción y un fabricante que niegue lo exacto reventaría la alarma.
muta "la exactitud sin red" "$ALARMA" \
  '} catch (SecurityException aunqueDijeraQueSi) {' \
  '} catch (IllegalStateException aunqueDijeraQueSi) {' \
  "F16 · la exactitud"

# 4 · la frase honesta desaparece: queda `exacta:false`, que de madrugada no lee
#     nadie.
muta "la exactitud no se dice" "$ALARMA" \
  'no me da el minuto exacto' \
  'va como un reloj' \
  "F16 · la exactitud"

# 5 · el permiso que no se declara aparece: cambia la superficie medida del
#     manifiesto sin decirlo.
muta "aparece SCHEDULE_EXACT_ALARM" "$MANIFIESTO" \
  '    <application' \
  '    <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />
    <application' \
  "F16 · la exactitud"

# 6 · el receptor se abre: cualquier app podría despertar la alarma de CORT.
muta "el receptor se exporta" "$MANIFIESTO" \
  'android:name=".AlarmaSuena"
            android:exported="false" />' \
  'android:name=".AlarmaSuena"
            android:exported="true" />' \
  "F16 · el disparo"

# 7 · se pide `RECEIVE_BOOT_COMPLETED`: es un permiso nuevo y además la alarma no
#     se rearma sola, así que la promesa sería doble.
muta "aparece RECEIVE_BOOT_COMPLETED" "$MANIFIESTO" \
  '    <application' \
  '    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <application' \
  "F16 · el disparo"

# 8 · el aviso pierde su canal de alarma y sale por uno cualquiera: en Android 8+
#     se queda mudo o sin importancia alta.
muta "el aviso pierde su canal" "$ALARMA" \
  'static final String CANAL = "cort-alarma";' \
  'static final String CANAL = "cort";' \
  "F16 · el aviso"

# 9 · la cara deja de reconocer el evento: el despertador suena y no hay pantalla
#     que lo enseñe ni botón que lo calle.
muta "la cara no reconoce la alarma" "$TEL" \
  "if (ev.type === 'alarma')" \
  "if (ev.type === 'despertador')" \
  "F16 · la pantalla"

# 10 · el evento se pega sin comprobar que sea un objeto: un cuadro roto que la
#      cara no puede leer.
muta "el evento se pega a ciegas" "$PUENTE" \
  'if (dentro.startsWith("{") && dentro.endsWith("}")) {' \
  'if (true) {' \
  "F16 · la pantalla"

# 11 · el botón de detener pierde la guardia: en un APK viejo llamaría a una tecla
#      que no existe.
muta "detener sin guardia" "$TEL" \
  "puede('alarmaDetener')" \
  "true" \
  "F16 · las teclas"

# 12 · vuelve `alarmaPoner`: dos bocas para poner la alarma y una de ellas sin
#      llamar. Es el fallo que la 30.b ya prohíbe con `Elige`.
muta "vuelve la segunda boca para poner" "$PUENTE" \
  '    @JavascriptInterface
    public String alarmaEstado()' \
  '    @JavascriptInterface
    public String alarmaPoner(String t) { return Alarma.ponerDesde(act, t); }

    @JavascriptInterface
    public String alarmaEstado()' \
  "F16 · las teclas"

# 13 · `Cerebro.hora` vuelve a comerse lo de detrás: «07:30 con after dark para el
#      examen» pierde la canción y la nota antes de llegar a `Despertar`.
muta "la hora se come la cola" "$CEREBRO" \
  '+ " " + hhmm + " "
                             + dicho.substring(m.end())).trim();' \
  '+ " " + hhmm).trim();' \
  "F16 · la cola"

# 14 · `Prueba7` fuera del bucle: la suite daría verde sin haber mirado una sola
#      alarma.
muta "Prueba7 fuera del bucle" "$SH" \
  'Prueba6 Prueba7; do' \
  'Prueba6; do' \
  "F16 · Despertar puro"

# 15 · `Alarma` se cuela en la suite de papel, donde no hay `AlarmManager`: el
#      verde de `prueba-mente.sh` sería de cartón.
muta "Alarma entra en la suite de papel" "$SH" \
  '"$E"/Despertar.java "$T/src/com/cort/ia/"' \
  '"$E"/Despertar.java "$E"/Alarma.java "$T/src/com/cort/ia/"' \
  "F16 · Despertar puro"

# 16 · la tabla pierde una frase compuesta: el fallo de la cola podría volver sin
#      que Prueba3 se ponga rojo.
muta "la tabla pierde la frase compuesta" "$P3" \
  '            {"despiertame a las 7:30 con after dark para el examen", "alarma",
             "07:30 con after dark para el examen"},
' \
  '' \
  "F16 · la cola"

# 17 · la corrección del hueco de marzo resta en vez de sumar: devuelve las 01:30
#      del día siguiente, una hora que además de no existir es el pasado. La
#      costura lo ve (el `puesto < pedido`), y aquí se exige además que `Prueba7`
#      lo nombre: es la prueba que de verdad entiende el reloj.
if [ -z "$SOLO" ] || printf '%s' "marzo devuelve el pasado" | grep -qi -- "$SOLO"; then
  rm -f "$TALLER/$DESP"
  cp "$REPO/$DESP" "$TALLER/$DESP"
  if reemplaza "$DESP" 'if (puesto < pedido)' 'if (puesto != pedido)'; then
    log="$TALLER/mente.log"
    if bash "$TALLER/scripts/prueba-mente.sh" > "$log" 2>&1; then
      echo "  AGUANTA marzo devuelve el pasado: la suite dio verde"
      AGUANTAN=$((AGUANTAN + 1))
    elif ! grep -q "FALLO  DST de marzo" "$log"; then
      echo "  AGUANTA marzo devuelve el pasado: cayó, pero no por DST de marzo"
      AGUANTAN=$((AGUANTAN + 1))
    else
      echo "  cae     marzo devuelve el pasado: Prueba7 lo vio («DST de marzo»)"
      CAEN=$((CAEN + 1))
    fi
  else
    echo "  ???     marzo devuelve el pasado: el reemplazo no encontró el umbral"
    AGUANTAN=$((AGUANTAN + 1))
  fi
fi

# 18 · «con la canción» sin nombre se convierte en una canción llamada «la
#      canción»: la alarma prometería una pieza que no existe. La costura no lo
#      puede ver; sólo `Prueba7` escucha la frase.
if [ -z "$SOLO" ] || printf '%s' "canción inventada" | grep -qi -- "$SOLO"; then
  rm -f "$TALLER/$DESP"
  cp "$REPO/$DESP" "$TALLER/$DESP"
  if reemplaza "$DESP" \
      'if (cancion.matches("(?:la |el |una |un )?(?:cancion|musica|tema)")) cancion = "";' \
      'if (false) cancion = "";'; then
    log="$TALLER/mente.log"
    if bash "$TALLER/scripts/prueba-mente.sh" > "$log" 2>&1; then
      echo "  AGUANTA canción inventada: la suite dio verde"
      AGUANTAN=$((AGUANTAN + 1))
    elif ! grep -q "FALLO  sin nombre no hay canción" "$log"; then
      echo "  AGUANTA canción inventada: cayó, pero no por la canción sin nombre"
      AGUANTAN=$((AGUANTAN + 1))
    else
      echo "  cae     canción inventada: Prueba7 lo vio («sin nombre no hay canción»)"
      CAEN=$((CAEN + 1))
    fi
  else
    echo "  ???     canción inventada: el reemplazo no encontró el relleno"
    AGUANTAN=$((AGUANTAN + 1))
  fi
fi

echo
if [ "$AGUANTAN" -gt 0 ]; then
  echo "TALLER F16 CON $AGUANTAN AGUANTE(S): hay comprobaciones que no prueban nada."
  exit 1
fi
[ "$CAEN" -eq 0 ] && echo "el filtro no casó con ninguna mutación" && exit 0
echo "TALLER F16 OK: $CAEN mutaciones, las $CAEN caen nombrando lo que faltaba."
