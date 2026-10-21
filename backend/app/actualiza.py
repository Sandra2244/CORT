"""Mira si hay un CORT nuevo en GitHub y prepara la reparación del escritorio.

Dos verbos, dos riesgos:
  · `comprobar()` es de lectura: una petición a la API pública de Releases
    (sin clave) y la comparación de versiones. Barato, siempre disponible.
  · `aplicar()` es de escritura: aquí manda `scripts/actualiza.sh`, que trabaja
    SOLO dentro de `~/Aplicaciones/` y `~/.cort/actualiza/`. La memoria, las
    notas y las claves de `~/.cort/` no se tocan jamás — eso lo aprendió mal
    la dueña cuando el instalador le barría la llave de Groq.

Regla de RAM: un instalador de más de 100 MB NO se descarga dentro de una
respuesta HTTP (congelaría el portátil); se marca `"pendiente": True` y el
script, corriendo fuera del backend, lo baja con `curl` en un rato tranquilo.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from pathlib import Path

import rutas

REPO = "Sandra2244/CORT"
UA = "CORT/2.0 (asistente local)"
RAM_MAX_MB = 100                              # más grande, no entra en una petición
DESKTOP = (".appimage", ".deb", ".exe")       # los instaladores de SU PC
PASOS = "bash scripts/actualiza.sh"

REPO_RAIZ = Path(__file__).resolve().parents[2]


def _obtener(url: str, timeout: int):
    peticion = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(peticion, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def _version_instalada() -> str:
    """Qué CORT es este: primero la constante de `main.py`; si algún día no
    está, el tag de git del repo; y si tampoco hay git, «desconocida»."""
    try:
        texto = (Path(__file__).resolve().parent / "main.py").read_text(encoding="utf-8")
        m = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', texto, re.M)
        if m:
            return m.group(1)
    except OSError:
        pass
    try:
        r = subprocess.run(["git", "describe", "--tags"], cwd=str(REPO_RAIZ),
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "desconocida"


def _limpia(v: str) -> str:
    """`v0.2.12-demo` → `0.2.12`: sin la v ni sufijos, para poder comparar."""
    return re.sub(r"^v", "", (v or "").strip().lower()).split("-", 1)[0]


def _mas_nueva(ultima: str, instalada: str) -> bool:
    if _limpia(instalada) in ("", "desconocida") or not _limpia(ultima):
        return True
    def partes(v: str):
        try:
            return tuple(int(x) for x in _limpia(v).split("."))
        except ValueError:
            return None
    a, b = partes(ultima), partes(instalada)
    if a and b:
        return a > b
    return _limpia(ultima) != _limpia(instalada)


def _release_ultima() -> dict:
    return _obtener(f"https://api.github.com/repos/{REPO}/releases/latest", 8)


def comprobar() -> dict:
    """La llamada de `GET /api/update`: qué tengo, qué hay, qué dice la Release."""
    try:
        r = _release_ultima()
    except Exception as e:
        return {"ok": False,
                "error": f"no pude mirar en GitHub ({type(e).__name__}): "
                         "revisa la conexión y vuelve a intentarlo"}
    instalada = _version_instalada()
    ultima = r.get("tag_name") or ""
    notas = (r.get("body") or "").strip()
    if len(notas) > 600:
        notas = notas[:600].rstrip() + " …"
    enlaces = [{"nombre": a.get("name") or "",
                "url": a.get("browser_download_url") or "",
                "bytes": a.get("size") or 0} for a in r.get("assets", [])]
    return {"ok": True, "instalada": instalada, "ultima": ultima,
            "hay_actualizacion": _mas_nueva(ultima, instalada),
            "notas": notas, "enlaces": enlaces,
            "publicada": r.get("published_at") or ""}


def aplicar(nombre_asset: str = "") -> dict:
    """Prepara la reparación del escritorio (o avisa de que el APK no se arregla así)."""
    try:
        r = _release_ultima()
    except Exception as e:
        return {"ok": False,
                "error": f"no pude mirar en GitHub ({type(e).__name__}): "
                         "revisa la conexión y vuelve a intentarlo"}
    assets = r.get("assets", [])
    nombre = (nombre_asset or "").strip().lower()
    if nombre:
        elegido = next((a for a in assets if nombre in (a.get("name") or "").lower()), None)
        if not elegido:
            return {"ok": False,
                    "error": f"en la Release no hay nada que se llame «{nombre_asset}»"}
    else:
        elegido = next((a for a in assets
                        if (a.get("name") or "").lower().endswith(DESKTOP)), None)
        if not elegido:
            return {"ok": False, "error": "la Release no trae instalador de escritorio"}
    url = elegido.get("browser_download_url") or ""
    nom = elegido.get("name") or Path(url).name

    if nom.lower().endswith(".apk"):
        # Android no deja que una app se reemplace a sí misma desde dentro:
        # la única salida honesta es darle el enlace del APK nuevo.
        return {"ok": False, "apk": True,
                "aviso": "en el teléfono Android no se deja que una app se "
                         "reemplace a sí misma desde dentro: te llevo al APK nuevo",
                "url": url}
    if not nom.lower().endswith(DESKTOP):
        return {"ok": False,
                "error": f"«{nom}» no es un instalador de escritorio que sepa poner"}

    if int(elegido.get("size") or 0) > RAM_MAX_MB * 1024 * 1024:
        # pesado: que lo baje el script, fuera de esta petición, a su ritmo
        return {"ok": True, "pendiente": True, "asset": nom, "url": url,
                "pasos": PASOS + "   (el instalador pesa más de 100 MB: "
                                 "no lo descargo dentro de una petición)"}

    destino = rutas.DATOS / "actualiza"        # ~/.cort/actualiza: lo único que
    try:                                       # sí se escribe aquí
        destino.mkdir(parents=True, exist_ok=True)
        archivo = _desocupar(destino / nom)
        peticion = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(peticion, timeout=60) as cuerpo, \
                open(archivo, "wb") as f:
            while True:
                trozo = cuerpo.read(1024 * 1024)   # de megabyte en megabyte:
                if not trozo:                      # 1,8 GiB de RAM no aguantan
                    break                          # el fichero entero de golpe
                f.write(trozo)
    except Exception as e:
        return {"ok": False, "hecho": False, "url": url,
                "error": f"la descarga falló ({type(e).__name__}): "
                         f"lanza el script a mano: {PASOS}"}
    script = REPO_RAIZ / "scripts" / "actualiza.sh"
    if script.is_file():
        try:
            script.chmod(0o755)
        except OSError:
            pass
    return {"ok": True, "descargado": str(archivo), "hecho": script.is_file(),
            "pasos": PASOS}


def _desocupar(destino: Path) -> Path:
    """No se sobrescribe ni un .deb viejo: si existe, sufijo ` (2)`."""
    if not destino.exists():
        return destino
    n = 2
    while True:
        candidato = destino.parent / f"{destino.stem} ({n}){destino.suffix}"
        if not candidato.exists():
            return candidato
        n += 1
