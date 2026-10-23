#!/usr/bin/env bash
# Taller de mutaciones de la mitad del TELÉFONO de F13 (`Ollama.java` + `Mente.java`).
#
# Por qué existe: **un verde que no puede caer no es prueba.** `scripts/prueba-mente.sh`
# da verde sobre el Ollama de mentira del JDK, y aquí se rompe el Java a propósito —una
# mutación por cada red que `Prueba4` vigila— para exigir que caiga Y ADEMÁS diga qué
# comprobación era la que faltaba. Si el código roto sigue dando verde, la comprobación
# es decoración y la dueña volvería a ver la barra quieta.
#
# Qué se rompe, dicho en una línea: el progreso sumado por capa, el ping corto antes de
# abrir `/api/pull`, y el cancelar (el interruptor, la corriente que se cierra, la
# conexión que se suelta, el aviso que NO se manda y la acción que conoce `Mente`).
#
# Dónde se corre: en el taller, NUNCA como paso del pipeline. El pipeline ya corre
# `prueba-mente.sh` limpio. Trabaja sobre una copia de links duros en `/tmp` y rompe el
# link antes de tocar, así que el repo no se entera.
#
# Uso:  bash scripts/taller-ollama.sh     (≈3-4 minutos: cada mutación recompila Java)
#       bash scripts/taller-ollama.sh cancelar      (sólo las que digan «cancelar»)
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TALLER="$(mktemp -d /tmp/cort-taller-ollama-XXXXXX)"
trap 'rm -rf "$TALLER"' EXIT

cp -al "$REPO/apps" "$TALLER/apps" 2>/dev/null || cp -a "$REPO/apps" "$TALLER/apps"
mkdir -p "$TALLER/scripts"
cp -al "$REPO/scripts/prueba-mente.sh" "$TALLER/scripts/" 2>/dev/null \
  || cp -a "$REPO/scripts/prueba-mente.sh" "$TALLER/scripts/"

OLLAMA="apps/apk/src/com/cort/ia/Ollama.java"
MENTE="apps/apk/src/com/cort/ia/Mente.java"

CAEN=0
AGUANTAN=0
SOLO="${1:-}"
[ -n "$SOLO" ] && echo "  (filtro: sólo las mutaciones que contienen «$SOLO»)"

muta() {  # muta <nombre> <sed> [archivo; por defecto Ollama.java]
  local nombre="$1" expr="$2" rel="${3:-$OLLAMA}"
  # Con `SOLO` se corre una mutación concreta (para no recompilar las trece cuando se
  # está arreglando una frase del taller). No cambia nada más: mismo taller, misma suite.
  if [ -n "$SOLO" ] && ! printf '%s' "$nombre" | grep -qi -- "$SOLO"; then
    return 0
  fi
  rm -f "$TALLER/$rel"                       # rompe el link duro antes de tocar
  cp "$REPO/$rel" "$TALLER/$rel"
  sed -i "$expr" "$TALLER/$rel"
  if cmp -s "$REPO/$rel" "$TALLER/$rel"; then
    echo "  ???     $nombre: el sed no cambió nada (mutación mal escrita)"
    AGUANTAN=$((AGUANTAN + 1))
    return
  fi
  local log="$TALLER/salida.log"
  if bash "$TALLER/scripts/prueba-mente.sh" > "$log" 2>&1; then
    echo "  AGUANTA $nombre: la suite dio verde con $rel roto"
    AGUANTAN=$((AGUANTAN + 1))
  else
    # El motivo se busca en los cuatro modos que tiene `prueba-mente.sh` de caer:
    # una comprobación suya (`  MAL`), el recuento final (`FALLEN`), un javac que no
    # compila (`error:`) o una excepción suelta. Si ninguno aparece, se imprime la
    # última línea del registro: sin motivo, el «cae» de abajo no sería evidencia.
    local motivo
    # Se imprimen hasta TRES comprobaciones rotas, no sólo la primera: una mutación
    # suele romper de rebote algo de su entorno (mover el ping cambia el orden de los
    # cuadros y toca la prueba de las capas), y si se muestra una sola línea parece que
    # la mutación cayó por el motivo equivocado.
    motivo=$(grep -E '^  MAL |^FALLEN |error:|Exception in thread' "$log" | head -3 | cut -c1-88 | paste -sd' | ' -)
    [ -n "$motivo" ] || motivo=$(grep -v '^\s*$' "$log" | tail -1 | cut -c1-88)
    echo "  cae     $nombre -> $motivo"
    CAEN=$((CAEN + 1))
  fi
}

