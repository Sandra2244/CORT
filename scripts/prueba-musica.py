#!/usr/bin/env python3
"""Prueba decisiva del núcleo de música del PC (`backend/app/musica.py`), SIN reproducir nada.

Qué tiene que salir cierto para que la dueña pueda fiarse de la pantalla de música:

  1. **Las etiquetas se leen de verdad.** El lector ID3 está escrito a mano (stdlib
     no tiene, y no se va a meter `mutagen` en el instalador), así que se prueba
     contra bytes reales: v2.4 con UTF-8, v2.3 con tamaños que NO son synchsafe,
     v2.2 con ids de tres letras, UTF-16 con BOM (el que traen los catorce mp3 de
     su disco, medido 2026-10-26: `TIT2` salía como `\\ufeffNewsinko` sin quitarlo),
     y una cabecera mentira que tiene que dar `{}` en vez de reventar.
  2. **Nada se inventa.** `dur` sale de `TLEN` o del `wave` de stdlib; en ogg/flac
     se queda vacío. `artista` sale de `TPE1` o se queda vacío — no se presta el
     nombre de la carpeta como hacía `sensors.py:166`. El estilo, de `TCON` o de la
     carpeta, y las dos cosas se devuelven separadas porque en su disco **ningún**
     mp3 trae `TCON`.
  3. **La seguridad no se relaja.** Un enlace simbólico dentro de Música que apunta
     a fuera no puede ni listarse ni reproducirse, y `/api/play` no acepta una ruta
     que no esté validada por `sensors.music_path`.
  4. **El reproductor se nombra con lo que responde el sistema**, y si el aparato no
     confirma que suena se dice `desconocido`. La prueba **sustituye `subprocess`**
     por un grabador: ni VLC ni Strawberry se abren mientras corre esta batería,
     que es lo que manda la regla de no congelar su portátil de dos núcleos.
  5. **Nunca se sobrescribe una playlist**: si el nombre existe, sale `existe: True`
     y el archivo viejo queda byte a byte igual.
  6. Las frases de voz nuevas («pon música de X», «pon la lista Y», «pon música del
     estilo Z») buscan de verdad y, cuando no hay nada, **dicen lo que hay** en vez
     de poner una canción al azar.

No se toca `~/Música` ni `~/.cort` de la dueña: todo corre en un directorio
temporal, con `CORT_HOME` y `sensors.ROOTS` apuntando allí antes de importar.

Uso:  python3 scripts/prueba-musica.py     (dos segundos, sin red, sin reproductor)
"""
import json
import os
import pathlib
import shutil
import struct
import sys
import tempfile
import time

# El sector [7] quiere importar `main.py`, que necesita FastAPI. En el equipo de
# Actions no está (corre `python3` pelado a propósito), pero en el portátil sí vive
# en `.venv`: si este script se lanza con el python del sistema y el entorno
# existe, se relanza dentro de él. Sin entorno, `informe()` igualmente se prueba
# entero porque `musica.py` no depende del framework.
_VENV = pathlib.Path(__file__).resolve().parent.parent / ".venv" / "bin" / "python"
if _VENV.exists() and pathlib.Path(sys.prefix).resolve() != _VENV.parent.parent.resolve():
    try:
        import fastapi  # noqa: F401
    except ModuleNotFoundError:
        os.execv(str(_VENV), [str(_VENV), *sys.argv])

TRAJO = pathlib.Path(tempfile.mkdtemp(prefix="cort-musica-"))
os.environ["CORT_HOME"] = str(TRAJO / "casa")            # las listas de CORT van aquí
# `CORT_CODIGO` permite probar una COPIA del código (la batería de mutaciones la
# usa): el repo nunca se muta, y sin esa variable se prueba el código de siempre.
CODIGO = pathlib.Path(os.environ.get("CORT_CODIGO")
                      or pathlib.Path(__file__).resolve().parent.parent / "backend" / "app")
sys.path.insert(0, str(CODIGO))

