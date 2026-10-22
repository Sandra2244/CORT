#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────────
# perfil.py — el manifiesto de CORT en dos perfiles, con UNA sola variable.
#
# Por qué existe. Medido el 2026-10-22 con los tres APK en el mismo disco (el
# `1.1.0` original de la dueña, el `1.1.4` que SALIÓ de este pipeline y que a ella
# se le instala, y el `2.4.2-ligero` que Play Protect BLOQUEA), leyendo la charca de
# cadenas UTF-16 del `AndroidManifest.xml` BINARIO de cada uno — el mismo método
# está ahora dentro de `scripts/audita-apk.sh`, renglón «manifiesto binario», así
# que el pipeline lo comprueba en cada Release:
#
#   APK                 permisos   servicios privilegiados                 instala
#   CORT-IA-1.1.0          13      ninguno                                  sí
#   CORT-IA-1.1.4          13      ninguno                                  sí
#   CORT-IA-2.4.2-ligero   28      4 permisos BIND_* sobre cinco servicios   no
#                                    (asistente, sesión, reconocedor, avisos,
#                                     baldosín) + ASSIST y VOICE_COMMAND
#
# El peso y las `.so` ya estaban descartados por la ronda 2.4.2: el ligero no lleva
# ni una ni otro y se bloquea igual, y su `AndroidManifest.xml` es idéntico byte a
# byte al del completo. Lo único que separa lo que entra de lo que no es la
# SUPERFICIE DE INTEGRACIÓN: `BIND_VOICE_INTERACTION` (ser el asistente del
# sistema), `BIND_SPEECH_RECOGNIZER`, `BIND_NOTIFICATION_LISTENER_SERVICE` (leer
# todas las notificaciones, WhatsApp incluido), `BIND_QUICK_SETTINGS_TILE`,
# `ACTION_ASSIST`/`ACTION_VOICE_COMMAND`, y el trío `CALL_PHONE` + `READ_CONTACTS`
# + `READ_CALENDAR`. Ese paquete de declaraciones es, literalmente, la firma con la
# que los clasificadores automáticos describen un troyano de accesibilidad: no
# significa que CORT lo sea, significa que un escáner sin contexto no tiene forma
# de saberlo.
#
# Así que el experimento se hace sobre ESA variable:
#
#   completo  → el manifiesto de siempre (lo que ella ya tiene publicado), más la
#               única línea nueva: la meta-datos del perfil.
#   nucleo    → el MISMO CORT sin la superficie privilegiada: el perfil que tiene
#               que instalarse sí o sí, porque es el que tenía el 1.1.4.
#
# Cómo se corta: el manifiesto lleva regiones marcadas con
# `<!-- PERFIL-DESDE:tag -->` / `<!-- PERFIL-HASTA:tag -->`, y cada perfil nombra
# las tags que tira. Los marcadores NO se copian a la salida, NUNCA, los de la
# región que se queda y los de la que se tira: los comentarios tampoco llegan al
# `AndroidManifest.xml` binario (aapt2 no los copia), así que al texto no les
# afectan y a cambio la salida puede volver a pasar por este script sin sorpresas.
#
# Lo cual se puede comprobar renglón por renglón, y está comprobado (2026-10-22, y
# `scripts/prueba-costura.py` sector 14 lo repite en cada ronda):
#
#   diff <(grep -v PERFIL- AndroidManifest.xml) manifest-completo.xml   → UNA línea
#
# y esa línea es el `<meta-data>` del perfil. Es decir: el envase `completo` que
# sale de aquí es EL MISMO que ella ya tiene, y por eso la comparación entre rondas
# sigue siendo limpia. El `nucleo` sale de quitar las tres regiones y nada más:
# 24 permisos y seis servicios pasan a 21 y uno, con cero delatores.
#
# Y el APK tiene que saber qué lleva dentro, porque una app que ofrece una puerta
# que no está declarada miente: `perfil.py` clava
# `<meta-data android:name="com.cort.ia.PERFIL" android:value="…"/>` dentro de
# `<application>`, `CortNative.capacidades()` lo lee y la cara esconde lo que no
# puede ofrecer.
#
# Salida: el texto del manifiesto por la stdout (o por `--salida`), y por stderr un
# resumen de lo que hay en cada uno. Si el recorte produjera XML inválido, el
# script sale en 1: mejor un pipeline rojo que un instalador roto.
# ─────────────────────────────────────────────────────────────────────────────
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Lo que delata el escáner, en las palabras exactas del manifiesto. Se comprueba
# contra el texto recortado: si una de estas cadenas sobrevive al perfil `nucleo`,
# el recorte no ha servido para nada y hay que saberlo aquí, no en el teléfono.
DELATORES = [
    "android.permission.BIND_VOICE_INTERACTION",
    "android.service.voice.VoiceInteractionService",
    "android.permission.BIND_SPEECH_RECOGNIZER",
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE",
    "android.service.notification.NotificationListenerService",
    "android.permission.BIND_QUICK_SETTINGS_TILE",
    "android.service.quicksettings.action.QS_TILE",
    "android.intent.action.ASSIST",
    "android.intent.action.VOICE_COMMAND",
    "android.permission.CALL_PHONE",
    "android.permission.READ_CONTACTS",
    "android.permission.READ_CALENDAR",
]

