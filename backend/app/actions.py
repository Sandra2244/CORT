"""Acciones del sistema para CORT — POST /api/command.

La pantalla ya resuelve sola las órdenes que son *de ventana* (organizar,
ocultar, abrir el cerebro…). Aquí va lo que necesita al **sistema operativo**:
apuntar una nota, abrir una carpeta o un archivo, lanzar un sitio de la lista
blanca y reproducir música.

Diseño: una frase puede contener VARIAS órdenes separadas por «y / luego /
después», así que se ejecutan todas y se responde con un resumen. Si alguna
requiere inteligencia (p. ej. «abre mi carpeta de facturas y dime cuánto
gasté»), el texto sobrante se manda al cerebro híbrido.

Seguridad: ninguna acción usa shell; solo las funciones de `sensors`, que ya
validan que la ruta caiga dentro de las raíces permitidas y que la extensión
no sea ejecutable.
"""
from __future__ import annotations

import re

import memory
import sensors

SPLIT = re.compile(r"\s+(?:y\s+|luego\s+|despu[eé]s\s+|tambi[eé]n\s+)", re.I)

RE_NOTA = re.compile(r"^(?:apunta|anota|apunta que|recuerda|takes? note|nota[:\s])\s+(.+)", re.I | re.S)
RE_LANCAR = re.compile(r"^(?:abre|abrir|lanza|lanza|abre\s+la\s+p[aá]gina\s+de|open)\s+"
                       r"(youtube|el\s+navegador|navegador|la\s+navegador)\b[\s\.\!]*$", re.I)
RE_CARPETA = re.compile(r"^(?:abre|muestra|mu[eé]strame|abre\s+la\s+carpeta)\s+"
                        r"(?:la\s+carpeta\s+(?:de\s+)?|los\s+|las\s+|el\s+)?([\wáéíóúñü .\-]+)", re.I)
RE_ARCHIVO = re.compile(r"^(?:abre|abrir|muestra|mu[eé]strame)\s+(?:el\s+archivo\s+|la\s+)?(\S+\.\w{2,5})\b", re.I)
RE_MUSICA = re.compile(r"^(?:reproduce|pon|ponme|toca)\s+(?:m[uú]sica|la\sm[uú]sica|unapo|una\s+canci[oó]n)"
                        r"[\s\.\!]*$|^(?:reproduce|pon|ponme|toca)\s+m[uú]sica", re.I)
RE_YOUTUBE = re.compile(r"youtube", re.I)

# ── modelos locales (Ollama) y optimización del equipo ──────────────────────
RE_MODELO_BAJAR = re.compile(
    r"^(?:descarga|descargar|baja|bajar|instala|instalar)\s+"
    r"(?:el\s+modelo\s+|los\s+modelos?\s+|un\s+modelo\s+)?([A-Za-z][\w.\-/:@]{2,})", re.I)
RE_USAR_MODELO = re.compile(r"^(?:usa|usar|pon(?:e|me)?\s+el|c[aá]mbiate?\s+a\s+el|activa)\s+"
                            r"(?:el\s+)?modelo\s+(\S+)", re.I)
RE_MODELOS_LISTA = re.compile(r"(?:lista|cu[aá]les|mu[eé]strame|enséñame)\s+(?:me\s+)?(?:los\s+)?"
                              r"(?:modelos|ia locales?)\b", re.I)
RE_OLLAMA = re.compile(r"^(enciende|prende|levanta|arranca|apaga|para|det[eé]n|cierra)\s+"
                       r"(?:el\s+)?(?:servidor\s+)?ollama\b", re.I)
RE_LIMPIA = re.compile(r"^(?:limpia|limpiar|borra|borrar|vacía|libera|optimiza)\s+"
                       r"(?:la\s+|el\s+|toda\s+la\s+)?(cach[eé]|cache|ram|memoria)\b"
                       r"|^(?:optimiza|libera)\s+el\s+equipo\b", re.I)
RE_RAM_QUERY = re.compile(r"cu[aá]nta\s+(?:ram|memoria)\b|qu[eé]\s+pesado|\bestado\s+del\s+equipo\b", re.I)

ROOT_NAMES = list(sensors.ROOTS.keys())