echo
echo "· taller de mutaciones de la descarga del teléfono"

# — el progreso: varias capas, sumadas —
muta "la última capa gana (el bug de la barra quieta)" \
  's/hecho += capa\[0\]; total += capa\[1\];/hecho = capa[0]; total = capa[1];/'
muta "las capas no se anotan" \
  '/capas.put(mota, new long/d'
muta "una línea de verificación borra el total de su capa" \
  '/if (t <= 0 && capas.containsKey(mota)) t = capas.get(mota)\[1\];/d'
muta "el porcentaje se dice sin sumar" \
  's/boolean salto = pct - puntoEnvio >= 0.05;/boolean salto = pct - puntoEnvio >= 0.05; hecho = 0;/'

# — el ping corto antes de abrir la bajada —
muta "sin ping: un PC mudo se esperaría 90 segundos" \
  's/String ver = version(servidor());/String ver = "0.0.0";/'
muta "el ping se hace pero no mira el resultado" \
  's/if (ver == null) {/if (ver == null \&\& false) {/'

# — cancelar —
muta "cancelar no mueve el interruptor" \
  '/^        quieroCancelar = true;$/d'
# Las dos formas de cerrar —la `InputStream` bloqueada y el `HttpURLConnection`— son
# redundantes a propósito, y está MEDIDO: con `Prueba4` en el escenario `callada`,
# quitar SÓLO una sigue despertando al lector dentro de los 2 s que espera la prueba.
# Por eso no tienen mutación cada una (sería exigirle a la suite que cayera con código
# que funciona) y sí la tiene quitarlas LAS DOS: ahí el hilo se queda clavado leyendo
# un servidor mudo, y el «cancelado» que contesta el puente sería una mentira.
muta "cancelar no cierra nada (ni corriente ni conexión)" \
  's/^        cerr(entradaBajada);$/        \/\/ MUTA: sin cerrar la corriente/; s/if (c != null) { try { c.disconnect(); } catch (Exception yaCerrada) { } }/if (c == null) { }/'
muta "cancelar avisa a la dueña de algo que ella cortó" \
  's/ultimoFallo = "cancelaste la bajada de " + nombre;/ultimoFallo = "cancelaste la bajada de " + nombre; Timbre.bajada(app, false, nombre, 0, 0, ultimoFallo, servidor());/'
muta "la bajada termina y deja el modelo apuntado (el botón queda vivo)" \
  '/^            bajandoModelo = "";$/d'
muta "el cuadro de progreso no dice cuántas capas lleva" \
  's/+ ",\\"capas\\":" + capas.size()//'

# — y el contrato por el que entra la cara —
muta "Mente no conoce la acción cancelar" "s/\"cancela\".equals(accion)/false/" "$MENTE"

# Con el código limpio tiene que volver a dar verde; si no, el recuento de arriba
# no significa nada (el taller se quedó con un fichero roto).
rm -f "$TALLER/$OLLAMA" "$TALLER/$MENTE"
cp "$REPO/$OLLAMA" "$TALLER/$OLLAMA"
cp "$REPO/$MENTE" "$TALLER/$MENTE"
if bash "$TALLER/scripts/prueba-mente.sh" > "$TALLER/limpio.log" 2>&1; then
  echo
  echo "  (y con el código limpio vuelve a dar verde)"
else
  echo
  echo "  OJO: con el código limpio la suite cayó"
  AGUANTAN=$((AGUANTAN + 1))
fi
echo
echo "mutaciones: caen $CAEN, aguantan $AGUANTAN"
[[ $AGUANTAN -eq 0 ]]