# Qué se tira en cada perfil. `completo` = la lista vacía.
PERFILES = {
    "completo": [],
    "nucleo": ["llamadas", "acciones-asistente", "servicios-privilegiados"],
}

DESDE = "<!-- PERFIL-DESDE:{} -->"
HASTA = "<!-- PERFIL-HASTA:{} -->"


def recorta(texto: str, perfil: str) -> str:
    """Devuelve el manifiesto con las regiones del perfil fuera."""
    lineas = texto.splitlines(keepends=True)
    fuera = set(PERFILES[perfil])
    activo = None          # tag de la región que se está tirando
    salto = []             # tags con principio pero sin fin: error de marcado
    salida = []
    for ln in lineas:
        m = re.search(r"<!--\s*PERFIL-DESDE:([a-z0-9-]+)\s*-->", ln)
        if m:
            tag = m.group(1)
            if tag in fuera:
                if activo is not None:
                    salto.append(activo)
                activo = tag
                continue
            continue                   # región de otro perfil: se queda entera, pero
                                         # el marcador NO: ningún `<!-- PERFIL-* -->`
                                         # sale en la salida, porque ninguno llega al
                                         # binario y así el fichero recortado puede
                                         # volver a recortarse sin sorpresas.
        m = re.search(r"<!--\s*PERFIL-HASTA:([a-z0-9-]+)\s*-->", ln)
        if m:
            tag = m.group(1)
            if activo == tag:
                activo = None
            continue                   # el marcador de cierre tampoco se copia
        if activo is None:
            salida.append(ln)
    if activo is not None:
        salto.append(activo)
    if salto:
        sys.exit(f"perfil.py: regiones sin cerrar en AndroidManifest.xml: "
                 f"{', '.join(sorted(set(salto)))}")
    return "".join(salida)


def pon_perfil(texto: str, perfil: str) -> str:
    """Clava el `<meta-data>` del perfil dentro de `<application>`.

    Si el fichero de entrada ya llevara una, se REESCRIBE su valor en vez de
    respetarla: lo que declara el envase tiene que ser lo que se pidió compilar, no
    lo que decía el último recorte. La trampa es real — `--origen` acepta cualquier
    manifiesto, y un `build/manifest-completo.xml` recortado otra vez a `nucleo`
    saldría con la etiqueta de `completo` dentro, que es justo la mentira que este
    renglón existe para evitar.
    """
    valor = f'android:value="{perfil}"'
    if "com.cort.ia.PERFIL" in texto:
        return re.sub(r'(<meta-data android:name="com\.cort\.ia\.PERFIL" )android:value="[^"]*"',
                      r"\g<1>" + valor, texto, count=1)
    marca = f'<meta-data android:name="com.cort.ia.PERFIL" {valor} />'
    i = texto.find("<application")
    if i < 0:
        sys.exit("perfil.py: no encuentro <application>, no sé dónde poner el perfil")
    j = texto.index(">", i)            # el `>` que cierra la etiqueta de apertura
    return texto[: j + 1] + "\n        " + marca + texto[j + 1:]


def sin_comentarios(texto: str) -> str:
    """El manifiesto como lo ve aapt2: los `<!-- … -->` no llegan al binario.

    Sin esto el contador se crece: el propio fichero lleva un renglón de
    documentación que escribe `<uses-permission` dentro de un comentario, y un
    `DELATOR` citado en un comentario no declara nada. Lo que se comprueba tiene
    que ser lo que se publica.
    """
    return re.sub(r"<!--.*?-->", "", texto, flags=re.S)


def resumen(texto: str) -> str:
    limpio = sin_comentarios(texto)
    perm = len(re.findall(r"<uses-permission\b", limpio))
    serv = len(re.findall(r"<service\b", limpio))
    activos = [d for d in DELATORES if d in limpio]
    return (f"permisos {perm} · servicios {serv} · delatores {len(activos)}"
            + (" — " + ", ".join(a.split(".")[-1] for a in activos) if activos else ""))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Recorta AndroidManifest.xml al perfil pedido y le clava la meta-datos del perfil."
    )
    ap.add_argument("--perfil", default="completo", choices=sorted(PERFILES))
    ap.add_argument("--origen", default=str(Path(__file__).parent / "AndroidManifest.xml"))
    ap.add_argument("--salida", default="")
    args = ap.parse_args()

    origen = Path(args.origen).read_text(encoding="utf-8")
    texto = pon_perfil(recorta(origen, args.perfil), args.perfil)

    # El XML tiene que seguir siendo XML: un corte mal marcado suelta una etiqueta
    # huérfana, y eso aapt2 lo casa con un error opaco en la mitad del pipeline.
    try:
        ET.fromstring(texto)
    except ET.ParseError as e:
        sys.exit(f"perfil.py: el perfil `{args.perfil}` produce un manifiesto inválido: {e}")

    if args.salida:
        Path(args.salida).write_text(texto, encoding="utf-8")
    else:
        sys.stdout.write(texto)

    print(f"perfil {args.perfil}: {resumen(texto)}", file=sys.stderr)
    if args.perfil != "completo":
        sobrantes = [d for d in DELATORES if d in sin_comentarios(texto)]
        if sobrantes:
            sys.exit(f"perfil.py: el recorte dejó {len(sobrantes)} delatores dentro: "
                     f"{', '.join(sobrantes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