def _find_root(word: str) -> str | None:
    """«Documentos», «documentos», «mi carpeta de Documentos» → la clave exacta."""
    w = word.strip().lower()
    for name in ROOT_NAMES:
        if name.lower() == w:
            return name
    for name in ROOT_NAMES:
        if w and (w in name.lower() or name.lower() in w):
            return name
    return None


def run_command(message: str) -> dict:
    """{reply, source, done:[nombre-de-acción]} — lo que espera la pantalla."""
    text = (message or "").strip()
    if not text:
        return {"reply": "¿En qué puedo ayudarte?", "source": "local", "done": []}

    done: list[str] = []
    lines: list[str] = []
    leftovers: list[str] = []

    for chunk in SPLIT.split(text):
        c = chunk.strip(" .,¡!")
        if not c:
            continue
        hit = _one(c)
        if hit is None:
            leftovers.append(chunk.strip())
        else:
            name, msg = hit
            done.append(name)
            if msg:
                lines.append(msg)

    if not done:
        return _brain(text)

    if leftovers:
        extra = " ".join(leftovers)
        reply, source = _brain(extra)[:2]
        lines.append(reply)
    else:
        source = "ejecutor"

    reply = " · ".join(lines) if lines else "Hecho."
    memory.remember("user", text, "accion")
    memory.remember("assistant", reply, source)
    return {"reply": reply, "source": source, "done": done}


def _one(c: str) -> tuple[str, str] | None:
    """Una orden suelta → (nombre, mensaje) o None si no es acción."""
    m = RE_NOTA.match(c)
    if m:
        txt = m.group(1).strip()
        if len(txt) < 2:
            return None
        nid = memory.add_note(txt)
        return "nota", f"Nota #{nid} apuntada: «{txt[:60]}»"

    if RE_LANCAR.match(c) or RE_YOUTUBE.search(c):
        key = "youtube" if RE_YOUTUBE.search(c) else "navegador"
        r = sensors.launch_app(key)
        return "app", (f"Abriendo {key} en tu navegador." if r.get("ok")
                       else f"No pude abrir {key}: {r.get('error', 'sin navegador')}")

    # ── Ollama: encender, listar, descargar, usar, borrar ───────────────────
    m = RE_OLLAMA.match(c)
    if m:
        import models
        encender = m.group(1).lower() in ("enciende", "prende", "levanta", "arranca")
        r = models.arrancar_servidor() if encender else models.detener_servidor()
        return "ollama", (r.get("detalle") or "listo") if r.get("ok") \
            else f"Ollama no respondió: {r.get('error')}"

    if RE_MODELOS_LISTA.search(c):
        import models
        e = models.estado_completo()
        if not e["instalado"]:
            return "modelos", e["aviso"]
        tengo = [x["modelo"] for x in e["modelos"] if x["descargado"]]
        van = [f"{x['modelo']} ≈{x['gb']} GB" for x in e["modelos"] if x["estado"] == "va"]
        return "modelos", (
            f"Ollama {'está encendido' if e['corriendo'] else 'está apagado'} y tu equipo tiene "
            f"{e['ram_equipo']} GB de RAM. Descargados: {', '.join(tengo) if tengo else 'ninguno'}. "
            f"Te caben bien: {', '.join(van) if van else 'ninguno sin cerrar cosas'}."
            " Di «descarga el modelo …» y lo bajo.")

    m = RE_MODELO_BAJAR.match(c)
    if m and _pinta_de_modelo(m.group(1)):
        import models
        nombre = m.group(1).rstrip('.').strip()
        e = models.estado_completo()
        ficha = next((x for x in e["modelos"] if x["modelo"] == nombre), None)
        if ficha and ficha["estado"] == "no cabe":
            return "modelos", (f"{nombre} necesita ~{ficha['ram']} GB y tu equipo tiene "
                               f"{ficha['ram_equipo']} GB: se va a colgar. Prueba "
                               f"{_mejor_para(ficha['ram_equipo'])}.")
        r = models.descargar(nombre)
        return "modelo", (f"Descargando {nombre}. Mira la ventana 10 · Modelos para el avance."
                          if r.get("ok") else f"No pude lanzar la descarga: {r.get('error')}")

    m = RE_USAR_MODELO.match(c)
    if m:
        import models
        r = models.usar(m.group(1))
        return "modelo", (f"Listo: el cerebro local ahora usa {r['modelo']}." if r.get("ok")
                          else f"No pude cambiar el modelo: {r.get('error')}")

    # ── optimización: RAM y caché ───────────────────────────────────────────
    if RE_LIMPIA.match(c):
        import optimize
        i = optimize.informe()
        r = optimize.limpiar("seguro")
        if not r.get("ok"):
            return "limpia", f"No pude limpiar: {r.get('error')}"
        return "limpia", (f"Limpié {len(r['borrado'])} caché(s) y liberé {r['mb_liberados']} MB "
                          f"de disco; la RAM disponible pasó a {i['ram']['disponible_mb']} MB. "
                          f"{r['nota']}.")

    if RE_RAM_QUERY.search(c):
        import optimize
        i = optimize.informe()
        top = ", ".join(f"{p['nombre']} {round(p['mb'])} MB" for p in i["procesos"][:4])
        return "ram", (f"RAM al {i['ram']['usado_pct']} % de {i['ram']['total_gb']} GB "
                       f"(quedan {i['ram']['disponible_mb']} MB libre). Lo que más pesa: {top}. "
                       f"Hay {i['liberable_mb']} MB de caché borrable: di «limpia la caché».")

    m = RE_ARCHIVO.match(c)
    if m:
        rel = m.group(1).strip()
        cand = _guess_file(rel)
        if cand:
            r = sensors.open_path(cand)
            if r.get("ok"):
                return "archivo", f"Abriendo {cand.split('/')[-1]} en su visor."
            return "archivo", f"No pude abrir {cand.split('/')[-1]}: {r.get('error')}"
        return None

    m = RE_CARPETA.match(c)
    if m:
        root = _find_root(m.group(1))
        if root:
            r = sensors.open_dir(root)
            return ("carpeta", f"Abriendo la carpeta {root} en el explorador."
                    if r.get("ok") else f"No pude abrir {root}: {r.get('error')}")
        return None

    if RE_MUSICA.match(c):
        r = sensors.play_external()
        return ("musica", f"Poniendo {r['cancion']} en tu reproductor."
                if r.get("ok") else f"Sin música: {r.get('error')}")

    return None


