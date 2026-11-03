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
# El prefijo se acepta porque las etiquetas de esta línea se llaman cort-vX.Y.Z: en el
# repo de GitHub ya existen v0.1 … v0.17.0 y son de otra base de código, así que
# compartir el número habría hecho que CORT se creyera más vieja o más nueva de lo que es.
ETIQUETA = re.compile(r"^(?:[A-Za-z][\w-]*[-_])?v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def _numero(etiqueta):
    m = ETIQUETA.match((etiqueta or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def _prefijo(etiqueta):
    """El nombre de línea de una etiqueta: «cort-v0.9.0» → «cort-», «v0.17.0» → «»."""
    m = re.match(r"^([A-Za-z][\w-]*[-_])?v?\d", (etiqueta or "").strip())
    return m.group(1) if m and m.group(1) else ""


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
    if not nombres:
        return {"ok": False, "origen": "real", "version_local": version,
                "motivo": f"el repo {repo} existe pero todavía no tiene ninguna etiqueta de versión",
                "etiquetas": nombres[:8]}
    # Sólo se comparan etiquetas de la misma línea: el repo de GitHub guarda v0.1 …
    # v0.17.0 de otra base de código, y anunciar «hay nueva v0.17.0» sobre este árbol
    # habría empujado a la usuaria a cambiar su proyecto por el de otra época.
    linea = _prefijo(version)
    comparables = [n for n in nombres if _prefijo(n) == linea]
    if not comparables:
        return {"ok": False, "origen": "real", "version_local": version, "hay_nueva": False,
                "motivo": (f"el repo {repo} tiene {len(nombres)} etiquetas "
                           f"({', '.join(nombres[:3])}…) pero ninguna de la línea "
                           f"«{linea or 'sin prefijo'}»: son de otra base de código y no "
                           f"son comparables con esta"),
                "etiquetas": nombres[:8]}
    validas = [(n, _numero(n)) for n in comparables]
    validas = [(n, v) for n, v in validas if v]
    if not validas:
        return {"ok": False, "origen": "real", "version_local": version,
                "motivo": f"el repo {repo} tiene etiquetas pero ninguna con número de versión válido",
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