import rutas                                              # noqa: E402
import sensors                                            # noqa: E402

MUS = TRAJO / "Música"
FUERA = TRAJO / "afuera"
for d in (MUS, FUERA):
    d.mkdir(parents=True, exist_ok=True)
sensors.ROOTS["Música"] = MUS
sensors.ROOTS["Music"] = TRAJO / "no-hay"                 # una sola raíz, sin sorpresas

import musica                                             # noqa: E402
import actions                                           # noqa: E402

FALLOS = []
_LIMPIAR = []


def dice_ok(que, como):
    print(f"  ok   {que:52} {como}")


def falla(que, como):
    FALLOS.append(que)
    print(f"  FALLA {que:52} {como}")


def espero(que, obtenido, querido):
    if obtenido == querido:
        dice_ok(que, repr(obtenido))
    else:
        falla(que, f"dio {obtenido!r} y tenía que dar {querido!r}")


def pasa(que, se_cumple, como=""):
    (dice_ok if se_cumple else falla)(que, como or ("se cumplió" if se_cumple else "NO"))


# ── cómo se fabrica un mp3 con etiquetas de verdad ─────────────────────────────
def _synch(n: int) -> bytes:
    return bytes([(n >> 21) & 0x7f, (n >> 14) & 0x7f, (n >> 7) & 0x7f, n & 0x7f])


def _marco(id_: str, datos: bytes, version: int) -> bytes:
    if version == 2:                                     # v2.2 escribe ids de TRES letras
        id_ = {"TIT2": "TT2", "TPE1": "TP1", "TALB": "TAL",
               "TCON": "TCO", "TLEN": "TLE"}.get(id_, id_)
    if len(id_) == 3:                                    # tamaño de 3 bytes, sin banderas
        return (id_.encode() + bytes([(len(datos) >> 16) & 0xff, (len(datos) >> 8) & 0xff,
                                      len(datos) & 0xff]) + datos)
    tam = _synch(len(datos)) if version == 4 else len(datos).to_bytes(4, "big")
    return id_.encode() + tam + b"\x00\x00" + datos       # v2.3/2.4: id de 4 + 2 banderas


def _txt(texto: str, cod: int) -> bytes:
    """El byte de codificación que usa ID3: 0 latin-1, 1 utf-16 con BOM, 2 utf-16be, 3 utf-8."""
    if cod == 0:
        return b"\x00" + texto.encode("latin-1")
    if cod == 1:
        return b"\x01\xff\xfe" + texto.encode("utf-16-le")
    if cod == 2:
        return b"\x02" + texto.encode("utf-16-be")
    return b"\x03" + texto.encode("utf-8")


def mp3(ruta: pathlib.Path, campos: dict, version: int = 4, cod: int = 3,
        relleno: bytes = b"\xff\xfb\x90\x00-cuerpo de audio de mentira"):
    cuerpo = b"".join(_marco(k, _txt(v, cod), version) for k, v in campos.items())
    cab = b"ID3" + bytes([version, 0, 0]) + _synch(len(cuerpo))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(cab + cuerpo + relleno)


# la discoteca de pega, calcada de la suya (carpeta/canción.mp3, letras .lrc, vídeos .mp4)
mp3(MUS / "Dark Rose" / "2 on.mp3",
    {"TIT2": "2 on — tinashe", "TPE1": "cyberysz", "TALB": "cyberysz", "TLEN": "222000",
     "TSSE": "Lavf60.3.100"})
mp3(MUS / "Looksmaxing " / "closer.mp3",
    {"TIT2": "closer - the chainsmokers", "TPE1": "saturday night", "TLEN": "207000"},
    version=3, cod=1)                                     # v2.3 + UTF-16 con BOM, sin TALB
mp3(MUS / "snaptube" / "download" / "SnapTube Audio" / "Exitin x 2 on(MP3_160K).mp3",
    {"TIT2": "Exitin x 2 on (Slowed)", "TPE1": "Newsinko", "TALB": "Newsinko",
     "TLEN": "260000", "TCON": "Electronic"})
