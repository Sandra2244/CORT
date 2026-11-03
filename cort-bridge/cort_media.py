#!/usr/bin/env python3
"""CORT — media en el PC (fase F9).

Qué puede hacer hoy y qué no, dicho con nombre y número:

* En esta máquina hay VLC y Strawberry (verificados en /usr/share/applications el
  2026-11-03). Se busca la pista dentro de las carpetas de música del usuario y se
  lanza el reproductor con una lista de argumentos, sin shell.
* `playerctl` NO está instalado aquí: no hay forma de pausar o pasar de pista sin
  volver a lanzar el programa. Lo dice en vez de fingir que obedeció.
* El teléfono es otro mundo. Lark Player no expone una API ni un intent que el
  navegador pueda tocar desde la PWA; eso se hace con MediaStore dentro del APK
  (fase F12), no desde acá. Este módulo no finge conocer la playlist del A16.

CORT_MEDIA_SIMULA=1 prepara todo y no lanza nada: así se mide el buscador sin que
suene música mientras se prueba otra cosa.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import unicodedata
from pathlib import Path

CASA = Path(os.environ.get("CORT_HOME", str(Path.home())))
REPRODUCTORES = ("vlc", "mpv", "strawberry", "paplayer", "pw-play")
MAX_PISTAS = 3000


def _sin(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _raices_musica() -> list[Path]:
    p = CASA / "Música"
    sitios = [p] if p.is_dir() else []
    extra = os.environ.get("CORT_MUSICA", "")
    if extra:
        sitios.append(Path(extra).expanduser())
    return [s for s in sitios if s.is_dir()]


def jugador() -> str | None:
    for nombre in REPRODUCTORES:
        if shutil.which(nombre):
            return nombre
    return None


def listar_pistas() -> list[dict]:
    out = []
    for base in _raices_musica():
        for nivel, carpetas, archivos in os.walk(base):
            carpetas[:] = [c for c in carpetas if not c.startswith(".")]
            for a in archivos:
                q = Path(nivel) / a
                if q.suffix.lower() in (".mp3", ".ogg", ".m4a", ".flac", ".wav", ".opus"):
                    out.append({"pista": q.stem, "album": Path(nivel).name, "ruta": str(q)})
                    if len(out) >= MAX_PISTAS:
                        return out
    return sorted(out, key=lambda d: _sin(d["album"] + " " + d["pista"]))


def buscar_pista(texto: str, playlist: str = "") -> tuple:
    """(ruta, motivo). Primero por nombre de pista; si se nombra una carpeta-playlist,
    se busca dentro de esa carpeta, porque en el PC las playlists son carpetas."""
    pista = _sin(texto or "")
    if not pista:
        return None, "el plan no trae nombre de pista"
    en = listar_pistas()
    if playlist:
        carpeta = _sin(playlist)
        dentro = [d for d in en if carpeta in _sin(d["album"])]
        if not dentro:
            return None, (f"no tengo la carpeta-playlist «{playlist}» en {', '.join(str(s) for s in _raices_musica()) or 'Música'} "
                          f"(en el PC hay {len(en)} pistas; las del teléfono viven en Lark Player y eso es fase F12)")
        en = dentro
    exactas = [d for d in en if _sin(d["pista"]) == pista]
    if exactas:
        return exactas[0], ""
    parciales = [d for d in en if pista in _sin(d["pista"])]
    if len(parciales) == 1:
        return parciales[0], ""
    if len(parciales) > 1:
        return None, "hay varias: " + " · ".join(d["pista"] for d in parciales[:4])
    return None, f"no encuentro «{texto}» entre {len(en)} pistas" + (f" de «{playlist}»" if playlist else "")


def reproducir(texto: str, playlist: str = "") -> dict:
    d, motivo = buscar_pista(texto, playlist)
    if d is None:
        return {"ok": False, "decir": motivo, "origen": "no disponible", "detalle": {"pedido": texto}}
    j = jugador()
    if not j:
        return {"ok": False, "decir": f"encontré {d['pista']} pero no hay reproductor instalado",
                "origen": "no disponible", "detalle": {"ruta": d["ruta"]}}
    if os.environ.get("CORT_MEDIA_SIMULA") == "1":
        return {"ok": True, "decir": f"(simulado) sonaría {d['pista']} en {j}.",
                "origen": "real", "detalle": {"ruta": d["ruta"], "jugador": j, "simulado": True}}
    try:
        subprocess.Popen([j, d["ruta"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError as e:
        return {"ok": False, "decir": f"{j} no arrancó: {type(e).__name__}", "origen": "no disponible",
                "detalle": {"ruta": d["ruta"]}}
    return {"ok": True, "decir": f"Pongo {d['pista']}, de {d['album']}, en {j}.",
            "origen": "real", "detalle": {"ruta": d["ruta"], "jugador": j}}


def control(que: str) -> dict:
    if shutil.which("playerctl"):
        r = subprocess.run(["playerctl", que], capture_output=True, text=True, timeout=6)
        return {"ok": r.returncode == 0, "decir": (r.stdout or r.stderr).strip()[:80] or que,
                "origen": "real", "detalle": {"accion": que}}
    return {"ok": False, "origen": "no disponible",
            "decir": f"no puedo {que}: playerctl no está instalado en este equipo, y relanzar el "
                     f"reproductor cada vez cortaría la canción",
            "detalle": {"accion": que, "faltante": "playerctl"}}


def disponibilidad() -> dict:
    p = listar_pistas()
    return {"modulo": "cort_media", "listo": bool(jugador()), "jugador": jugador(),
            "carpetas": [str(s) for s in _raices_musica()], "pistas": len(p),
            "control": bool(shutil.which("playerctl")),
            "en_telefono": "requiere el APK (F12), no la PWA"}


if __name__ == "__main__":
    print(json.dumps(disponibilidad(), ensure_ascii=False, indent=1))
