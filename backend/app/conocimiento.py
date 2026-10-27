"""El conocimiento de CORT: su carpeta de documentos, indexada y buscable sin nube.

Su prompt lo pedía con estos nombres: «la actualización extra le agregaremos lectura de
archivos, que guardaremos en carpeta de conocimiento y a su vez tendremos otra carpeta
llamada `knowledge.py`, cual se encargará de pegar los códigos con nuestra carpeta
conocimiento para que nuestra IA la pueda leer correctamente». Aquí está, con nombre en
español como el resto del núcleo (`conocimiento.py`, no `knowledge.py`), y con una regla
que manda sobre todo el fichero:

  **CORT sólo cita lo que de verdad leyó.** El índice no es una promesa decorativa: cada
  entrada sale de abrir el archivo, tomar sus primeras líneas y medir su fecha. Si la
  carpeta no existe, se dice la ruta exacta que hay que crear. Si la pregunta no está, se
  dice «no está en tus N archivos» en vez de rellenar con lo que el modelo se invente.

Qué NO hace, y por qué está escrito aquí y no en un comentario suelto:

  · **No lee PDF ni Word.** En esta casa el texto a pelo es `.txt`, `.md`, `.log`
    (la misma lista de `sensors.LEE_EXT`, para que «lo que se indexa» y «lo que se puede
    leer» no sean dos verdades distintas). Un `.pdf` aparece en el índice con su motivo de
    estar fuera, y el candado de `sensors` sigue siendo el único que abre la ventana.
  · **No manda nada a la nube ni usa embeddings.** El equipo de la dueña tiene 2 núcleos y
    1,8 GiB: un índice de palabras bien medido responde el 90 % de «busca en mis apuntes»
    y no le come la RAM a Ollama.
  · **No se sale de la raíz.** Se recorre con `os.walk` sobre un `Path` ya resuelto por
    `sensors._resolve`, que es el que conoce las seis raíces permitidas; los enlaces
    simbólicos se ignoran y `../` no llega ni a intentarse.

Uso normal desde la cara (cuando la dueña commitee `main.py`, que es donde vive la ruta):
`estado()` para la placa, `indice()` para la hoja, `responde()` para la charla.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

try:
    from . import sensors                      # núcleo empaquetado
except ImportError:                            # scripts y pruebas sueltas
    import sensors

RAIZ_POR_DEFECTO = "Documentos/conocimiento"
EXT_LEIBLES = set(sensors.LEE_EXT)             # {txt, md, markdown, log}
LIMITE_ARCHIVOS = 300                          # tope duro: 1,8 GiB no dan para más
LIMITE_PROFUNDIDAD = 4                         # conocimiento/<materia>/<tema>/x.md
EXTRACTO_CARACTERES = 400                      # lo que se guarda para poder buscar
PALABRA_MINIMA = 3                             # «la», «el» no puntúan
TTL_CACHE = 300.0                              # segundos; la hoja puede forzar

_CACHE: dict[str, tuple[float, dict]] = {}

# «# Ciclo de la urea», «## Ciclo de la Urea», «**ciclo**» y «ciclo de la urea.»
# tienen que dar el mismo título.
_MD = re.compile(r"^[#>*\-\s]+")
_PUNT = re.compile(r"[.,;:!?$]+$")

def normaliza(texto: str) -> str:
    """Minúsculas, sin tildes, sin signos de puntuación y sin ruido: «Bioquímica»,
    «bioquimica» y «BIOQUÍMICA» son la misma palabra, y «¿urea?» también lo es.

    Es el mismo pliegue que usan `ordenes.js` y `automatiza.js`. Los signos se quitan
    porque si no, la pregunta «¿dónde se forma la urea?» buscaría la palabra `urea?`,
    que no está en ningún título, y CORT diría que no lo sabe cuando sí lo sabe.
    """
    import unicodedata
    s = unicodedata.normalize("NFD", str(texto or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s.lower()).strip()


def titula(texto: str, nombre: str) -> str:
    """Título de un archivo: su primera línea con letras, sin adornos de Markdown.

    Un archivo vacío o hecho sólo de `#` no tiene título, y se queda con el nombre del
    archivo sin extensión — que es un hecho, no una invención. Los `*` de énfasis se
    quitan todos, no sólo los del principio: «**Repaso** de bioquímica» se llama
    «Repaso de bioquímica».
    """
    for linea in str(texto or "").splitlines():
        limpio = _PUNT.sub("", _MD.sub("", linea.strip().replace("*", ""))).strip()
        if len(limpio) >= 3 and any(c.isalpha() for c in limpio):
            return limpio[:90]
    return Path(nombre).stem[:90]


def _sin_raid(ruta: Path) -> bool:
    """True si NO es un enlace simbólico: el índice no sigue salidas de la raíz."""
    try:
        return not ruta.is_symlink()
    except OSError:
        return False


def escanea(raiz: Path) -> dict:
    """Recorre la carpeta y devuelve el índice. No toca la red ni el cerebro.

    Cada entrada: `ruta` (relativa a la raíz, con `/`), `nombre`, `titulo`, `kb`,
    `modificado` (AAAA-MM-DD), `lineas` y `extracto` (las primeras palabras, para poder
    buscar sin reabrir el archivo). Los archivos que no se pueden leer letra a letra
    entran en `fuera` con su motivo, para que la cara lo diga en vez de callarse.
    """
    raiz = Path(raiz)
    if not raiz.exists():
        return {"ok": False, "raiz": str(raiz), "existe": False, "archivos": [],
                "fuera": [], "total": 0, "vaciar": 0,
                "dice": f"no tengo la carpeta de conocimiento: créala en {raiz} "
                        f"y guarda ahí tus notas (.txt o .md)"}
    if not raiz.is_dir():
        return {"ok": False, "raiz": str(raiz), "existe": True, "archivos": [],
                "fuera": [], "total": 0, "vaciar": 0,
                "dice": f"{raiz} no es una carpeta"}

    archivos: list[dict] = []
    fuera: list[dict] = []
    vaciar = 0
    base_len = len(raiz.parts)
    for raiz_dir, dirs, nombres in os.walk(raiz):
        dirs[:] = [d for d in sorted(dirs) if not d.startswith(".") and _sin_raid(Path(raiz_dir) / d)]
        if len(Path(raiz_dir).parts) - base_len >= LIMITE_PROFUNDIDAD:
            dirs[:] = []
        for n in sorted(nombres):
            if n.startswith("."):
                continue
            f = Path(raiz_dir) / n
            if not _sin_raid(f) or not f.is_file():
                continue
            rel = "/".join(f.parts[base_len:])
            ext = f.suffix.lower()
            if ext not in EXT_LEIBLES:
                fuera.append({"ruta": rel, "motivo": f"{ext or 'sin extensión'} no es texto que se pueda leer"})
                continue
            try:
                tam = f.stat().st_size
                if tam > sensors.LEE_MAX_KB * 1024:
                    fuera.append({"ruta": rel, "motivo": f"grande para leerlo aquí ({tam // 1024} KB)"})
                    continue
                crudo = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                fuera.append({"ruta": rel, "motivo": "sin permiso para leerlo"})
                continue
            limpio = crudo.strip()
            if not limpio:
                vaciar += 1                     # vacío es vacío: no cuenta como leído
            cabecera = crudo[:EXTRACTO_CARACTERES]
            archivos.append({
                "ruta": rel,
                "nombre": n,
                "titulo": titula(crudo, n),
                "kb": round(tam / 1024, 1),
                "modificado": time.strftime("%Y-%m-%d", time.localtime(f.stat().st_mtime)),
                "lineas": 0 if not limpio else crudo.count("\n") + 1,
                "extracto": " ".join(cabecera.split()),
            })
            if len(archivos) >= LIMITE_ARCHIVOS:
                fuera.append({"ruta": "…", "motivo": f"se cortó en {LIMITE_ARCHIVOS} archivos"})
                break
        if len(archivos) >= LIMITE_ARCHIVOS:
            break

    dice = (f"leí {len(archivos)} archivo(s) de {raiz.name}"
            + (f", {len(fuera)} sin poder leerse" if fuera else "")
            + (f", {vaciar} vacío(s)" if vaciar else "")) if archivos else \
           f"la carpeta {raiz} está vacía o no tiene textos"
    return {"ok": bool(archivos), "raiz": str(raiz), "existe": True,
            "archivos": archivos, "fuera": fuera, "total": len(archivos),
            "vaciar": vaciar, "dice": dice}


def raiz_resuelta(rel: str = RAIZ_POR_DEFECTO) -> Path:
    """La raíz por dentro del candado de `sensors`, y NUNCA asomándose fuera.

    `sensors._resolve` arma la ruta pero no la limpia, así que el `..` viajaría hasta el
    disco. Aquí se corta antes de tocar nada: la primera parte tiene que ser una de las
    seis raíces permitidas, ninguna parte puede ser `.` o `..`, y la ruta resuelta tiene
    que quedar dentro de esa raíz. Si no, `ValueError` con el motivo en español, que
    `indice` convierte en una respuesta honesta en vez de en un fallo de la cara.
    """
    parts = [p for p in str(rel or "").replace("\\", "/").split("/") if p]
    if not parts or parts[0] not in sensors.ROOTS:
        raise ValueError("el conocimiento tiene que vivir dentro de una de las carpetas "
                         "permitidas (Documentos, Escritorio, Descargas…)")
    if any(p in (".", "..") for p in parts):
        raise ValueError("sin `../`: el índice no se asoma fuera de su raíz")
    raiz = sensors._resolve("/".join(parts)).resolve()
    base = sensors.ROOTS[parts[0]].resolve()
    try:
        raiz.relative_to(base)
    except ValueError:
        raise ValueError("la carpeta de conocimiento se salió de " + str(base))
    return raiz


def indice(rel: str = RAIZ_POR_DEFECTO, *, fuerza: bool = False) -> dict:
    """Índice con caché. `fuerza=True` lo reconstruye (el botón «refrescar» de la hoja).

    Nunca lanza: una raíz prohibida o un `../` devuelven el mismo molde de «no hay
    índice» con su `dice`, porque la cara no tiene forma de pintar una excepción.
    """
    try:
        raiz = raiz_resuelta(rel)
    except ValueError as e:
        return {"ok": False, "raiz": str(rel), "existe": False, "archivos": [],
                "fuera": [], "total": 0, "vaciar": 0, "en_caché": False, "dice": str(e)}
    clave = str(raiz)
    visto = _CACHE.get(clave)
    if visto and not fuerza and (time.time() - visto[0]) < TTL_CACHE:
        return dict(visto[1], en_caché=True)
    dato = escanea(raiz)
    _CACHE[clave] = (time.time(), dato)
    return dict(dato, en_caché=False)


def busca(texto: str, index: dict, *, n: int = 3) -> list[dict]:
    """Qué archivos hablan de `texto`, con su motivo medible y sin inventar nada.

    Puntuación: 3 por palabra en el título, 2 en el nombre, 1 en el extracto. El desempate
    es la fecha más reciente, y si dos archivos tienen la misma gana el orden de ruta —por
    eso la primera pasada ordena por ruta y la segunda, que es estable, sólo ordena por
    puntos y fecha. No es un modelo: son palabras que están o no están, y por eso el
    `motivo` se puede enseñar sin mentir.
    """
    palabras = [p for p in normaliza(texto).split() if len(p) >= PALABRA_MINIMA]
    if not palabras or not index.get("archivos"):
        return []
    marcados = []
    for a in index["archivos"]:
        ti, no, ex = normaliza(a["titulo"]), normaliza(a["nombre"]), normaliza(a["extracto"])
        puntos, porque = 0, []
        for p in palabras:
            g = 0
            if p in ti:
                g += 3
            if p in no:
                g += 2
            if p in ex:
                g += 1
            if g:
                puntos += g
                porque.append(p)
        if puntos:
            m = dict(a)
            m["puntos"] = puntos
            m["motivo"] = "habla de " + ", ".join(porque[:4])
            marcados.append(m)
    marcados.sort(key=lambda a: a["ruta"])
    marcados.sort(key=lambda a: (a["puntos"], a["modificado"]), reverse=True)
    return marcados[:n]


def lee(ruta_rel: str, *, rel: str = RAIZ_POR_DEFECTO, maximo: int = sensors.LEE_MAX_KB * 1024):
    """Contenido de un archivo del índice, por el mismo candado de `sensors.leer_texto`."""
    return sensors.leer_texto(f"{rel}/{ruta_rel}".replace("//", "/"), maximo)


def responde(pregunta: str, *, rel: str = RAIZ_POR_DEFECTO, maximo: int = EXTRACTO_CARACTERES * 2) -> dict:
    """La respuesta con fundamento: busca, abre el mejor archivo y cita lo que leyó.

    Nunca inventa. Si la carpeta no existe, si no hay coincidencia, o si el archivo se
    cortó al leerlo, el `dice` lo cuenta tal cual.
    """
    idx = indice(rel)
    if not idx.get("existe"):
        return {"ok": False, "modo": "sin-carpeta", "dice": idx["dice"], "raiz": idx["raiz"]}
    candidatos = busca(pregunta, idx)
    if not candidatos:
        return {"ok": False, "modo": "no-esta", "dice":
                f"busqué «{pregunta}» en {idx['total']} archivo(s) de {Path(idx['raiz']).name} "
                f"y no está", "total": idx["total"]}
    mejor = candidatos[0]
    dato = lee(mejor["ruta"], rel=rel, maximo=maximo)
    if not dato.get("ok"):
        return {"ok": False, "modo": "no-leyable", "dice":
                f"encontré {mejor['nombre']}, pero no lo pude abrir: {dato.get('error', 'motivo desconocido')}",
                "ruta": mejor["ruta"]}
    texto = dato["texto"] if "texto" in dato else dato.get("contenido", "")
    cortado = len(texto) >= maximo
    return {"ok": True, "modo": "citado", "pregunta": pregunta,
            "ruta": mejor["ruta"], "titulo": mejor["titulo"],
            "modificado": mejor["modificado"], "candidatos": [c["ruta"] for c in candidatos],
            "cita": texto[:maximo],
            "dice": f"en {mejor['titulo']} ({mejor['ruta']}, {mejor['modificado']}) dice: "
                    + texto[:maximo] + ("…" if cortado else "")}


def estado(rel: str = RAIZ_POR_DEFECTO) -> dict:
    """Lo mínimo para la placa: si hay carpeta, cuántos textos, y cuándo se midió."""
    idx = indice(rel)
    return {"ok": bool(idx.get("total")), "raiz": idx["raiz"], "existe": idx.get("existe", False),
            "total": idx.get("total", 0), "midiendo": time.strftime("%H:%M")}
