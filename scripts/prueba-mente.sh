#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# prueba-mente.sh — el cerebro del APK, probado EN EL PORTÁTIL, sin teléfono.
#
# Siete clases de `apps/apk/src/com/cort/ia` son Java puro o casi puro: `Razon`
# (cuentas, unidades, fechas), `Cerebro` (la tabla de frases), `Nube` (el
# proveedor), `Ollama` (los cerebros del PC de casa por Wi-Fi), `Mente` (quién
# responde cada frase), `Elige` (qué canción, qué lista, qué preset) y
# `Despertar` (qué hora, qué canción y qué nota lleva una alarma, y cuándo
# toca). Lo que las ata a Android son cinco tipos: `Log`, `Context`,
# `SharedPreferences`, `AssetManager` y el `org.json` del sistema. Aquí se les
# pone su **gemelo de papel** (`apps/apk/prueba/papeles`) y con eso el JDK de a
# pie compila y ejecuta las siete pruebas:
#
#   Prueba.java   · `Razon` a pelo: 43 frases suyas y seis que no lo son.
#   Prueba2.java  · la RUTA: acción conocida → `Cerebro`; cuenta/unidad/hora →
#                   `Razon`; lo desconocido → la nube o la respuesta honesta.
#   Prueba3.java  · las 283 frases de la tabla, una por una, contra las DOS
#                   tablas (la del asset y la del código) para ver los robos
#                   por orden — sólo se ven aquí, nunca en la cara.
#   Prueba4.java  · `Ollama` contra un Ollama de mentira levantado en el propio
#                   JDK (`com.sun.net.httpserver`): listar, bajar con progreso,
#                   avisar una vez por final (el aviso bueno, y el de la cortada),
#                   borrar en las dos formas de la API, descubrir y que la pregunta
#                   se conteste con el modelo de casa. Todo por `127.0.0.1`.
#   Prueba5.java  · el diccionario en LOS DOS SENTIDOS: las 208 frases de razón
#                   (`casos-razon.txt`, salidas de saber.py) tienen que contestarse,
#                   y las 192 de casa/nube (`casos-no-locales.txt`) no pueden
#                   contestarlas ni Cerebro ni Razon. Un verde que no puede caerse
#                   no es prueba: si una frase de casa se contesta en local, rojo.
#   Prueba6.java  · `Elige` a pelo: el título exacto gana al remix, la tilde no
#                   separa, «mr kitty» lleva a la canción del artista, lo que no
#                   está devuelve -1, y los presets del ecualizador se traducen
#                   de «clásica»/«graves» al nombre inglés del aparato.
#   Prueba7.java  · `Despertar` a pelo: «a las 7:30 con after dark para el
#                   examen» se parte en hora, canción y nota; sin hora no hay
#                   plan; el próximo disparo es estrictamente futuro (hoy, mañana,
#                   en los dos cambios de hora) y «falta» se dice en palabras.
#
# `--release 11` no se pasa: en este portátil `javac` sólo existe como módulo del
# JDK (`java -m jdk.compiler/…`) y ese punto de entrada no acepta la bandera. El
# APK se compila con `--release 11` en GitHub Actions; aquí se comprueba LOGICA.
#
# Por eso `Timbre.java` (el aviso de Android de que la bajada terminó) NO se copia
# aquí: habla con `NotificationManager` y eso en el JDK no existe. Lo que sí entra
# es su gemelo de papel (`prueba/papeles/com/cort/ia/Timbre.java`), que anota cada
# aviso en `Timbre.PUESTOS`, y `Prueba4` los cuenta: así se comprueba en casa que
# `Ollama` avisa justo cuando toca, y el `notify` de verdad se mira en la costura
# [24] sobre el fichero del APK. La firma de los dos `Timbre` es la misma, y si un
# día cambian una sin la otra, este `javac` no compila.
#
# Uso:  bash scripts/prueba-mente.sh
#       JAVA_MEM=192m bash scripts/prueba-mente.sh   (si el portátil va justo)
# Tarda ~25 s. No toca el teléfono ni la red: sólo JDK.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."
RAIZ=$(pwd)
E=$RAIZ/apps/apk/src/com/cort/ia
P=$RAIZ/apps/apk/prueba
T=/tmp/cort-mente

