#!/usr/bin/env python3
"""CORT — manos en los archivos (fase F9).

Por qué existe: el cerebro que propone un plan no puede ser también el que toca el
disco. Un modelo de 0,5 B predice texto; si se le deja mover archivos por su cuenta,
una alucinación se convierte en datos perdidos. Aquí el modelo pide y este módulo
decide, con tres reglas duras:

1. Raíces cerradas. Sólo se opera dentro de las carpetas del usuario que están en
   RAICES (Documentos, Descargas, Escritorio, Música, Imágenes, Videos). Un plan que
   nombre `/`, `../../etc` o la carpeta de otra persona se rechaza con el motivo.
2. No hay verbo borrar. Este archivo no exporta `borrar`, `rm` ni `vaciar`. Si la
   fase de borrado llega, tendrá su propia lista, su propia confirmación y papelera,
   nunca un `shutil.rmtree` prestado.
3. Nada se pisa sin permiso. Si en el destino ya existe algo con ese nombre, la
   operación se detiene y responde `necesita_confirmacion`; con `confirmar=True` se
   guarda la copia vieja al lado con sufijo `-cort-<hora>` en vez de destruirla.

Cada operación se anota en registro-archivos.jsonl y cada respuesta lleva `origen`:
"real" después de releer el disco, "no disponible" si el modelo pidió algo que no
puede hacerse, nunca un éxito inventado.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import unicodedata
from pathlib import Path

CASA = Path(os.environ.get("CORT_HOME", str(Path.home())))
DATOS = Path(os.environ.get("CORT_DATOS", str(CASA / ".local" / "share" / "cort")))
REGISTRO = DATOS / "registro-archivos.jsonl"

# Las únicas Carpetas donde CORT mueve cosas. Se pueden ampliar con CORT_RAICES
# ("Music:Descargas/personal"), pero una raíz absoluta nunca se añade por texto
# suelto de un modelo: la lista base es fija y relativa a la casa del usuario.
RAICES_BASE = ("Documentos", "Descargas", "Escritorio", "Música", "Imágenes", "Videos")

# topes del buscador por nombre: que «proyectos» no implique recorrer todo el disco
MAX_CANDIDATOS = 4000
MAX_NIVEL = 4


def _sin(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def raices() -> dict:
    """Nombre -> Path, sólo las que existen de verdad en este equipo."""
    out = {}
    for nombre in RAICES_BASE + tuple(os.environ.get("CORT_RAICES", "").split(":")):
        nombre = nombre.strip()
        if not nombre:
            continue
        p = Path(nombre).expanduser()
        if not p.is_absolute():
            p = CASA / p
        if p.is_dir():
            out[_sin(nombre) or nombre] = p
    return out


def _dentro_de_raiz(p: Path) -> bool:
    q = p.resolve(strict=False)
    return any(q == r or r in q.parents for r in raices().values())


def _ruta(texto: str) -> Path:
    p = Path(str(texto or "").strip().strip('"').strip("'")).expanduser()
    return p if p.is_absolute() else CASA / p


def buscar(texto: str) -> tuple:
    """De un nombre hablado a una ruta real. Devuelve (Path|None, motivo).

    Primero la ruta tal cual; si no existe, se buscan nombres parecidos dentro de las
    raíces, con acentos ignorados. No se adivina una ruta que no está en el disco:
    «mueve la carpeta proyectos a documentos» sin `proyectos` en ninguna parte debe
    responder «no la encuentro», que es lo que la plantilla nunca hacía.
    """
    if not texto:
        return None, "el plan no trae nombre de archivo ni carpeta"
    directo = _ruta(texto)
    if directo.exists():
        if _dentro_de_raiz(directo):
            return directo, ""
        return None, f"{directo} está fuera de las carpetas que CORT puede tocar"

    diana = _sin(str(texto))
    diana = re.sub(r"^(la|el|las|los|una|un)\s+", "", diana)
    diana = re.sub(r"\s+(carpeta|archivo|carpetas|archivos)$", "", diana)
    candidatos, descartadas = [], 0
    for base in raices().values():
        for nivel, carpetas, archivos in os.walk(base):
            if Path(nivel).relative_to(base).parts and len(Path(nivel).relative_to(base).parts) > MAX_NIVEL:
                carpetas[:] = []
                continue
            carpetas[:] = [c for c in carpetas if not c.startswith(".")]
            for nombre in carpetas + archivos:
                descartadas += 1
                if descartadas > MAX_CANDIDATOS:
                    break
                s = _sin(nombre)
                if s == diana or (len(diana) > 3 and (diana in s or s in diana)):
                    candidatos.append(Path(nivel) / nombre)
            if descartadas > MAX_CANDIDATOS:
                break
        if descartadas > MAX_CANDIDATOS:
            break
    if not candidatos:
        return None, f"no hay nada que se llame «{texto}» en {', '.join(p.name for p in raices().values())}"
    if len(candidatos) > 1:
        # un empate no se resuelve por gusto: se pregunta con las rutas delante
        return None, "hay varias: " + " · ".join(str(c) for c in candidatos[:4])
    return candidatos[0], ""


# ------------------------------------------------------------------ operadores ----
def _nota(verb: str, ok: bool, decir: str, detalle: dict) -> dict:
    try:
        DATOS.mkdir(parents=True, exist_ok=True)
        with open(REGISTRO, "a", encoding="utf-8") as f:
            f.write(json.dumps({"hora": time.strftime("%Y-%m-%dT%H:%M:%S"), "verb": verb,
                                "ok": ok, "decir": decir, "origen": "real" if ok else "no disponible",
                                **detalle}, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return {"ok": ok, "decir": decir, "origen": "real" if ok else "no disponible", "detalle": detalle}


def _destino_listo(origen: Path, destino: Path, confirmar: bool) -> tuple:
    """Nada se pisa sin preguntar; con permiso, lo viejo se conserva al lado."""
    if not destino.exists():
        return destino, ""
    if not confirmar:
        return None, f"ya existe {destino.name} en {destino.parent}; hace falta confirmación"
    guardado = destino.with_name(f"{destino.stem}-cort-{time.strftime('%H%M%S')}{destino.suffix}")
    if destino.is_dir():
        guardado = destino.with_name(f"{destino.name}-cort-{time.strftime('%H%M%S')}")
    shutil.move(str(destino), str(guardado))
    return destino, f"lo que estaba ahí quedó como {guardado.name}"


def listar(carpeta: str) -> dict:
    p, motivo = buscar(carpeta) if not _ruta(carpeta).exists() else (_ruta(carpeta), "")
    if p is None:
        return _nota("listar", False, motivo, {"pedido": carpeta})
    if p.is_file():
        return _nota("listar", True, f"{p.name} es un archivo de {p.stat().st_size // 1024} kB.",
                     {"ruta": str(p), "archivos": [p.name]})
    elementos = sorted([q for q in p.iterdir() if not q.name.startswith(".")], key=lambda q: q.name)
    etiquetas = [f"{q.name}{'/' if q.is_dir() else ''}" for q in elementos]
    decir = (f"{p.name} está vacía." if not etiquetas else
             f"{p.name} tiene {len(etiquetas)}: " + ", ".join(etiquetas[:12]) +
             ("…" if len(etiquetas) > 12 else "."))
    return _nota("listar", True, decir, {"ruta": str(p), "archivos": etiquetas, "total": len(etiquetas)})


def _mover_o_copiar(verb: str, origen: str, destino: str, confirmar: bool, fn) -> dict:
    a, motivo = buscar(origen)
    if a is None:
        return _nota(verb, False, motivo, {"origen": origen})
    b, motivo2 = buscar(destino) if destino else (None, "")
    if b is None and destino:
        # el destino puede no existir todavía: «mueve X a documentos/pileta»
        b = _ruta(destino)
        if not _dentro_de_raiz(b.parent if b.suffix else b):
            return _nota(verb, False, motivo2 or f"{b} cae fuera de tus carpetas", {"destino": destino})
    if b is None:
        return _nota(verb, False, motivo2, {"destino": destino})
    if b.is_file():
        b = b.parent
    final = b / a.name
    final, aviso = _destino_listo(a, final, confirmar)
    if final is None:
        return _nota(verb, False, aviso, {"origen": str(a), "destino": str(b)})
    try:
        fn(str(a), str(final))
    except (OSError, shutil.Error) as e:
        return _nota(verb, False, f"no pude {verb}: {type(e).__name__}", {"error": str(e)[:120]})
    # verificar es releer, no confiar en que el sistema dijo 0
    cayo = final.exists()
    fue = not a.exists() if verb == "mover" else a.exists()
    if cayo and fue:
        decir = f"Hecho: {a.name} está en {b.name}." + (f" {aviso}." if aviso else "")
        return _nota(verb, True, decir, {"origen": str(a), "destino": str(final), "verificado": True})
    return _nota(verb, False, f"moví pero no lo veo en {final}; lo reviso antes de dar por hecho.",
                 {"origen": str(a), "destino": str(final), "verificado": False})


def mover(origen: str, destino: str, confirmar: bool = False) -> dict:
    return _mover_o_copiar("mover", origen, destino, confirmar, shutil.move)


def copiar(origen: str, destino: str, confirmar: bool = False) -> dict:
    return _mover_o_copiar("copiar", origen, destino, confirmar, shutil.copy2)


def crear_carpeta(donde: str, nombre: str = "") -> dict:
    base, motivo = buscar(donde) if donde else (None, "")
    if base is None:
        base = _ruta(donde) if donde else None
    if base is None:
        return _nota("crear_carpeta", False, motivo or "falta dónde crear la carpeta", {"pedido": donde})
    p = (base / nombre) if nombre else base
    if p.name.lower() in ("", "."):
        return _nota("crear_carpeta", False, "la carpeta no tiene nombre", {})
    if not _dentro_de_raiz(p):
        return _nota("crear_carpeta", False, f"{p} cae fuera de tus carpetas", {"ruta": str(p)})
    if p.exists():
        return _nota("crear_carpeta", True, f"{p.name} ya existe en {p.parent.name}.", {"ruta": str(p)})
    try:
        p.mkdir(parents=True)
    except OSError as e:
        return _nota("crear_carpeta", False, f"no pude crear {p.name}: {type(e).__name__}", {})
    return _nota("crear_carpeta", bool(p.is_dir()), f"Creé {p.name} en {p.parent.name}.",
                 {"ruta": str(p), "verificado": p.is_dir()})


def disponibilidad() -> dict:
    r = raices()
    return {"modulo": "cort_archivos", "listo": True, "raices": sorted(p.name for p in r.values()),
            "sin_borrado": True, "registro": str(REGISTRO)}


if __name__ == "__main__":
    import sys
    print(json.dumps(disponibilidad(), ensure_ascii=False, indent=1))
    for arg in sys.argv[1:]:
        print(arg, "->", buscar(arg)[0] or buscar(arg)[1])
