"""Canal de actualización de CORT (fase U1).

CORT avisa cuando existe una versión nueva y dice cómo traerla. No se autoinstala:
bajar código y ejecutarlo en el equipo de la usuaria es una decisión suya, y un
asistente que se actualiza solo es la puerta de entrada a que lo haga otro.

Todo lo que dice este módulo es medido en el momento: si no hay red, si el repo no
existe todavía o si GitHub contesta otra cosa, se dice con la frase de GitHub y no
se inventa ninguna versión.
"""
import json
import os
import re
import urllib.request
from pathlib import Path

# Los valores de entorno se leen en cada consulta, no al importar: si no, cambiar el
# repo o la versión pedía reiniciar el puente y una prueba nunca atrapaba el defecto.
VERSION = "0.9.0"
REPO = "Sandra2244/CORT"
API = "https://api.github.com"


RAIZ = Path(__file__).resolve().parent.parent


def _git(*args):
    """Lee el git local sin tocar nada. Si no hay git o falla, cadena vacía."""
    try:
        import subprocess
        r = subprocess.run(("git", "-C", str(RAIZ)) + args, capture_output=True, text=True, timeout=4)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def repo_local():
    """El repo se deriva del remoto configurado, no se adivina: adivinarlo mandó la
    primera prueba a buscar etiquetas de otro proyecto."""
    url = _git("remote", "get-url", "origin")
    if not url:
        return ""
    corto = url.split("//")[-1].split(":")[-1]
    partes = corto.replace(".git", "").strip("/").split("/")
    return "/".join(partes[-2:]) if len(partes) >= 2 else ""


def version_local():
    return _git("describe", "--tags", "--abbrev=0")


def config():
    return (os.environ.get("CORT_VERSION") or version_local() or VERSION,
            os.environ.get("CORT_REPO") or repo_local() or REPO,
            os.environ.get("CORT_API_GITHUB", API))

NOMBRE_REPO = re.compile(r"^[\w.-]+/[\w.-]+$")
ETIQUETA = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def _numero(etiqueta):
    m = ETIQUETA.match((etiqueta or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def mas_nueva(local, remota):
    """True sólo si los dos números son válidos y la remota es mayor."""
    a, b = _numero(local), _numero(remota)
    return bool(a and b and b > a)


def _pedir(url):
    req = urllib.request.Request(url, headers={"User-Agent": "CORT",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def consultar():
    """Mira las etiquetas del repo. Devuelve dict con `origen` real o no disponible."""
    version, repo, api = config()
    if not NOMBRE_REPO.match(repo):
        return {"ok": False, "origen": "no disponible",
                "motivo": f"el repositorio configurado no tiene forma válida ({repo})",
                "version_local": version}
    try:
        etiquetas = _pedir(f"{api}/repos/{repo}/tags")
    except Exception as e:
        return {"ok": False, "origen": "no disponible",
                "motivo": f"no se pudo leer {repo}: {type(e).__name__} {e}",
                "version_local": version}
    nombres = [t.get("name", "") for t in etiquetas if isinstance(t, dict)]
    validas = [(n, _numero(n)) for n in nombres]
    validas = [(n, v) for n, v in validas if v]
    if not validas:
        return {"ok": False, "origen": "real", "version_local": version,
                "motivo": f"el repo {repo} existe pero todavía no tiene ninguna etiqueta de versión",
                "etiquetas": nombres[:8]}
    mejor, _ = max(validas, key=lambda par: par[1])
    hay = mas_nueva(version, mejor)
    web = re.sub(r"^https://api\.", "https://", api)   # api.github.com → github.com
    aviso = (f"git fetch --tags y revisa {web}/{repo}/tags — cambiar de versión con "
             f"`git checkout {mejor}` reescribe el "
             f"árbol de trabajo, así que se hace con el proyecto commiteado y decidido por ti"
             if hay else "ya estás en la última etiqueta publicada")
    return {"ok": True, "origen": "real", "version_local": version, "remota": mejor,
            "hay_nueva": hay, "n_etiquetas": len(validas),
            "sin_etiqueta_local": version == VERSION, "como": aviso}


def registrar(r):
    """Deja la última comprobación en disco: el aviso sobrevive al reinicio del puente."""
    ESTADO = Path(os.environ.get("CORT_ACTUALIZA_estado", "/tmp/cort-actualiza.json"))
    try:
        ESTADO.parent.mkdir(parents=True, exist_ok=True)
        ESTADO.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return r


def ultimo():
    ESTADO = Path(os.environ.get("CORT_ACTUALIZA_estado", "/tmp/cort-actualiza.json"))
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except Exception:
        return None