# 1 · el escenario, siempre limpio: fuentes + gemelos de papel + pruebas
rm -rf "$T"; mkdir -p "$T/src/com/cort/ia" "$T/papeles" "$T/assets" "$T/assets-vacias" "$T/out"
cp "$E"/Cerebro.java "$E"/Nube.java "$E"/Mente.java "$E"/Razon.java "$E"/Ollama.java "$E"/Elige.java "$E"/Despertar.java "$T/src/com/cort/ia/"
cp -r "$P"/papeles/* "$T/papeles/"
cp "$P"/Prueba.java "$P"/Prueba2.java "$P"/Prueba3.java "$P"/Prueba4.java "$P"/Prueba5.java "$P"/Prueba6.java "$P"/Prueba7.java "$T/src/com/cort/ia/"
cp "$RAIZ"/apps/apk/assets/habilidades.json "$T/assets/"
cp "$P"/casos-razon.txt "$P"/casos-no-locales.txt "$T/"

# 2 · `javac` como orden o como módulo del JDK, según el portátil
si_javac() {
  if command -v javac >/dev/null 2>&1; then
    javac "$@"
  else
    java -Xmx"${JAVA_MEM:-256m}" -m jdk.compiler/com.sun.tools.javac.Main "$@"
  fi
}

LISTA=$(find "$T/papeles" "$T/src" -name '*.java')
echo "== compilando $(echo "$LISTA" | wc -l) ficheros de papel"
# `--add-modules jdk.httpserver` hace falta desde que `Prueba4` monta un Ollama de
# mentira: el servidor HTTP del JDK no está en el conjunto de módulos raíz cuando se
# compila desde el classpath de toda la vida. En Android ese servidor NO existe (allí
# se habla con `HttpURLConnection`), así que la bandera sólo vive en esta prueba.
# shellcheck disable=SC2086
si_javac -encoding UTF-8 --add-modules jdk.httpserver -d "$T/out" $LISTA

# 3 · las siete suites; la última manda en el código de salida
#
# Cada salida va a su propio `.log` y se imprime entera SI ALGO FALLA. Con
# `java … | tail -1` se perdería el detalle justo cuando hace falta: `pipefail`
# devuelve el código, sí, pero la línea que explica el fallo se queda arriba y
# fuera de la pantalla. `JAVA_MEM` baja el techo del montón cuando el portátil
# va justo de RAM (aquí son 1,8 GiB compartidos con el editor).
MEM="${JAVA_MEM:-256m}"
pasa=0
fallan=0
for suite in Prueba Prueba2 Prueba3 Prueba4 Prueba5 Prueba6 Prueba7; do
  caso="Razon a pelo"; [ "$suite" = Prueba2 ] && caso="la ruta de Mente"
  [ "$suite" = Prueba3 ] && caso="las frases de la tabla"
  [ "$suite" = Prueba4 ] && caso="Ollama en la Wi-Fi de casa"
  [ "$suite" = Prueba5 ] && caso="el diccionario, en los dos sentidos"
  [ "$suite" = Prueba6 ] && caso="elegir la canción, la lista y el preset"
  [ "$suite" = Prueba7 ] && caso="partir el despertar: hora, canción, nota"
  echo "== $caso"
  set +e
  java -Xmx"$MEM" --add-modules jdk.httpserver -cp "$T/out" "com.cort.ia.$suite" > "$T/$suite.log" 2>&1
  st=$?
  set -e
  if [ $st -eq 0 ]; then
    tail -1 "$T/$suite.log"; pasa=$((pasa + 1))
  else
    fallan=$((fallan + 1))
    cat "$T/$suite.log"                       # el fallo se lee entero
    echo "   (sale $st — log: $T/$suite.log)"
  fi
done
[ $fallan -eq 0 ] || { echo "FALLEN $fallan suite(s) de 7"; exit 1; }
FRASES=$(python3 -c 'import json;d=json.load(open("apps/apk/assets/habilidades.json"));print(sum(len(p["patrones"]) for p in d["patrones"]))' 2>/dev/null || echo "?")
echo "MENTE OK: las 7 suites pasan sobre las $FRASES frases de la tabla."