def _pinta_de_modelo(nombre: str) -> bool:
    """Evita que «baja el volumen» se lea como descarga de modelo: tiene que
    parecer un nombre de Ollama (digit, dos puntos o familia conocida)."""
    n = nombre.strip().lower()
    if any(f in n for f in ("qwen", "llama", "phi", "gemma", "mistral", "deepseek",
                            "codellama", "tinyllama", "llava", "starling")):
        return True
    return bool(re.search(r"[\d:]", n))


def _mejor_para(ram_gb: float) -> str:
    """El modelo del catálogo que mejor le cabe al equipo."""
    import models
    aptos = [f for f in models.CATALOGO if f["ram"] <= ram_gb * 0.6]
    aptos.sort(key=lambda f: -f["ram"])
    return aptos[0]["modelo"] if aptos else "qwen2.5:0.5b"


def _guess_file(nombre: str) -> str | None:
    """Busca `nombre` (o su raíz) dentro de las raíces y devuelve la ruta relativa."""
    needle = nombre.lower().strip()
    stem = re.sub(r"\.\w{2,5}$", "", needle)
    for root_name, root in sensors.ROOTS.items():
        if not root.exists():
            continue
        try:
            for f in root.rglob("*"):
                if not f.is_file():
                    continue
                fn = f.name.lower()
                if fn == needle or stem and (stem in fn or fn.startswith(stem)):
                    if f.suffix.lower() in sensors.OPEN_EXT:
                        return f"{root_name}/{f.relative_to(root)}".replace("\\", "/")
        except (PermissionError, OSError):
            continue
    return None


def _brain(text: str) -> dict:
    import brain
    reply, source = brain.think(text, memory.history())
    memory.remember("user", text)
    memory.remember("assistant", reply, source)
    return {"reply": reply, "source": source, "done": []}
