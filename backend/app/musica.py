"""El núcleo de música del PC — la misma disciplina que ya tiene el de Android.

Por qué existe este archivo en vez de seguir estirando `sensors.music_list()`:
esa función devolvía `{nombre, artista, ruta, dur}` con el `artista` sacado del
**nombre de la carpeta** y el `dur` **siempre vacío** (`sensors.py:166-169`), así
que la cara no podía ni filtrar por estilo ni abrir una playlist. El teléfono ya
hace todo eso leyéndoselo al índice (`Musica.java:107-136`: TITLE/ARTIST/GENRE/
ALBUM/DURATION, `encaja()` en `:203-205`); en un PC no hay índice que consultar,
hay **carpetas y etiquetas**. Aquí se lee lo que de verdad hay en el disco.

Medido en el disco de la dueña (2026-10-26, `~/Música` — 282 archivos, 15 mp3,
161 mp4, 23 `.lrc`, 2 `.pls`):

| qué | de dónde sale | ejemplo real |
|---|---|---|
| título | etiqueta ID3v2 `TIT2`, y si no el nombre del archivo | `Exitin x 2 on (Slowed)` |
| artista | `TPE1` (el archivo no lo dice) | `Newsinko` |
| álbum | `TALB` | `Newsinko` |
| **duración** | `TLEN` en **milisegundos** | `260000` → 4:20 |
| estilo | `TCON` si existe; si no, **la primera carpeta** | `Dark Rose`, `snaptube` |
| playlist | `.m3u`/`.m3u8`/`.pls` del árbol | `SnapTube All Musics.pls` |
| tiene vídeo | mismo título plegado en un `.mp4` del árbol (la píldora `MV` de Android) | |
| tiene letra | `.lrc` o `.txt` hermano (`Musica.java:195-200`) | |

Los catorce mp3 bajados con ffmpeg traen `ID3\x04` con `TSSE: Lavf60.3.100`,
`TIT2`/`TPE1`/`TALB` en UTF-16 y `TLEN`; ninguno trae `TCON`, así que en esta
discoteca el **estilo viene de la carpeta** y por eso las dos cosas se exponen
separadas (`generos` y `carpetas`): fingir un género que el archivo no dice
rompería la regla de honestidad de estado.

Reglas duras: sólo stdlib (nada de mutagen ni ffmpeg — el instalador se arma en
Actions con `fastapi/uvicorn/psutil/requests/dotenv`), nunca se sale de las
raíces de música (la validación sigue siendo `sensors.music_path`), no se escribe
en `~/Música` sin que ella lo pida, y **nunca se sobreescribe** una lista: si el
nombre existe, se devuelve el error en vez de destruir la ajena.
"""
from __future__ import annotations

import platform
import random
import re
import shutil
import struct
import subprocess
import time
import unicodedata
from pathlib import Path
from urllib.parse import unquote

import sensors

AUDIO_EXT = sensors.AUDIO_EXT                      # .mp3 .ogg .wav .m4a .flac .opus
VIDEO_EXT = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}
LISTA_EXT = {".m3u", ".m3u8", ".pls"}
NOMBRES = ("Música", "Music")                      # las raíces que se recorren

_TOPE_ETIQUETA = 8 * 1024 * 1024                   # etiqueta de 8 MiB ya no es una etiqueta
_CADUCIDAD = 20.0                                  # s: el árbol se vuelve a mirar solo
_CACHE: dict = {"pistas": None, "caduca": 0.0}


def raices() -> list[tuple[str, Path]]:
    """Las raíces de música que existen, con el nombre con el que las conoce la cara."""
    out = []
    for n in NOMBRES:
        r = sensors.ROOTS.get(n)
        if r and r.exists():
            out.append((n, r))
    return out


