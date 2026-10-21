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

# ── leer en voz alta: la petición de la dueña («que me lea las notas, el WhatsApp,
#    las tareas o los documentos, como Siri») ────────────────────────────────────
# Una sola entrada: «lee …» seguido de lo que sea. Se resuelve dentro de `_leer`,
# que es la que sabe si habla de notas, de pendientes, de un archivo o del teléfono.
# No se confunde con `RE_CARPETA`/`RE_ARCHIVO`, que exigen «abre|muestra|muéstrame».
RE_LEER = re.compile(r"^(?:lee|leer|l[eé]eme|l[eé]elo|cu[eé]ntame|rec[ií]tame|recita|narra)"
                     r"\s+(?:en\s+voz\s+alta\s+)?(?:los\s+|las\s+|el\s+|la\s+|mis\s+|mi\s+)?"
                     r"(.+)$", re.I | re.S)
RE_PENDIENTE = re.compile(r"^(?:tengo que|hay que|me falta|apunta (?:una )?pendiente|"
                          r"pendiente[:\s]|anota (?:una )?pendiente)\s+(.+)", re.I | re.S)
RE_HECHO = re.compile(r"^(?:ya (?:hice|termin[eé]|acab[eé])|marca(?:me)? como hecha|listo|"
                      r"complet[eé]|he terminado)\s+(?:la\s+(?:tarea|pendiente|cosa)\s+)?#?(\d+)\b",
                      re.I)

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
    # Va ANTES que `RE_NOTA` a propósito: «apunta una pendiente …» lo capturaría
    # primero la nota y se guardaría como texto suelto en vez de como tarea.
    m = RE_PENDIENTE.match(c)
    if m:
        txt = m.group(1).strip(" .,:!")
        if len(txt) < 3:
            return None
        nid = memory.add_task(txt)
        abiertas = len(memory.list_tasks(100))
        return "pendiente", (f"Pendiente #{nid} apuntada: «{txt[:70]}». "
                             f"Llevas {abiertas} por hacer.")

    m = RE_HECHO.match(c)
    if m:
        if memory.finish_task(int(m.group(1))):
            quedan = memory.list_tasks(30)
            return "pendiente", (f"Pendiente #{m.group(1)} marcada como hecha. "
                                 + (f"Quedan {len(quedan)}." if quedan else "Ya no queda ninguna."))
        return "pendiente", f"No tengo abierta la pendiente #{m.group(1)}."

    m = RE_LEER.match(c)
    if m:
        return _leer(m.group(1).strip(" .,:!"))

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


def _leer(objetivo: str) -> tuple[str, str] | None:
    """«lee mis notas / mis tareas / el documento X» → la frase que hay que hablar.

    Devuelve `None` cuando el objetivo no es ninguna de las tres cosas, para que la
    frase siga su camino normal al cerebro («cuéntame un chiste» no es una lectura).
    El texto sale corto y sin adornos porque **se habla entero**: la boca de CORT es
    `speechSynthesis` en el PC y `TextToSpeech` en el teléfono, y ninguna puede
    saltarse un párrafo.
    """
    o = (objetivo or "").strip().lower()
    if not o:
        return None

    if any(k in o for k in ("whatsapp", "mensaje", "aviso", "notificaci", "telegram",
                            "correo", "email")):
        return "leer", ("Los avisos del teléfono los leo desde la app de CORT, no desde el "
                        "PC: ábrela y di «lee mis avisos». Lo que llegó se me queda en la "
                        "cabeza mientras la app esté abierta, y no lo guardo.")

    if any(k in o for k in ("pendient", "tarea", "lista", "hacer")):
        ts = memory.list_tasks(8)
        if not ts:
            return "leer", ("No tengo ninguna pendiente apuntada. Di «tengo que …» y la apunto, "
                            "y «listo 1» cuando la hayas hecho.")
        dicho = ". ".join(f"{n}: {t['texto']}" for n, t in enumerate(ts, 1))
        unidad = "pendiente abierta" if len(ts) == 1 else "pendientes abiertas"
        return "leer", _recorta(f"Tienes {len(ts)} {unidad}. {dicho}.", 620)

    if any(k in o for k in ("nota", "apunte", "apuntes", "recuerd")):
        ns = memory.list_notes(50)
        if not ns:
            return "leer", "Aún no hay notas guardadas. Di «apunta …» y la apunto."
        ult = ns[-6:]
        dicho = ". ".join(f"{n['texto']} ({n['fecha'][-5:]})" for n in ult)
        pref = (f"Tus {len(ult)} notas" if len(ult) > 1 else "Tu única nota") + ": "
        return "leer", _recorta(pref + dicho + ".", 620)

    if "carpeta" in o:
        return None                       # «lee la carpeta X» no es una lectura: es un directorio
    nombre = re.sub(r"^(?:documento|documentos|archivo|fichero|de\s+los?\s+)\s*", "",
                    objetivo.strip(), flags=re.I)
    # Sólo se interpreta como archivo si lo dice (`«lee el documento X»`) o si lleva
    # extensión (`«lee informe.txt»`). Sin eso, «cuéntame un chiste» o «lee los
    # modelos» terminarían en un «no encuentro el archivo» cuando lo que toca es el
    # cerebro. La regla: si no hay candidato claro, `None` y sigue su camino.
    es_archivo = any(k in o for k in ("documento", "archivo", "fichero")) \
        or bool(re.search(r"\.\w{2,5}$", o))
    if not es_archivo or len(nombre) < 2:
        return None
    cand = _guess_file(nombre)
    if not cand:
        return "leer", f"No encuentro «{nombre}» dentro de tus carpetas permitidas."
    r = sensors.leer_texto(cand, 1400)
    if r.get("ok"):
        corte = "" if r["entero"] else " …se corta aquí, que es largo."
        return "leer", (f"«{r['archivo']}», en {r['carpetas']}: {r['texto']}{corte}")
    if r.get("abrir"):
        # Un PDF o un .docx no se puede leer letra a letra con las herramientas que
        # trae este proyecto. **No se abre solo**: nadie espera que pedir una lectura
        # le levante una ventana, así que se dice el camino («abre la factura.pdf»).
        return "leer", (f"{r['error']}. Si quieres verlo, di «abre {r['abrir'].split('/')[-1]}».")
    return "leer", r.get("error", f"{nombre} no lo puedo leer aquí.")


def _recorta(texto: str, tope: int) -> str:
    """Corta por palabra, que una frase partida a media sílaba suena mal hablada."""
    if len(texto) <= tope:
        return texto
    corte = texto[:tope]
    espacio = corte.rfind(" ")
    return (corte[:espacio] if espacio > tope * 0.6 else corte).rstrip(" ,;:.") + "…"


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