mp3(MUS / "snaptube" / "v22.mp3", {"TIT2": "Tema viejo", "TPE1": "Autor"}, version=2, cod=0)
mp3(MUS / "Canciones" / "canion.mp3", {"TIT2": "Canción Rota", "TPE1": "La Tilde",
                                       "TALB": "Maqueta 2024", "TCON": "Rock en Español",
                                       "TLEN": "61000"})
(MUS / "CORT Demo").mkdir(parents=True, exist_ok=True)
import wave                                              # noqa: E402
with wave.open(str(MUS / "CORT Demo" / "Tono.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
    w.writeframes(b"\x00\x00" * 8000 * 10)                # 10 segundos justos
(MUS / "snaptube" / "download" / "SnapTube Audio" / "Exitin x 2 on(MP3_160K).lrc").write_text(
    "[00:01.00]letra de prueba\n", encoding="utf-8")   # hermano exacto: `Musica.java:195-200`
(MUS / "snaptube" / "download" / "SnapTube Video").mkdir(parents=True, exist_ok=True)
(MUS / "snaptube" / "download" / "SnapTube Video" / "Exitin x 2 on (Slowed).mp4").write_bytes(b"\x00")
(MUS / "snaptube" / "download" / "SnapTube Video" / "otro video.mp4").write_bytes(b"\x00")
(MUS / "sin-etiqueta.ogg").write_bytes(b"OggS\x00\x00")  # sin lector: `dur` y artista vacíos
(MUS / "Dark Rose" / "Otra Cancion(MP3_160K).mp3").write_bytes(b"\xff\xfb\x90\x00solo audio")
mp3(FUERA / "colada.mp3", {"TIT2": "NO DEBE SALIR", "TPE1": "nadie"})
try:
    (MUS / "puerta-falsa.mp3").symlink_to(FUERA / "colada.mp3")
    HAY_ENLACE = True
except OSError:
    HAY_ENLACE = False

(MUS / "Mi ruta.m3u").write_text(
    "#EXTM3U\n#EXTINF:260,Exitin\nsnaptube/download/SnapTube Audio/Exitin x 2 on(MP3_160K).mp3\n"
    "CORT Demo/Tono.wav\n../../afuera/colada.mp3\n"
    f"{MUS / 'CORT Demo' / 'Tono.wav'}\n\n", encoding="utf-8")   # absoluta, dentro: sí vale
(MUS / "Del otro lado.pls").write_text(
    "[playlist]\nNumberOfEntries=3\n"
    "File1=content://com.snaptube.premium.fileprovider/root/storage/emulated/0/a.mp3\n"
    "Title1=De Android\nFile2=%2Fextranjero%2Fb.mp3\nTitle2=Con espacios\n"
    f"File3={FUERA}/colada.mp3\nTitle3=Ruta absoluta que existe pero está fuera\n",
    encoding="utf-8")
(MUS / "roto.mp3").write_bytes(b"ID3" + bytes([4, 0, 0]) + _synch(30 * 1024 * 1024) + b"nada")

# ── el reproductor, de pega: graba en vez de lanzar ───────────────────────────
LANZADOS: list[list[str]] = []
PREGUNTAS: list[str] = []
_MIME = {"respuesta": "org.strawberrymusicplayer.strawberry.desktop", "suena": ""}


class _Proc:
    returncode = 0
    stdout = ""


def _stub_run(cmd, *a, **k):
    PREGUNTAS.append(" ".join(cmd))
    p = _Proc()
    if cmd[0] == "xdg-mime":
        p.stdout = _MIME["respuesta"]
    elif cmd[0] == "playerctl":
        p.stdout = _MIME["suena"]
    return p


def _stub_popen(cmd, *a, **k):
    LANZADOS.append(list(cmd))
    return _Proc()


musica.subprocess = type("S", (), {"run": staticmethod(_stub_run),
                                   "Popen": staticmethod(_stub_popen),
                                   "SubprocessError": Exception})()
musica.platform = type("P", (), {"system": staticmethod(lambda: "Linux")})()

# ── [1] el lector de etiquetas ─────────────────────────────────────────────────
print("\n[0] el traje: esta prueba no escribe ni lee la música ni la casa reales")
espero("la casa de CORT de esta prueba es temporal",
       str(rutas.DATOS).startswith(str(TRAJO)), True)
espero("la raíz de Música también",
       str(sensors.ROOTS["Música"]).startswith(str(TRAJO)), True)
espero("y la otra raíz apunta a un sitio que no existe", sensors.ROOTS["Music"].exists(), False)
espero("musica sólo ve una raíz de música", [n for n, _ in musica.raices()], ["Música"])

print("\n[1] etiquetas ID3 leídas de bytes reales (los cuatro casos que hay en su disco)")
e = musica.etiquetas(MUS / "Dark Rose" / "2 on.mp3")
espero("v2.4 UTF-8: título", e.get("TIT2"), "2 on — tinashe")
espero("v2.4: duración en ms", e.get("TLEN"), "222000")
espero("v2.4: no se cuela el encoder", "TSSE" in e, False)
espero("v2.3 UTF-16 con BOM: artista sin \\ufeff",
       musica.etiquetas(MUS / "Looksmaxing " / "closer.mp3").get("TPE1"), "saturday night")
espero("v2.2 (ids de tres letras)", sorted(musica.etiquetas(MUS / "snaptube" / "v22.mp3")),
       ["TIT2", "TPE1"])
espero("cabecera mentira (30 MiB anunciado) no revienta", musica.etiquetas(MUS / "roto.mp3"), {})
espero("ogg sin lector", musica.etiquetas(MUS / "sin-etiqueta.ogg"), {})
espero("archivo que no existe", musica.etiquetas(MUS / "nadie.mp3"), {})

# ── [2] el barrido del disco ───────────────────────────────────────────────────
print("\n[2] pistas(): lo que hay en el disco, con los campos que se pudieron confirmar")
p = musica.pistas(forzar=True)
por = {x["nombre"]: x for x in p}
espero("pistas encontradas (el enlace fuera NO cuenta)", len(p), 9)
pasa("ninguna ruta sale de Música",
     all(sensors.music_path(x["ruta"]) for x in p),
     " · ".join(x["ruta"] for x in p if not sensors.music_path(x["ruta"])) or "las 8 validan")
pasando = por.get("Exitin x 2 on (Slowed)", {})
espero("título real, no el nombre del archivo con `(MP3_160K)`",
       any(x["nombre"] == "Exitin x 2 on (Slowed)" for x in p), True)
espero("artista de TPE1", pasando.get("artista"), "Newsinko")
espero("álbum de TALB", pasando.get("album"), "Newsinko")
espero("duración real de TLEN", pasando.get("dur"), "4:20")
espero("segundos para LRCLIB", pasando.get("seg"), 260)
espero("estilo de etiqueta cuando existe", pasando.get("genero"), "Electronic")
espero("el mp4 del mismo título se marca como vídeo (la píldora MV de Android)",
       pasando.get("video"), True)
espero("y no se la pone a una canción sin vídeo",
       {x["nombre"]: x["video"] for x in p}["Tono"], False)
espero("el .lrc hermano se marca como letra", pasando.get("letra"), True)
espero("la carpeta se muestra limpia (ella la tiene con espacio al final)",
       por["closer - the chainsmokers"]["carpeta"], "Looksmaxing")
espero("wav medido con stdlib", por["Tono"]["dur"], "0:10")
espero("wav sin etiquetas: artista vacío (no se presta la carpeta)",
       por["Tono"]["artista"], "")
espero("ogg: sin duración inventada", por["sin-etiqueta"]["dur"], "")
espero("sin TCON el estilo queda vacío y lo cubre la carpeta",
       (por["sin-etiqueta"]["genero"], por["sin-etiqueta"]["carpeta"]), ("", ""))
espero("el enlace fuera de Música no se lista", "colada" in " ".join(x["nombre"] for x in p), False)
espero("nombre limpio del archivo cuando no hay etiqueta (el rastro del bajador)",
       por.get("Otra Cancion", {}).get("ruta"), "Música/Dark Rose/Otra Cancion(MP3_160K).mp3")
espero("la ruta que sirve `/api/audio` sigue siendo la de siempre (`Música/…`)",
       all(x["ruta"].startswith("Música/") for x in p), True)

# ── [3] la búsqueda, con la misma media que Android ────────────────────────────
print("\n[3] busca(): la misma comparación que `encaja` (Musica.java:203), plegada")
espero("plegar quita acentos", musica.plegar("Beyoncé  Canción"), "beyonce  cancion")
espero("por artista", [x["nombre"] for x in musica.busca(q="cyberysz")], ["2 on — tinashe"])
espero("escrito sin tilde encuentra lo que está tildeado",
       [x["nombre"] for x in musica.busca(q="cancion rota")], ["Canción Rota"])
espero("por álbum", [x["nombre"] for x in musica.busca(q="Newsinko")], ["Exitin x 2 on (Slowed)"])
espero("por álbum cuando ni el título ni el artista lo dicen",
       [x["nombre"] for x in musica.busca(q="maqueta 2024")], ["Canción Rota"])
espero("por carpeta (lo que hace de estilo)", len(musica.busca(q="snaptube")), 2)
espero("estilo por etiqueta, plegado", {x["nombre"] for x in musica.busca(genero="electronic")},
       {"Exitin x 2 on (Slowed)"})
espero("estilo por carpeta cuando el archivo no trae TCON",
       len(musica.busca(genero="dark rose")), 2)
espero("estilo que no existe da vacío, no todo", musica.busca(genero="reggaeton"), [])
espero("la traducción no se inventa: «electrónica» no es «Electronic»",
       musica.busca(genero="electrónica"), [])
espero("lista por nombre", [x["nombre"] for x in musica.busca(lista="Mi ruta")],
       ["Exitin x 2 on (Slowed)", "Tono"])
espero("lista rota del teléfono no cuela canciones", musica.busca(lista="Del otro lado"), [])
espero("los estilos salen de las dos fuentes que hay",
       {s["fuente"] for s in musica.estilos()}, {"etiqueta", "carpeta"})
espero("y cada nombre con cuántas pistas tiene",
       {s["nombre"]: (s["pistas"], s["fuente"]) for s in musica.estilos()}["Electronic"], (1, "etiqueta"))
espero("una carpeta usada por dos canciones cuenta las dos",
       {s["nombre"]: s["pistas"] for s in musica.estilos() if s["fuente"] == "carpeta"}["Dark Rose"], 2)

# ── [4] playlists ──────────────────────────────────────────────────────────────
print("\n[4] listas(): lo que resuelve en ESTE equipo, contado con honestidad")
L = {x["nombre"]: x for x in musica.listas(forzar=True)}
espero("m3u: 4 líneas, 3 de verdad en este disco (la que apunta afuera no cuenta)",
       (L["Mi ruta"]["pistas"], L["Mi ruta"]["resueltas"]), (4, 3))
espero("pls de SnapTube: 3 escritas, 0 en este disco (aunque el archivo exista fuera)",
       (L["Del otro lado"]["pistas"], L["Del otro lado"]["resueltas"]), (3, 0))
# La pieza de abajo se comprueba sola, sin pasar por el conteo: es la reja que
# decide si una línea del archivo de texto puede convertirse en una canción.
pl = MUS / "Mi ruta.m3u"
espero("_resuelve: relativa dentro de Música",
       musica._resuelve(pl, "CORT Demo/Tono.wav"), "Música/CORT Demo/Tono.wav")
espero("_resuelve: absoluta dentro de Música",
       musica._resuelve(pl, str(MUS / "CORT Demo" / "Tono.wav")), "Música/CORT Demo/Tono.wav")
espero("_resuelve: absoluta que EXISTE pero está fuera, rechazada",
       musica._resuelve(pl, str(FUERA / "colada.mp3")), None)
espero("_resuelve: relativa que sale con `..`, rechazada",
       musica._resuelve(pl, "../../afuera/colada.mp3"), None)
espero("_resuelve: esquema de otro aparato, rechazado",
       musica._resuelve(pl, "content://com.snaptube.premium.fileprovider/x.mp3"), None)
espero("_resuelve: comentario o línea vacía, ignorada",
       (musica._resuelve(pl, "#EXTM3U"), musica._resuelve(pl, "   ")), (None, None))
espero("_resuelve: un vídeo no es una canción de la lista",
       musica._resuelve(pl, "snaptube/download/SnapTube Video/otro video.mp4"), None)
r = musica.pon_lista("Para el gimnasio", ["Música/Dark Rose/2 on.mp3",
                                          "Música/no-existe.mp3"])
espero("guardar una lista deja fuera lo que no existe", (r.get("ok"), r.get("pistas")), (True, 1))
guardada = rutas.DATOS / "listas" / "Para el gimnasio.m3u"
espero("se guarda en la casa de CORT, no en su Música", guardada.exists(), True)
antes = guardada.read_bytes()
r2 = musica.pon_lista("Para el gimnasio", ["Música/Dark Rose/2 on.mp3"])
espero("el mismo nombre NO sobrescribe", (r2.get("ok"), r2.get("existe")), (False, True))
espero("y el archivo viejo queda byte a byte igual", guardada.read_bytes() == antes, True)
espero("nombre con barra no sale de la carpeta",
       musica.pon_lista("../../huida", ["Música/Dark Rose/2 on.mp3"]).get("ok"), True)
pasa("esa lista se escribió dentro de la casa de CORT",
    not (TRAJO / "huida.m3u").exists() and (rutas.DATOS / "listas" / "huida.m3u").exists())
espero("lista vacía no se guarda", musica.pon_lista("vacia", []).get("error"),
       "ninguna canción de esa lista está en Música")
espero("la lista de CORT aparece en el listado", "Para el gimnasio" in
       {x["nombre"] for x in musica.listas(forzar=True)} or "huida" in
       {x["nombre"] for x in musica.listas(forzar=True)}, True)

# ── [5] el reproductor predeterminado ─────────────────────────────────────────
print("\n[5] suena(): el reproductor se nombra con lo que contesta el sistema, y nada se lanza aquí")
espero("nombre del programa real", musica.reproductor_predeterminado(),
       "org.strawberrymusicplayer.strawberry")
espero("sin asociación: cadena vacía, no «predeterminado»",
       (_MIME.update(respuesta=""), musica.reproductor_predeterminado(),
        _MIME.update(respuesta="org.strawberrymusicplayer.strawberry.desktop"))[1], "")
espero("estado sin playerctl", musica.estado_real(), "desconocido")
_MIME["suena"] = "Playing\n"
espero("estado confirmado por playerctl", musica.estado_real(), "reproduciendo")
_MIME["suena"] = "Paused\n"
espero("estado dicho como viene", musica.estado_real(), "paused")
_MIME["suena"] = ""
_MIME["respuesta"] = "org.strawberrymusicplayer.strawberry.desktop"
espero("pista inexistente rechazada", musica.suena("Música/no-está.mp3").get("error"),
       "canción no encontrada en Música")
espero("huida por `..` rechazada", musica.suena("../afuera/colada.mp3").get("ok"), False)
r = musica.suena("Música/Dark Rose/2 on.mp3")
espero("abre con xdg-open y dice el programa", (r.get("ok"), r.get("reproductor")),
       (True, "org.strawberrymusicplayer.strawberry"))
espero("y no promete que suena si el aparato no lo confirma", r.get("estado"), "desconocido")
espero("el comando lanzado es el archivo validado, no una ruta libre",
       LANZADOS[-1][0] == "xdg-open" and str(LANZADOS[-1][1]).startswith(str(MUS)), True)
sin_xdg, sin_mime = shutil.which, musica.reproductor_predeterminado
try:
    shutil.which = lambda n: None                        # equipo sin nada que abra audio
    _MIME["respuesta"] = ""
    esperado = musica.suena("Música/Dark Rose/2 on.mp3")
    espero("sin reproductor: error honesto con sugerencia",
           (esperado.get("ok"), "no hay reproductor" in esperado.get("error", "")),
           (False, True))
finally:
    shutil.which = sin_xdg
    _MIME["respuesta"] = "org.strawberrymusicplayer.strawberry.desktop"
espero("al azar también funciona (frase «pon música»)",
       musica.suena("").get("ok"), True)
espero("y nunca se le pasó una ruta al sistema por fuera de Música",
       all(str(x[1]).startswith(str(MUS)) for x in LANZADOS), True)
print(f"       (comandos grabados: {len(LANZADOS)} · preguntas al sistema: {len(PREGUNTAS)})")

# ── [6] la voz ─────────────────────────────────────────────────────────────────
print("\n[6] las frases de voz: buscar de verdad, y decir lo que hay cuando no")
suenan: list[str] = []
musica.suena_real = musica.suena


def _solo_apunta(rel=""):
    suenan.append(rel)
    t = (musica.pistas(forzar=True) if not rel else
         [x for x in musica.pistas(forzar=True) if x["ruta"] == rel])
    return {"ok": True, "cancion": (t[0]["nombre"] if t else "alguna"),
            "reproductor": "strawberry", "estado": "reproduciendo"} if t else \
        {"ok": False, "error": "canción no encontrada en Música"}


musica.suena = _solo_apunta
LAS_DE_LA_LISTA = {"Música/Dark Rose/2 on.mp3",
                   "Música/snaptube/download/SnapTube Audio/Exitin x 2 on(MP3_160K).mp3",
                   "Música/CORT Demo/Tono.wav"}
Exitin = "Música/snaptube/download/SnapTube Audio/Exitin x 2 on(MP3_160K).mp3"


def ultima():
    return suenan[-1] if suenan else "(no se puso nada)"


suenan.clear()
nombre, frase = actions._one("pon música de tinashe")
espero("«pon música de X» encuentra al artista", (nombre, "2 on" in frase), ("musica", True))
espero("«pon música de X» no se confunde con el estilo", ultima(),
       "Música/Dark Rose/2 on.mp3")
nombre, frase = actions._one("pon la lista Mi ruta")
pasa("«pon la lista Y» sólo puede elegir de esa lista",
     nombre == "musica" and ultima() in LAS_DE_LA_LISTA, ultima())
suenan.clear()
nombre, frase = actions._one("pon música del estilo Electronic")
pasa("«del estilo Z» filtra por la etiqueta del archivo",
     nombre == "musica" and ultima() == Exitin, ultima())
pasa("y la respuesta nombra la canción encontrada", "Exitin" in frase, frase)
espero("la frase suelta NO cae en el filtro de estilo", actions._one("pon música")[1]
       .startswith("Poniendo"), True)
antes = len(suenan)
nombre, frase = actions._one("pon la lista la que no existe")
espero("lista inexistente: no pone nada y dice cuáles hay",
       ("No encontré" in frase, "Mi ruta" in frase, len(suenan) == antes), (True, True, True))
suenan.clear()
nombre, frase = actions._one("reproduce la canción closer")
pasa("«reproduce la canción X»", nombre == "musica" and "closer" in frase, frase)
nombre, frase = actions._one("pon música del estilo reggaeton")
pasa("estilo inexistente: dice los que hay en vez de inventar",
     "No encontré" in frase and "Electronic" in frase, frase)
suenan.clear()
nombre, frase = actions._one("pon música")
espero("la frase suelta sigue poniendo algo al azar", (nombre, suenan), ("musica", [""]))
nombre = actions._one("hazme un café")
pasa("una frase que no es de música NO la atrapa el ejecutor de música",
     nombre is None, repr(nombre))
musica.suena = musica.suena_real

# ── [7] el contrato con la cara ────────────────────────────────────────────────
print("\n[7] el cuerpo de /api/music: los campos viejos siguen ahí para que la cara actual no se rompa")
res = musica.informe()
espero("`canciones` trae nombre/artista/ruta/dur (como antes)",
       all(k in res["canciones"][0] for k in ("nombre", "artista", "ruta", "dur")), True)
espero("y lo nuevo: estilos, listas, total, raíz, reproductor y por qué está vacía",
       all(k in res for k in ("estilos", "listas", "total", "raices", "reproductor", "vacio")),
       True)
espero("cada pista trae además álbum, carpeta, segundos, vídeo y letra",
       all(k in res["canciones"][0] for k in ("album", "carpeta", "seg", "video", "letra")), True)
espero("la raíz que ve la cara es la de siempre", res["raices"], ["Música"])
espero("el total coincide con el barrido", res["total"], len(res["canciones"]))
espero("el reproductor llega a la cara", res["reproductor"],
       "org.strawberrymusicplayer.strawberry")
espero("sin filtro y con canciones, `vacio` está vacío", res["vacio"], "")
espero("con un filtro que no cuela, `vacio` lo dice con palabras",
       musica.informe(q="zzzz")["vacio"], "nada encaja con ese filtro")
guardado = dict(musica._CACHE)                     # el disco de la dueña NO se toca:
musica._CACHE.update(pistas=[], caduca=time.time() + 99,          # sólo se finge el
                     listas=[], lc=time.time() + 99)              # barrido ya hecho
espero("con la Música vacía, `vacio` dice lo otro y `total` es 0",
       (musica.informe()["vacio"], musica.informe()["total"]),
       ("no hay música en las carpetas Música", 0))
musica._CACHE.clear(); musica._CACHE.update(guardado)
espero("`sensors.music_list` es la misma lista (delegación, no copia)",
       sensors.music_list(2)[0]["ruta"], res["canciones"][0]["ruta"])
# El envoltorio FastAPI sólo se puede mirar si el framework está instalado (en el
# equipo de Actions no lo está: corre `python3` pelado). En el portátil de la dueña
# sí, con `.venv`, y ahí se comprueba además que las firmas no cambiaron.
try:
    import main                                            # noqa: E402
except ModuleNotFoundError:
    dice_ok("envoltorio FastAPI", "sin fastapi en este entorno: se comprueba el cuerpo puro")
else:
    espero("el modelo de `/api/play` no cambió de nombre", main.Play().ruta, "")
    espero("`main.music()` es el mismo informe", main.music()["total"], res["total"])
    espero("POST /api/music/lista da 409 si el nombre ya existe",
           main.music_lista(main.Lista(nombre="Para el gimnasio",
                                       rutas=["Música/Dark Rose/2 on.mp3"])).status_code, 409)
    espero("y 200 con un nombre nuevo",
           main.music_lista(main.Lista(nombre="Lista de prueba",
                                       rutas=[Exitin])).status_code, 200)
    espero("`main.play` delega sin cambiar el contrato",
           set(main.play(main.Play(ruta="Música/no-existe.mp3"))) >= {"ok", "error"}, True)

# ── cierre ─────────────────────────────────────────────────────────────────────
shutil.rmtree(TRAJO, ignore_errors=True)
print(f"\n{'TODO CIERTO' if not FALLOS else 'FALLOS: ' + str(len(FALLOS))} · "
      f"{len(FALLOS) and '' or 'comprobaciones en verde'}")
for f in FALLOS:
    print("   ·", f)
sys.exit(1 if FALLOS else 0)
