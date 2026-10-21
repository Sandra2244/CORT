"""Letras de canciones desde LRCLIB — API pública, sin cuenta ni clave.

Por qué LRCLIB: es el único buscador de letras que responde sin registro,
sin API key y sin rayar el portátil — justo lo que necesita un equipo de
1,8 GiB de RAM. La respuesta real (medida con `GET /api/search`) es una lista
de objetos con `syncedLyrics` (marcas `[00:13.42]`) y `plainLyrics`.

Costuras del contrato con la cara de JS:
  · caché en memoria de las últimas 40 búsquedas — la misma canción no vuelve
    a pasar por la red ni un byte;
  · si el servidor está saturado (503 u otra caída), se reintenta UNA vez y
    se avisa con `"reintenta": True` para que la pantalla muestre «más tarde»;
  · nada encontrado no es un error del equipo: es un `ok: False` con texto
    humano, sin `reintenta`.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict

UA = "CORT/2.0 (asistente local)"
BASE = "https://lrclib.net/api/search"
CACHE_MAX = 40

# dict ordenado: lo más nuevo al final, y cuando pasan de 40 se tira el viejo
CACHE: "OrderedDict[tuple, dict]" = OrderedDict()


def _pedir(url: str):
    peticion = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(peticion, timeout=6) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def letra(artista: str, titulo: str, duracion: int = 0) -> dict:
    """La letra de «titulo» de «artista», sincronizada si LRCLIB la tiene."""
    artista = (artista or "").strip()
    titulo = (titulo or "").strip()
    busqueda = f"{artista} – {titulo}"
    if not artista or not titulo:
        return {"ok": False, "error": "dime al menos el artista y el título"}
    clave = (artista.lower(), titulo.lower(), int(duracion or 0))
    if clave in CACHE:
        CACHE.move_to_end(clave)
        return dict(CACHE[clave])

    params = {"track_name": titulo, "artist_name": artista}
    if clave[2] > 0:
        params["duration"] = clave[2]        # la duración desambigua versiones
    url = f"{BASE}?{urllib.parse.urlencode(params)}"

    datos = None
    for intento in (1, 2):                   # un reintento, no una terquedad
        try:
            datos = _pedir(url)
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"ok": False, "error": f"no encontré la letra de {busqueda}"}
            if intento == 2:
                return {"ok": False, "error": "el buscador de letras está ocupado "
                                              "ahora mismo", "reintenta": True}
            time.sleep(1.0)
        except Exception:
            if intento == 2:
                return {"ok": False, "error": "el buscador de letras está ocupado "
                                              "ahora mismo", "reintenta": True}
            time.sleep(1.0)

    golpes = datos if isinstance(datos, list) else []
    if not golpes:
        return {"ok": False, "error": f"no encontré la letra de {busqueda}"}
    # la sincronizada vale oro para el karaoke: se prefiere aunque venga más abajo
    elegido = next((g for g in golpes if (g.get("syncedLyrics") or "").strip()),
                   golpes[0])
    resultado = {"ok": True,
                 "sincronizada": elegido.get("syncedLyrics") or "",
                 "plana": elegido.get("plainLyrics") or "",
                 "fuente": "lrclib", "busqueda": busqueda}
    CACHE[clave] = resultado
    while len(CACHE) > CACHE_MAX:
        CACHE.popitem(last=False)
    return dict(resultado)