def plegar(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar como compara Lark (`Musica.java:plegar`).

    Sin esto «Beyoncé» y `beyonce` son dos mundos distintos, que es justo el error
    que la cara de Android ya no comete desde que se plegaba el filtro.
    """
    sin = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in sin if unicodedata.category(c) != "Mn").lower().strip()


def _synchsafe(b: bytes) -> int:
    return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]


# Lista CERRADA de lo que se saca de la etiqueta. No es tacañería: si se aceptara
# cualquier marco `T`, `TSSE` (el encoder), `TXXX` (comentarios del bajador) o
# `TPE2` (el grupo de álbum) terminarían en la pantalla como si fueran artistas.
CAMPOS = ("TIT2", "TPE1", "TALB", "TCON", "TLEN")
# ID3v2.2 (año 1998, todavía sale en archivos viejos) usa ids de tres letras.
_V22 = {"TT2": "TIT2", "TP1": "TPE1", "TAL": "TALB", "TCO": "TCON", "TLE": "TLEN"}


def etiquetas(ruta: Path) -> dict:
    """Las etiquetas de texto ID3v2.2/2.3/2.4 de un archivo, o `{}` si no las hay.

    Escrito a mano porque stdlib no tiene lector de etiquetas y no se va a añadir
    una dependencia al instalador por esto. Se leen cinco códigos: `TIT2` título,
    `TPE1` artista, `TALB` álbum, `TCON` género y `TLEN` duración en ms — los
    cuatro primeros menos `TCON` son los que se midieron en los mp3 reales de la
    dueña (ninguno trae género).

    No lanza nunca: un archivo truncado, sin permiso o con una cabecera mentira
    devuelve `{}` o lo que se haya leído hasta ahí, que es la verdad del disco.
    """
    try:
        with open(ruta, "rb") as h:
            cab = h.read(10)
            if cab[:3] != b"ID3" or len(cab) < 10:
                return {}
            n = _synchsafe(cab[6:10])
            if n <= 0 or n > _TOPE_ETIQUETA:
                return {}
            cuerpo = h.read(n)
    except OSError:
        return {}

    salida: dict[str, str] = {}
    p = 0
    largo = 6 if cab[3] == 2 else 10              # v2.2 usa ids de 3 letras
    while p + largo <= len(cuerpo):
        id_ = cuerpo[p:p + (3 if largo == 6 else 4)]
        if not re.fullmatch(rb"[A-Za-z0-9]{3,4}", id_):
            break
        id_ = id_.upper().decode("ascii", "replace")
        if largo == 6:
            tam = cuerpo[p + 3] << 16 | cuerpo[p + 4] << 8 | cuerpo[p + 5]
        else:
            tam = struct.unpack(">I", cuerpo[p + 4:p + 8])[0]
            if cab[3] == 4:
                tam = _synchsafe(cuerpo[p + 4:p + 8])   # v2.4 también es synchsafe
        datos = cuerpo[p + largo:p + largo + tam]
        if not datos:
            break
        p += largo + tam
        id_ = _V22.get(id_, id_)                       # v2.2 escribe `TT2`, no `TIT2`
        if id_ not in CAMPOS:                          # lista cerrada: ni TSSE ni imágenes
            continue
        try:
            v = datos[1:].decode({0: "latin-1", 1: "utf-16", 2: "utf-16-be",
                                  3: "utf-8"}[datos[0]], "replace")
        except (IndexError, KeyError):
            v = datos.decode("latin-1", "replace")
        # `utf-16` sin BOM deja el `\ufeff` delante: en los archivos de ella está,
        # y sin quitarlo el artista sale como `\ufeffNewsinko` y nunca encaja.
        v = v.replace("\ufeff", "").strip("\x00").strip()
        if v:
            salida[id_] = v
    return salida


def _mmss(ms: int) -> str:
    if ms <= 0:
        return ""
    s = round(ms / 1000)
    return f"{s // 60}:{s % 60:02d}"


def _segundos_wav(f: Path) -> int:
    """Duración real de un `.wav` con stdlib (`wave`), para no dejar el `dur` vacío.

    Medido: `Música/CORT Demo/Sintetizador Azul.wav` es el único wav del disco. Es
    el único formato que stdlib sabe medir de cabo a rabo; en mp3 la duración ya
    viene en `TLEN`, y en ogg/flac/m4a **no se estima** por tamaño ni bitrate, que
    sería un número inventado en la pantalla.
    """
    import contextlib
    import wave
    with contextlib.suppress(Exception):
        with wave.open(str(f), "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            if frames > 0 and rate > 0:
                return round(frames / rate)
    return 0


def _nombre_listo(rel: Path) -> str:
    """El nombre del archivo sin el rastro del descargador: `(MP3_160K)`, `[Ultra Slowed]`...

    Sólo para el **mostrado** cuando no hay etiqueta: lo que se reproduce es el
    archivo tal cual. Medido: 12 de los 15 mp3 terminan en `(MP3_160K)`.
    """
    s = rel.stem
    s = re.sub(r"\((?:MP3|OGG|M4A|FLAC)[_ ]?\w{0,8}\)\s*$", "", s, flags=re.I)
    s = re.sub(r"[(\[)\](]{2,}", " ", s)           # `(Slowed _ Reverb)` del bajador
    return re.sub(r"\s{2,}", " ", s).strip() or rel.stem


def pistas(forzar: bool = False) -> list[dict]:
    """Toda la música del disco, con artista/álbum/estilo/duración reales.

    Cada pista lleva: `nombre`, `artista`, `album`, `genero`, `carpeta`, `ruta`,
    `dur`, `seg`, `video`, `letra`, `ext`. `ruta` es el mismo texto relativo que
    ya usaba `sensors.music_list` (`Música/…`), para que `/api/audio` y la cara
    vieja sigan valiendo sin tocarlos.

    Cacheado 20 s: recorrer el disco en un portátil de dos núcleos no se hace por
    cada pulsación de tecla, y bajar una canción nueva se ve sola en el siguiente
    barrido.
    """
    ahora = time.time()
    if not forzar and _CACHE["pistas"] is not None and ahora < _CACHE["caduca"]:
        return _CACHE["pistas"]

    titulos_video: set[str] = set()
    tos: list[tuple[str, Path, Path]] = []
    for nombre, raiz in raices():
        for f in sorted(raiz.rglob("*")):
            if not f.is_file():
                continue
            suf = f.suffix.lower()
            if suf in VIDEO_EXT:
                titulos_video.add(plegar(f.stem))
            elif suf in AUDIO_EXT:
                tos.append((nombre, raiz, f))

    salida: list[dict] = []
    for nombre, raiz, f in tos:
        try:
            rel = f.relative_to(raiz)
        except ValueError:
            continue
        tag = etiquetas(f) if suf_con_etiqueta(f.suffix) else {}
        carpeta = rel.parts[0].strip() if len(rel.parts) > 1 else ""
        try:
            seg = int(tag.get("TLEN", "0")) // 1000 or 0
        except ValueError:
            seg = 0
        if not seg and f.suffix.lower() == ".wav":
            seg = _segundos_wav(f)
        ms = int(seg * 1000) if seg else 0
        genero = tag.get("TCON", "")
        genero = re.sub(r"^\(?\d+\)?$", "", genero).strip() if genero else ""
        ruta = f"{nombre}/{rel}".replace("\\", "/")
        if not music_path_ok(ruta):
            # Un enlace simbólico a fuera de Música (o un archivo que se borró en
            # medio del barrido) aparece en el `rglob` pero `/api/audio` no lo va a
            # servir: listarlo sería una fila que falla al pulsarla.
            continue
        lado = f.with_suffix("")                   # `X.lrc` / `X.txt` hermanos
        salida.append({
            "nombre": tag.get("TIT2") or _nombre_listo(rel),
            # Si no hay `TPE1`, el artista se deja **vacío** en vez de prestar el
            # nombre de la carpeta como hacía `sensors.py:166`: la cara siempre
            # tiene `carpeta` para pintar «está en Dark Rose», que es lo que sí
            # se sabe. `—` en la pantalla es mejor mentira que un artista falso.
            "artista": tag.get("TPE1", ""),
            "album": tag.get("TALB", ""),
            "genero": genero,
            "genero_real": bool(genero),
            "carpeta": carpeta,
            "ruta": ruta,
            "dur": _mmss(ms),
            "seg": seg,
            "video": plegar(tag.get("TIT2") or f.stem) in titulos_video,
            "letra": any(lado.with_suffix(x).is_file() for x in (".lrc", ".txt")),
            "ext": f.suffix.lower(),
        })

    _CACHE["pistas"], _CACHE["caduca"] = salida, ahora + _CADUCIDAD
    return salida


def suf_con_etiqueta(suf: str) -> bool:
    """ID3 se lee en mp3; en ogg/flac/m4a las etiquetas viven en otro sitio y aquí
    no se inventa un lector a medias: devuelven etiqueta vacía y la cara muestra
    lo que sí se sabe (la carpeta)."""
    return suf.lower() in {".mp3"}


def busca(q: str = "", genero: str = "", carpeta: str = "", lista: str = "",
          limite: int = 400) -> list[dict]:
    """Filtro con la misma media que usa Android (`encaja`, `Musica.java:203-205`).

    En Android el filtro compara título/artista/género/álbum; aquí se le añade la
    **carpeta**, que en este disco es lo que hace de estilo cuando el archivo no
    trae `TCON`. La lista (`lista=`) no es un filtro de texto: son las rutas que
    salieron del `.m3u`/`.pls`, y si la playlist apunta a URIs de otro aparato
    devuelve vacío — que es la verdad, no una lista vacía fingida.
    """
    todo = pistas()
    if lista:
        # El orden de una playlist es SU orden (el de las líneas del archivo), no el
        # del barrido del disco: si no, «dale a la lista de correr» empezaría por
        # cualquiera.
        orden = {r: i for i, r in enumerate(rutas_de_lista(lista))}
        todo = [t for t in todo if t["ruta"] in orden]
        todo.sort(key=lambda t: orden[t["ruta"]])
    if genero:
        g = plegar(genero)
        # Como `encaja` en Android: cada campo se compara por su cuenta, así que una
        # canción etiquetada sigue apareciendo si se busca la carpeta donde está.
        todo = [t for t in todo if g in plegar(t["genero"]) or g in plegar(t["carpeta"])]
    if carpeta:
        c = plegar(carpeta)
        todo = [t for t in todo if c == plegar(t["carpeta"])]
    t = plegar(q)
    if t:
        todo = [x for x in todo if t in plegar(x["nombre"]) or t in plegar(x["artista"])
                or t in plegar(x["album"]) or t in plegar(x["genero"])
                or t in plegar(x["carpeta"])]
    return todo[:limite]


def estilos() -> list[dict]:
    """Géneros de etiqueta, y debajo las carpetas que hacen de estilo.

    Se devuelven las dos cosas porque en esta discoteca **ningún** mp3 trae `TCON`:
    si la cara pintara sólo «géneros», saldría vacía aunque tenga 15 canciones.
    Cada nombre lleva cuántas pistas tiene, para que el chip pueda decir `Dark Rose 4`.
    """
    cuenta_g: dict[str, int] = {}
    cuenta_c: dict[str, int] = {}
    for t in pistas():
        if t["genero"]:
            cuenta_g[t["genero"]] = cuenta_g.get(t["genero"], 0) + 1
        if t["carpeta"]:
            cuenta_c[t["carpeta"]] = cuenta_c.get(t["carpeta"], 0) + 1
    return [
        {"nombre": n, "pistas": c, "fuente": "etiqueta"}
        for n, c in sorted(cuenta_g.items(), key=lambda x: (-x[1], x[0]))
    ] + [
        {"nombre": n, "pistas": c, "fuente": "carpeta"}
        for n, c in sorted(cuenta_c.items(), key=lambda x: (-x[1], x[0]))
    ]


def _resuelve(pl: Path, texto: str) -> str | None:
    """Convierte una línea de playlist en una `ruta` relativa válida, o `None`.

    Los `.pls` de SnapTube que hay en su disco apuntan a
    `content://com.snaptube.premium.fileprovider/…`: eso es un proveedor de
    Android, no existe aquí, y **no se infla** a ver si casualmente se parece a un
    archivo. Sólo se cuenta lo que resuelve a un audio dentro de las raíces.
    """
    s = unquote(texto.strip())
    if not s or s.startswith("#"):
        return None
    if re.match(r"^[a-z]+://", s, re.I) or s.startswith("magnet:"):
        return None
    p = Path(s)
    candidato = p if p.is_absolute() else pl.parent / p
    try:
        candidato = candidato.resolve()
    except OSError:
        return None
    if candidato.suffix.lower() not in AUDIO_EXT or not candidato.is_file():
        return None
    for nombre, raiz in raices():
        try:
            rel = candidato.relative_to(raiz.resolve())
        except ValueError:
            continue
        return f"{nombre}/{rel}".replace("\\", "/")
    return None


def listas(forzar: bool = False) -> list[dict]:
    """Playlists del árbol y las que guardó CORT, con cuántas pistas de verdad hay.

    `resueltas` es la parte honesta: un `.pls` con 40 líneas que todas apuntan a
    URIs de otro teléfono se muestra como «0 de 40», no como una playlist con 40.
    """
    ahora = time.time()
    if not forzar and _CACHE.get("listas") is not None and ahora < _CACHE.get("lc", 0):
        return _CACHE["listas"]
    salida: list[dict] = []
    vistos: set[str] = set()
    for nombre, raiz in raices():
        for f in sorted(raiz.rglob("*")):
            if not f.is_file() or f.suffix.lower() not in LISTA_EXT:
                continue
            datos = _lee_lista(f)
            if datos is None:
                continue
            resueltas = [r for r in (x["ruta"] for x in datos if x.get("ruta"))
                         if r and music_path_ok(r)]
            salida.append({"nombre": f.stem, "origen": "disco",
                           "ruta": f"{nombre}/{f.relative_to(raiz)}".replace("\\", "/"),
                           "pistas": len(datos), "resueltas": len(resueltas)})
            vistos.add(plegar(f.stem))
    for f in sorted(_casa_cort().glob("*.m3u")):
        datos = _lee_lista(f) or []
        resueltas = [r for r in (x["ruta"] for x in datos if x.get("ruta"))
                     if r and music_path_ok(r)]
        salida.append({"nombre": f.stem, "origen": "cort", "ruta": f.name,
                       "pistas": len(datos), "resueltas": len(resueltas),
                       "guardada": True})
        vistos.add(plegar(f.stem))
    _CACHE["listas"], _CACHE["lc"] = salida, ahora + _CADUCIDAD
    return salida


def music_path_ok(rel: str) -> bool:
    """`True` sólo si la ruta relativa vive de verdad dentro de Música (valida sensors)."""
    return sensors.music_path(rel) is not None


def _casa_cort() -> Path:
    import rutas
    d = rutas.DATOS / "listas"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lee_lista(f: Path) -> list[dict] | None:
    """lee m3u/m3u8/pls con stdlib. `None` si el archivo no se puede abrir."""
    try:
        txt = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    itens: list[dict] = []
    ultimo_titulo = ""
    en_pls = f.suffix.lower() == ".pls"
    claves: dict[str, dict] = {}
    for linea in txt.splitlines():
        s = linea.strip()
        if not s:
            continue
        if s.lower().startswith("[playlist]") or s.lower().startswith("numberofentries"):
            en_pls = True
            continue
        if en_pls and "=" in s:
            k, v = s.split("=", 1)
            k, n = k.strip(), re.sub(r"\D", "", k)
            if k.lower().startswith("title") and n:
                claves.setdefault(n, {})["titulo"] = v.strip()
            elif k.lower().startswith("file") and n:
                i = claves.setdefault(n, {})
                i["ruta"] = _resuelve(f, v)
                i.setdefault("titulo", "")
            continue
        if s.startswith("#EXTINF"):
            ultimo_titulo = s.split(",", 1)[1].strip() if "," in s else ""
            continue
        if s.startswith("#"):
            continue
        itens.append({"titulo": ultimo_titulo, "ruta": _resuelve(f, s)})
        ultimo_titulo = ""
    if en_pls and claves:
        for n in sorted(claves, key=lambda x: int(x or 0)):
            i = claves[n]
            itens.append({"titulo": i.get("titulo", ""), "ruta": i.get("ruta")})
    return itens


def rutas_de_lista(nombre: str) -> list[str]:
    for L in listas():
        if plegar(L["nombre"]) == plegar(nombre):
            datos = _lee_lista(_fisico(L)) or []
            return [x["ruta"] for x in datos if x.get("ruta") and music_path_ok(x["ruta"])]
    return []


def _fisico(L: dict) -> Path:
    """El archivo de la lista: en las del disco, dentro de la raíz; en las de CORT, en su casa."""
    if L.get("origen") == "cort":
        return _casa_cort() / L["ruta"]
    for nombre, raiz in raices():
        if L["ruta"].startswith(nombre + "/"):
            return raiz / L["ruta"][len(nombre) + 1:]
    return Path(L["ruta"])


def pon_lista(nombre: str, rutas: list[str]) -> dict:
    """Guarda una playlist de CORT en `~/.cort/listas/<nombre>.m3u`.

    Se guarda en la carpeta personal y **no** en `~/Música` por dos motivos: el
    instalador no debe pisarle nunca sus listas, y `rutas.py` ya explica que los
    datos de la dueña viven fuera del programa. Y si el nombre ya existe, se
    devuelve el error sin tocar nada — nunca se sobrescribe.
    """
    nombre = re.sub(r"[/\\\x00-\x1f]", "", str(nombre or "")).strip().strip(".")[:60]
    if not nombre:
        return {"ok": False, "error": "la lista necesita un nombre"}
    buenas = [r for r in rutas if r and music_path_ok(r)]
    if not buenas:
        return {"ok": False, "error": "ninguna canción de esa lista está en Música"}
    destino = _casa_cort() / f"{nombre}.m3u"
    if destino.exists():
        return {"ok": False, "error": f"ya existe una lista llamada {nombre}",
                "existe": True}
    try:
        destino.write_text("#EXTM3U\n" + "\n".join(buenas) + "\n",
                           encoding="utf-8")
    except OSError as e:
        return {"ok": False, "error": f"no se pudo guardar: {type(e).__name__}"}
    _CACHE["listas"] = None
    return {"ok": True, "nombre": nombre, "pistas": len(buenas),
            "donde": str(destino)}


def informe(q: str = "", genero: str = "", carpeta: str = "", lista: str = "",
            limite: int = 400, refrescar: bool = False) -> dict:
    """El cuerpo exacto que devuelve `GET /api/music`, armado fuera de FastAPI.

    Vive aquí y no dentro de `main.py` por una razón práctica: el equipo de pruebas
    de GitHub Actions corre `python3` pelado, sin `fastapi` instalado, y aún así
    tiene que poder comprobar el contrato con la cara. `main.music()` es una línea.
    """
    todas = pistas(forzar=refrescar)
    canciones = (busca(q=q, genero=genero, carpeta=carpeta, lista=lista, limite=limite)
                 if (q or genero or carpeta or lista) else todas[:limite])
    return {
        "canciones": canciones,
        "estilos": estilos(),
        "listas": listas(forzar=refrescar),
        "total": len(todas),
        "raices": [n for n, _ in raices()],
        "reproductor": reproductor_predeterminado(),
        "vacio": "" if canciones else ("no hay música en las carpetas Música"
                                       if not todas else "nada encaja con ese filtro"),
    }


def reproductor_predeterminado(tipo: str = "audio/mpeg") -> str:
    """Qué programa responde hoy por esa clase de archivo en ESTE equipo.

    Es la pregunta honesta antes de prometer música: `xdg-mime query default`
    dice el `.desktop` del asociado. Medido en el portátil de la dueña:
    `org.strawberrymusicplayer.strawberry.desktop` para `audio/mpeg` y
    `audio/x-wav`. Si no hay asociación, se dice `""` y la cara lo avisa en vez
    de abrir un navegador con un archivo dentro.
    """
    s = platform.system()
    if s == "Windows":
        return "asociación de Windows"
    if s == "Darwin":
        return "QuickTime (open)"
    try:
        r = subprocess.run(["xdg-mime", "query", "default", tipo],
                           capture_output=True, text=True, timeout=4)
        d = (r.stdout or "").strip()
        if d:
            return d.replace(".desktop", "")
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def estado_real() -> str:
    """«reproduciendo» sólo si el sistema lo confirma; si no, «desconocido».

    `playerctl` es el único camino estándar de preguntar al reproductor qué está
    haciendo sin inventarse nada. Si no está instalado, CORT **no** dice que suena:
    dice `desconocido`, que es lo que sabe.
    """
    try:
        r = subprocess.run(["playerctl", "status"], capture_output=True,
                           text=True, timeout=2)
        if r.returncode == 0 and "Playing" in (r.stdout or ""):
            return "reproduciendo"
        if r.returncode == 0 and (r.stdout or "").strip():
            return r.stdout.strip().lower()
    except (OSError, subprocess.SubprocessError):
        pass
    return "desconocido"


def suena(rel: str = "") -> dict:
    """Abre una canción con el reproductor predeterminado y cuenta lo que pasó.

    Sale de aquí con `reproductor` (el programa real, no «predeterminado» genérico
    de `sensors.py:219`) y con `estado`, que sólo dice `reproduciendo` si el
    aparato lo confirmó. La cara pinta exactamente esos dos campos.
    """
    if rel:
        f = sensors.music_path(rel)
        if not f:
            return {"ok": False, "error": "canción no encontrada en Música"}
    else:
        s = pistas()
        if not s:
            return {"ok": False, "error": "no hay música en las carpetas Música"}
        f = sensors.music_path(random.choice(s)["ruta"])
        if not f:
            return {"ok": False, "error": "la lista de canciones está vieja"}
    programa = reproductor_predeterminado()
    if not programa and platform.system() not in ("Windows", "Darwin"):
        import shutil
        if not shutil.which("xdg-open"):
            return {"ok": False,
                    "error": "no hay reproductor predeterminado para audio en este equipo",
                    "sugerencia": "asócialo en Ajustes → Aplicaciones predeterminadas"}
    try:
        if platform.system() == "Windows":
            import os
            os.startfile(str(f))  # noqa: S606 — ruta ya validada por music_path
        else:
            subprocess.Popen(["xdg-open" if platform.system() == "Linux" else "open",
                              str(f)])
    except (OSError, ValueError) as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "cancion": f.stem, "ruta": rel or "",
            "reproductor": programa or "xdg-open", "estado": estado_real()}
