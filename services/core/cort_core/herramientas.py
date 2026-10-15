"""Las herramientas del asistente: una lista cerrada, con argumentos validados.

Es lo que convierte a CORT de un chat en un mayordomo: poner una alarma, anotar
un recordatorio, abrir YouTube, buscar algo en Spotify, abrir la calculadora.

**Regla 6 de `AGENTS.md`, hecha lista.** Aquí no hay ninguna vía para ejecutar un
comando que alguien escribió. Cada herramienta:

* se llama por un nombre de **esta** tabla (`HERRAMIENTAS`); un nombre que no esté
  se rechaza, lo escriba la usuaria o lo proponga el modelo;
* valida sus argumentos con tipos y largos antes de hacer nada;
* construye lo que abre desde listas cerradas (apps, sitios, carpetas) o desde
  direcciones de **hosts fijos** con la consulta pasada por `quote`: el modelo
  nunca aporta una URL, ni un ejecutable, ni una ruta;
* abre sin shell (`plataforma.abrir`).

Quien propone puede ser la usuaria, con frases en español (`entender`, sin
modelo, sin internet), o el modelo en la nube, con un objeto JSON
(`extraer_llamada`). **Las dos rutas desembocan en `validar` + `ejecutar`**: no
hay una puerta lateral para la que se haya olvidado la validación.

Lo que dice `ejecutar` es lo que **hizo**, no lo que el modelo prometió: «abrí
Spotify con la búsqueda…» y no «pongo la canción». Una herramienta que no puede
afirmar el resultado (no se lee el volumen de Windows, no se sabe si la ventana
apareció) lo dice con esas palabras.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable
from urllib.parse import quote, quote_plus

from . import actions, plataforma, tiempo
from .agenda import Agenda, MAX_TEXTO

#: Largo máximo de una consulta de búsqueda.
MAX_CONSULTA = 120
#: Hasta dónde se programa una alarma o un evento: un año.
HORIZONTE = timedelta(days=366)

# -- listas cerradas -------------------------------------------------------------

#: Programas de Windows. El valor es lo que se le pasa a `os.startfile`: un
#: ejecutable registrado en el sistema (`App Paths`) o un esquema `algo:`. Si el
#: programa no está instalado, Windows lo dice y aquí se cuenta tal cual.
APPS_WIN = {
    "calculadora": ("calc", "la calculadora"),
    "bloc de notas": ("notepad", "el bloc de notas"),
    "paint": ("mspaint", "Paint"),
    "explorador": ("explorer", "el explorador de archivos"),
    "edge": ("msedge", "Microsoft Edge"),
    "chrome": ("chrome", "Google Chrome"),
    "firefox": ("firefox", "Firefox"),
    "configuracion": ("ms-settings:", "la configuración"),
    "administrador de tareas": ("taskmgr", "el administrador de tareas"),
    "word": ("winword", "Word"),
    "excel": ("excel", "Excel"),
    "powerpoint": ("powerpnt", "PowerPoint"),
    "outlook": ("outlook", "Outlook"),
    "spotify": ("spotify:", "Spotify"),
    "whatsapp": ("whatsapp:", "WhatsApp"),
    "discord": ("discord:", "Discord"),
    "steam": ("steam:", "Steam"),
    "teams": ("msteams:", "Teams"),
    "camara": ("microsoft.windows.camera:", "la cámara"),
    "terminal": ("wt", "la terminal"),
    "visual studio code": ("code", "Visual Studio Code"),
    "grabadora": ("ms-call-recording:", "la grabadora"),
}
#: Cómo la gente nombra cada app, sin tildes ni artículo.
_ALIAS_APPS = {
    "calculadora": "calculadora", "calc": "calculadora",
    "bloc de notas": "bloc de notas", "notas": "bloc de notas", "notepad": "bloc de notas",
    "paint": "paint", "pintura": "paint",
    "explorador": "explorador", "explorador de archivos": "explorador", "archivos": "explorador",
    "gestor de archivos": "explorador", "mis archivos": "explorador",
    "edge": "edge", "microsoft edge": "edge", "navegador": "edge",
    "chrome": "chrome", "google chrome": "chrome",
    "firefox": "firefox",
    "configuracion": "configuracion", "ajustes": "configuracion",
    "administrador de tareas": "administrador de tareas", "task manager": "administrador de tareas",
    "word": "word", "excel": "excel", "powerpoint": "powerpoint", "power point": "powerpoint",
    "outlook": "outlook", "spotify": "spotify", "whatsapp": "whatsapp", "discord": "discord",
    "steam": "steam", "teams": "teams", "camara": "camara",
    "terminal": "terminal", "consola": "terminal",
    "visual studio code": "visual studio code", "vscode": "visual studio code", "vs code": "visual studio code",
    "grabadora": "grabadora",
}

#: Sitios web: direcciones fijas.
SITIOS = {
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "youtube": "https://www.youtube.com",
    "maps": "https://www.google.com/maps",
    "drive": "https://drive.google.com",
    "calendario": "https://calendar.google.com",
    "whatsapp web": "https://web.whatsapp.com",
    "netflix": "https://www.netflix.com",
    "github": "https://github.com",
    "spotify web": "https://open.spotify.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com",
    "traductor": "https://translate.google.com",
    "wikipedia": "https://es.wikipedia.org",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "linkedin": "https://www.linkedin.com",
    "amazon": "https://www.amazon.com",
    "mercado libre": "https://www.mercadolibre.com.co",
}
_ALIAS_SITIOS = {
    "google": "google", "gmail": "gmail", "correo": "gmail", "mi correo": "gmail",
    "youtube": "youtube", "you tube": "youtube",
    "maps": "maps", "mapas": "maps", "google maps": "maps",
    "drive": "drive", "google drive": "drive",
    "calendario": "calendario", "google calendar": "calendario", "mi calendario": "calendario",
    "whatsapp web": "whatsapp web", "netflix": "netflix", "github": "github",
    "claude": "claude", "gemini": "gemini", "traductor": "traductor",
    "wikipedia": "wikipedia", "instagram": "instagram", "facebook": "facebook",
    "linkedin": "linkedin", "amazon": "amazon", "mercado libre": "mercado libre",
}

#: Carpetas de la usuaria, relativas a su carpeta personal.
CARPETAS = {
    "descargas": ("Downloads", "las descargas"),
    "documentos": ("Documents", "los documentos"),
    "escritorio": ("Desktop", "el escritorio"),
    "imagenes": ("Pictures", "las imágenes"),
    "musica": ("Music", "la música"),
    "videos": ("Videos", "los videos"),
}
_ALIAS_CARPETAS = {"descargas": "descargas", "documentos": "documentos", "escritorio": "escritorio",
                   "imagenes": "imagenes", "fotos": "imagenes", "musica": "musica", "videos": "videos"}


# -- contexto inyectable ---------------------------------------------------------

@dataclass
class Contexto:
    """Todo lo que las herramientas tocan del mundo, a mano para sustituirlo."""
    agenda: Agenda
    ahora: Callable[[], datetime] = field(default=datetime.now)
    abrir: Callable[[str], None] = plataforma.abrir
    pulsar: Callable[..., None] = plataforma.pulsar
    recorte: Callable[[], None] = plataforma.recorte
    bloquear: Callable[[], None] = plataforma.bloquear
    windows: bool = field(default_factory=plataforma.es_windows)
    home: Path = field(default_factory=Path.home)
    notas: Path | None = None
    #: Dónde suena la música sin decir app: `spotify` (por defecto) o `youtube`.
    musica: str = "spotify"
    #: La misma llave que `actions.py`: `CORT_SYSTEM_ACTIONS=0` apaga todo lo que toca
    #: el sistema (abrir, teclas, bloquear). La agenda, las notas y el cronómetro no.
    acciones: Callable[[], bool] = actions.enabled

    def ruta_notas(self) -> Path:
        return self.notas or (self.agenda.ruta.parent / "notas.txt")


@dataclass
class Resultado:
    ok: bool
    texto: str
    #: Órdenes para el servidor, que es quien tiene el estado por conexión
    #: (`{"cronometro": "iniciar"}`) o debe despertar al vigilante de la agenda.
    extra: dict = field(default_factory=dict)


# -- texto y direcciones ---------------------------------------------------------

def limpiar(s: object, largo: int = MAX_CONSULTA) -> str:
    """Una sola línea, sin caracteres de control, recortada. Vacía si no hay nada."""
    t = "".join(c if c.isprintable() else " " for c in str(s))
    return " ".join(t.split())[:largo].strip()


def _clave(s: str) -> str:
    """«La Calculadora » → «calculadora»: minúscula, sin tildes ni artículo."""
    t = tiempo.sin_tildes(limpiar(s, 80).lower())
    t = re.sub(r"^(?:(?:la|el|los|las|mi|mis|un|una|tu|su)\s+)+", "", t)
    t = re.sub(r"\s+(?:por favor|porfa|ahora|ya)$", "", t)
    return t.strip(" .,!¡?¿")


def url_youtube(q: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote_plus(q)


def url_google(q: str) -> str:
    return "https://www.google.com/search?q=" + quote_plus(q)


def url_maps(q: str) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(q)


def uri_spotify(q: str) -> str:
    return "spotify:search:" + quote(q, safe="")


def url_spotify_web(q: str) -> str:
    return "https://open.spotify.com/search/" + quote(q, safe="")


def url_calendario(titulo: str, inicio: datetime, minutos: int, detalles: str = "") -> str:
    """Un evento de Google Calendar con los datos ya puestos: se abre en el
    navegador y la usuaria le da a guardar. (Crearlo sin que lo vea pediría su
    cuenta de Google y un permiso OAuth: otra decisión, no un detalle.)"""
    fin = inicio + timedelta(minutes=minutos)
    f = "%Y%m%dT%H%M%S"
    url = ("https://calendar.google.com/calendar/render?action=TEMPLATE"
           f"&text={quote_plus(titulo)}&dates={inicio:{f}}/{fin:{f}}")
    if detalles:
        url += f"&details={quote_plus(detalles)}"
    return url


def _fecha(valor: object) -> datetime | None:
    """«2026-10-13 07:00» o ISO con T. `None` si no es una fecha."""
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(valor).strip().replace("/", "-")).replace(tzinfo=None)
    except ValueError:
        return None


# -- el registro ------------------------------------------------------------------
# nombre -> (para el modelo, argumentos). Los tipos: "txt" (obligatorio), "txt?"
# (opcional), ("enum", [...]), "int?" (opcional).
HERRAMIENTAS: dict[str, tuple[str, dict]] = {
    "abrir_app": ("Abre una aplicación, carpeta o sitio web conocido (calculadora, bloc de notas, Word, "
                  "Spotify, WhatsApp, descargas, gmail...)", {"nombre": "txt"}),
    "youtube": ("Busca en YouTube (sin consulta, abre YouTube)", {"consulta": "txt?"}),
    "spotify": ("Busca música en Spotify (sin consulta, abre Spotify)", {"consulta": "txt?"}),
    "buscar_web": ("Busca algo en Google", {"consulta": "txt"}),
    "mapa": ("Busca un lugar o ruta en Google Maps", {"consulta": "txt"}),
    "multimedia": ("Controla la música o el video que suena", {"orden": ("enum", ["play_pausa", "siguiente", "anterior"])}),
    "volumen": ("Sube, baja o silencia el volumen", {"orden": ("enum", ["subir", "bajar", "silenciar"]), "pasos": "int?"}),
    "alarma": ("Pone una alarma que suena a esa hora", {"cuando": "txt", "texto": "txt?"}),
    "recordatorio": ("Avisa a esa hora con un mensaje", {"cuando": "txt", "texto": "txt"}),
    "evento_calendario": ("Prepara un evento en Google Calendar", {"titulo": "txt", "inicio": "txt", "duracion_min": "int?", "detalles": "txt?"}),
    "cronometro": ("Cronómetro que cuenta hacia arriba", {"orden": ("enum", ["iniciar", "parar", "reiniciar"])}),
    "nota": ("Guarda una nota rápida", {"texto": "txt"}),
    "leer_notas": ("Lee las últimas notas guardadas", {}),
    "agenda_listar": ("Dice qué alarmas y recordatorios hay pendientes", {}),
    "agenda_cancelar": ("Cancela alarmas o recordatorios", {"tipo": ("enum", ["alarma", "recordatorio", "todo"]), "todas": "int?"}),
    "hora": ("Dice qué hora es", {}),
    "fecha": ("Dice qué día y fecha es hoy", {}),
    "captura": ("Abre el recorte de pantalla", {}),
    "bloquear_pc": ("Bloquea la sesión de Windows", {}),
}


#: Lo que sale de CORT hacia el sistema: abre programas y páginas, pulsa teclas,
#: bloquea. Pasa por la llave `CORT_SYSTEM_ACTIONS`. Lo demás sólo lee o escribe
#: en `data/` (agenda, notas) o cuenta tiempo.
TOCAN_EL_SISTEMA = frozenset({"abrir_app", "youtube", "spotify", "buscar_web", "mapa", "multimedia",
                              "volumen", "evento_calendario", "captura", "bloquear_pc"})


def instrucciones() -> str:
    """El párrafo que se le suma al modelo en la nube para que pueda proponer."""
    lineas = []
    for nombre, (desc, args) in HERRAMIENTAS.items():
        a = ", ".join(f'"{k}"' + ("?" if (v == "txt?" or v == "int?") else "") for k, v in args.items())
        extra = ""
        for k, v in args.items():
            if isinstance(v, tuple):
                extra += f" {k} ∈ {{{', '.join(v[1])}}}."
        lineas.append(f"- {nombre}({a}): {desc}.{extra}")
    return (
        "\n\nHERRAMIENTAS. Si la usuaria te pide una ACCIÓN que puedas hacer con una de estas "
        "herramientas, responde ÚNICAMENTE con un objeto JSON en una línea, sin texto antes ni "
        'después y sin markdown: {"herramienta": "nombre", "args": {...}}. Las fechas y horas van en '
        'hora local como "AAAA-MM-DD HH:MM". Si no pide una acción, responde con texto normal. '
        "No inventes herramientas ni argumentos; si lo pedido no está en la lista, dilo con sinceridad. "
        "Herramientas:\n" + "\n".join(lineas)
    )


def validar(llamada: object) -> tuple[dict | None, str]:
    """(llamada normalizada, "") o (None, motivo). Es el único filtro: lo que
    sale de aquí es lo único que `ejecutar` acepta."""
    if not isinstance(llamada, dict):
        return None, "la llamada no era un objeto"
    nombre = llamada.get("herramienta")
    if not isinstance(nombre, str) or nombre not in HERRAMIENTAS:
        return None, f"no tengo la herramienta «{limpiar(nombre, 40)}»"
    args = llamada.get("args", {})
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return None, "los argumentos no eran un objeto"
    esquema = HERRAMIENTAS[nombre][1]
    limpio: dict = {}
    for k, tipo in esquema.items():
        v = args.get(k)
        vacio = v is None or (isinstance(v, str) and not v.strip())
        if tipo in ("txt?", "int?") and vacio:
            continue
        if isinstance(tipo, tuple):
            if not isinstance(v, str) or v not in tipo[1]:
                return None, f"«{k}» debe ser una de: {', '.join(tipo[1])}"
            limpio[k] = v
        elif tipo in ("txt", "txt?"):
            if vacio or not isinstance(v, (str, int, float)):
                return None, f"falta «{k}»"
            limpio[k] = limpiar(v, MAX_TEXTO if k in ("texto", "detalles", "titulo") else MAX_CONSULTA)
            if not limpio[k]:
                return None, f"falta «{k}»"
        elif tipo == "int?":
            try:
                limpio[k] = int(v)
            except (TypeError, ValueError):
                return None, f"«{k}» debe ser un número"
    return {"herramienta": nombre, "args": limpio}, ""


def extraer_llamada(respuesta: str) -> dict | None:
    """Si el modelo respondió con una llamada JSON, la saca; si no, `None` y la
    respuesta se muestra como texto. Tolera ```json y texto alrededor, porque
    los modelos lo ponen aunque se les pida que no."""
    llamadas = extraer_llamadas(respuesta)
    return llamadas[0] if llamadas else None


def extraer_llamadas(respuesta: str) -> list[dict]:
    """Todas las llamadas JSON de una respuesta, en el orden en que aparecen.

    `extraer_llamada` se quedó corta para el bucle del agente: un modelo que
    planea puede devolver dos o tres objetos en un mismo turno, y ejecutar
    solamente el primero era perder pasos sin decirlo. Cada objeto sale **crudo**:
    la validación sigue siendo obligatoria antes de ejecutar, aquí no se afloja
    nada —`extraer_*` es un localizador de texto, no una puerta—.

    Un detalle que importa con dos o más objetos: un JSON anidado también casa
    por su llave interior, así que se salta todo lo que caiga dentro de un
    objeto ya decodificado. Sin eso, `{"a": {"herramienta": …}}` devolvería dos
    llamadas donde la segunda es un pedazo de la primera.
    """
    if not isinstance(respuesta, str) or "herramienta" not in respuesta:
        return []
    dec = json.JSONDecoder()
    found: list[dict] = []
    consumido = -1
    for m in re.finditer(r"\{", respuesta):
        if m.start() <= consumido:
            continue
        try:
            obj, end = dec.raw_decode(respuesta[m.start():])
        except ValueError:
            continue
        consumido = m.start() + end
        if isinstance(obj, dict) and "herramienta" in obj:
            found.append(obj)
    return found


# -- ejecutar ---------------------------------------------------------------------

def _no_win(que: str) -> Resultado:
    return Resultado(False, f"{que} sólo está disponible en Windows por ahora")


def _abrir(ctx: Contexto, destino: str, dicho: str) -> Resultado:
    try:
        ctx.abrir(destino)
    except FileNotFoundError:
        return Resultado(False, f"no encontré {dicho} en este equipo")
    except OSError as err:
        return Resultado(False, f"no pude abrir {dicho}: {getattr(err, 'strerror', None) or err}")
    return Resultado(True, f"Abriendo {dicho}.")


def _resolver_app(ctx: Contexto, nombre: str) -> Resultado:
    k = _clave(nombre)
    if k in _ALIAS_APPS:
        app = _ALIAS_APPS[k]
        if not ctx.windows:
            return _no_win(f"abrir {APPS_WIN[app][1]}")
        destino, dicho = APPS_WIN[app]
        return _abrir(ctx, destino, dicho)
    if k in _ALIAS_CARPETAS:
        sub, dicho = CARPETAS[_ALIAS_CARPETAS[k]]
        return _abrir(ctx, str(ctx.home / sub), dicho)
    if k in _ALIAS_SITIOS:
        return _abrir(ctx, SITIOS[_ALIAS_SITIOS[k]], k if k in SITIOS else _ALIAS_SITIOS[k])
    return Resultado(False, f"no tengo «{limpiar(nombre, 40)}» en mi lista de aplicaciones; "
                            "puedo abrir las que figuran en ajustes → ayuda")


def _cuando(ctx: Contexto, valor: str) -> tuple[datetime | None, str]:
    d = _fecha(valor)
    if d is None:
        return None, "no entendí la fecha y la hora"
    ahora = ctx.ahora().replace(tzinfo=None)
    if d < ahora - timedelta(seconds=60):
        return None, f"{tiempo.cuando_texto(d, ahora)} ya pasó"
    if d > ahora + HORIZONTE:
        return None, "eso queda a más de un año; no lo programo"
    return d, ""


def ejecutar(llamada: dict, ctx: Contexto) -> Resultado:
    """Ejecuta una llamada ya **validada**. Devuelve lo que se hizo, no lo prometido."""
    llamada, motivo = validar(llamada)
    if llamada is None:
        return Resultado(False, motivo)
    n, a = llamada["herramienta"], llamada["args"]
    ahora = ctx.ahora().replace(tzinfo=None)
    if n in TOCAN_EL_SISTEMA and not ctx.acciones():
        return Resultado(False, "las acciones del sistema están apagadas (CORT_SYSTEM_ACTIONS=0 en el .env)")

    if n == "abrir_app":
        return _resolver_app(ctx, a["nombre"])

    if n == "youtube":
        q = a.get("consulta")
        if not q:
            return _abrir(ctx, SITIOS["youtube"], "YouTube")
        r = _abrir(ctx, url_youtube(q), "YouTube")
        return Resultado(r.ok, f"Busqué «{q}» en YouTube; elige el video que quieras." if r.ok else r.texto)

    if n == "spotify":
        q = a.get("consulta")
        if not q:
            if ctx.windows:
                r = _abrir(ctx, "spotify:", "Spotify")
                if r.ok:
                    return r
            return _abrir(ctx, SITIOS["spotify web"], "Spotify en el navegador")
        if ctx.windows:
            try:
                ctx.abrir(uri_spotify(q))
                return Resultado(True, f"Abrí Spotify con la búsqueda «{q}». Pulsa reproducir: "
                                       "no puedo darle play desde fuera sin enlazar tu cuenta.")
            except OSError:
                pass  # sin la app, al navegador
        r = _abrir(ctx, url_spotify_web(q), "Spotify en el navegador")
        return Resultado(r.ok, f"Busqué «{q}» en Spotify (navegador); pulsa reproducir." if r.ok else r.texto)

    if n == "buscar_web":
        r = _abrir(ctx, url_google(a["consulta"]), "Google")
        return Resultado(r.ok, f"Busqué «{a['consulta']}» en Google." if r.ok else r.texto)

    if n == "mapa":
        r = _abrir(ctx, url_maps(a["consulta"]), "Google Maps")
        return Resultado(r.ok, f"Busqué «{a['consulta']}» en Google Maps." if r.ok else r.texto)

    if n == "multimedia":
        if not ctx.windows:
            return _no_win("controlar la reproducción")
        etiqueta = {"play_pausa": "play/pausa", "siguiente": "siguiente pista", "anterior": "pista anterior"}[a["orden"]]
        try:
            ctx.pulsar(a["orden"])
        except OSError as err:
            return Resultado(False, f"no pude enviar la tecla: {err}")
        # Se afirma la tecla, no el efecto: Windows no dice si alguien la escuchó.
        return Resultado(True, f"Envié la tecla de {etiqueta}. (No puedo comprobar que el reproductor respondiera.)")

    if n == "volumen":
        if not ctx.windows:
            return _no_win("el volumen")
        orden = a["orden"]
        pasos = max(1, min(a.get("pasos", 5), 25))
        tecla = {"subir": "subir_volumen", "bajar": "bajar_volumen", "silenciar": "silenciar"}[orden]
        try:
            ctx.pulsar(tecla, 1 if orden == "silenciar" else pasos)
        except OSError as err:
            return Resultado(False, f"no pude tocar el volumen: {err}")
        if orden == "silenciar":
            return Resultado(True, "Silencio alternado. (Windows no me dice el nivel.)")
        return Resultado(True, f"Volumen {'subido' if orden == 'subir' else 'bajado'} "
                               f"unos {pasos * 2} %. (Windows no me dice el nivel exacto.)")

    if n in ("alarma", "recordatorio"):
        d, err = _cuando(ctx, a["cuando"])
        if d is None:
            return Resultado(False, err)
        texto = a.get("texto", "")
        try:
            item = ctx.agenda.agregar(n, d, texto)
        except ValueError as e:
            return Resultado(False, str(e))
        cuando = tiempo.cuando_texto(d, ahora)
        if n == "alarma":
            dicho = f"Alarma puesta para {cuando}." + (f" «{texto}»" if texto else "")
        else:
            dicho = f"Recordatorio para {cuando}: {texto}."
        return Resultado(True, dicho + " (Suena si Viernes está abierta a esa hora; si no, te aviso al abrirla.)",
                         {"agenda": item["id"]})

    if n == "evento_calendario":
        d, err = _cuando(ctx, a["inicio"])
        if d is None:
            return Resultado(False, err)
        minutos = max(5, min(a.get("duracion_min", 60), 1440))
        r = _abrir(ctx, url_calendario(a["titulo"], d, minutos, a.get("detalles", "")), "Google Calendar")
        if not r.ok:
            return r
        return Resultado(True, f"Preparé «{a['titulo']}» para {tiempo.cuando_texto(d, ahora)} en Google Calendar. "
                               "Revísalo y pulsa Guardar en la página que se abrió.")

    if n == "cronometro":
        orden = a["orden"]
        dicho = {"iniciar": "Cronómetro en marcha.", "parar": "Cronómetro detenido.",
                 "reiniciar": "Cronómetro reiniciado."}[orden]
        return Resultado(True, dicho, {"cronometro": orden})

    if n == "nota":
        ruta = ctx.ruta_notas()
        try:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            with ruta.open("a", encoding="utf-8") as f:
                f.write(f"{ahora:%Y-%m-%d %H:%M}  {a['texto']}\n")
        except OSError as err:
            return Resultado(False, f"no pude guardar la nota: {getattr(err, 'strerror', None) or err}")
        return Resultado(True, f"Anotado: {a['texto']}")

    if n == "leer_notas":
        try:
            lineas = [l.rstrip("\n") for l in ctx.ruta_notas().read_text(encoding="utf-8").splitlines() if l.strip()]
        except OSError:
            lineas = []
        if not lineas:
            return Resultado(True, "No tienes notas guardadas.")
        return Resultado(True, "Tus últimas notas: " + " | ".join(l[17:].strip() or l for l in lineas[-5:]))

    if n == "agenda_listar":
        pend = ctx.agenda.pendientes()
        if not pend:
            return Resultado(True, "No tienes alarmas ni recordatorios pendientes.")
        partes = []
        for i in pend[:8]:
            d = datetime.fromisoformat(i["cuando"])
            partes.append(f"{'alarma' if i['tipo'] == 'alarma' else 'recordatorio'} "
                          f"{tiempo.cuando_texto(d, ahora)}" + (f" ({i['texto']})" if i["texto"] else ""))
        mas = f" y {len(pend) - 8} más" if len(pend) > 8 else ""
        return Resultado(True, f"Tienes {len(pend)} pendiente{'s' if len(pend) != 1 else ''}: " + "; ".join(partes) + mas + ".")

    if n == "agenda_cancelar":
        tipo = None if a["tipo"] == "todo" else a["tipo"]
        pend = [i for i in ctx.agenda.pendientes() if tipo is None or i["tipo"] == tipo]
        if not pend:
            return Resultado(True, "No había nada que cancelar.")
        if a.get("todas"):
            quitados = ctx.agenda.cancelar(tipo)
            return Resultado(True, f"Cancelé {quitados} pendiente{'s' if quitados != 1 else ''}.", {"agenda": 0})
        # Sin «todas»: sólo el más próximo, que es lo que casi siempre se quiere.
        proximo = pend[0]
        ctx.agenda.cancelar_id(proximo["id"])
        d = datetime.fromisoformat(proximo["cuando"])
        return Resultado(True, f"Cancelé {proximo['tipo']} {tiempo.cuando_texto(d, ahora)}"
                               + (f" ({proximo['texto']})" if proximo["texto"] else "") + ".", {"agenda": 0})

    if n == "hora":
        h12 = ahora.hour % 12 or 12
        return Resultado(True, f"{'Es la' if h12 == 1 else 'Son las'} {tiempo.hora_12(ahora)}")

    if n == "fecha":
        return Resultado(True, f"Hoy es {tiempo.DIAS[ahora.weekday()]} {ahora.day} de "
                               f"{tiempo.MESES[ahora.month - 1]} de {ahora.year}.")

    if n == "captura":
        if not ctx.windows:
            return _no_win("el recorte de pantalla")
        try:
            ctx.recorte()
        except OSError as err:
            return Resultado(False, f"no pude abrir el recorte: {err}")
        return Resultado(True, "Abrí el recorte de pantalla; elige la zona.")

    if n == "bloquear_pc":
        if not ctx.windows:
            return _no_win("bloquear la sesión")
        try:
            ctx.bloquear()
        except OSError as err:
            return Resultado(False, f"no pude bloquear: {err}")
        return Resultado(True, "Bloqueando la sesión.")

    return Resultado(False, f"la herramienta «{n}» no está implementada")  # pragma: no cover


def etiqueta(llamada: dict) -> str:
    """El paso en palabras para el resumen de un plan."""
    n = llamada.get("herramienta", "")
    a = llamada.get("args", {})
    return {
        "abrir_app": f"abrir {a.get('nombre', '')}", "youtube": "buscar en YouTube",
        "spotify": "buscar en Spotify", "buscar_web": "buscar en Google", "mapa": "buscar en Maps",
        "multimedia": "controlar la reproducción", "volumen": "ajustar el volumen",
        "alarma": "poner la alarma", "recordatorio": "poner el recordatorio",
        "evento_calendario": "preparar el evento", "cronometro": "el cronómetro",
        "nota": "anotar", "captura": "el recorte de pantalla",
    }.get(n, n)


# -- entender frases en español (sin modelo) ---------------------------------------

_CORTESIA = re.compile(
    r"^\s*(?:(?:ok|okey|okay|oye|hey|hola)\s+)?(?:viernes\b[\s,:.!-]*)?"
    r"(?:(?:por favor|porfa)[\s,]*)?"
    r"(?:(?:me\s+)?(?:puedes|podr[ií]as|podr[ií]a|quiero que|necesito que|quisiera que|te pido que)\s+)?",
    re.I,
)


def _sin_cortesia(texto: str) -> str:
    t = _CORTESIA.sub("", texto.strip())
    t = re.sub(r"[\s,]*(?:por favor|porfa|gracias)[\s.!]*$", "", t, flags=re.I)
    return t.strip()


def _call(_herramienta: str, /, **args) -> dict:
    return {"herramienta": _herramienta, "args": {k: v for k, v in args.items() if v not in (None, "")}}


def _resto_suelto(consulta: str | None) -> bool:
    """Una consulta que empieza por «y», «luego», «después»… es lo que sobra de otra
    orden que no se entendió («abre youtube y cuéntame un chiste»): buscarla tal
    cual sería hacer una búsqueda absurda. Mejor no entender y dejarlo al modelo."""
    return bool(consulta) and bool(re.match(r"(?:y|e|luego|despu[eé]s|entonces|adem[aá]s)\b", consulta, re.I))


def _fecha_llamada(d: datetime) -> str:
    return d.strftime("%Y-%m-%d %H:%M")


def _entender_uno(texto: str, ctx: Contexto, trozo: bool = False) -> dict | None:
    """Una frase → una llamada, o `None`. El orden de las preguntas es una decisión:
    lo más específico primero («cancela la alarma» antes que «alarma»).

    `trozo=True`: la frase es un pedazo de un mensaje más largo. Las búsquedas
    (YouTube, Spotify) exigen entonces un verbo al principio: «Residente en
    Spotify» no es una orden aparte, es la segunda mitad de «pon música de Calle
    13 y Residente en Spotify», y partirla ahí buscaría dos veces."""
    t = _sin_cortesia(texto)
    if not t:
        return None
    ahora = ctx.ahora().replace(tzinfo=None)
    con_verbo = bool(re.match(
        r"(?:abre|abrir|[aá]breme|pon|ponme|reproduce|reproducir|busca|buscar|play|lanza|quiero|escuchar|mu[eé]strame|ver)\b", t, re.I))

    # la hora y la fecha: se saben sin preguntarle a nadie. Las dice el reloj de este
    # equipo, al instante, aunque no haya internet ni modelo.
    # Sólo si es **toda** la frase (o un tramo suelto de un plan): «¿qué hora es y sube
    # el volumen?» no se contesta con la hora dejando el volumen sin decir.
    from .intents import _SEPARA
    if trozo or not _SEPARA.search(t):
        if re.search(r"\bqu[eé]\s+hora(?:s)?\s+(?:es|son)\b|\bme\s+(?:dices|das|puedes\s+decir)\s+la\s+hora\b"
                     r"|\bhora\s+actual\b|\ba\s+qu[eé]\s+hora\s+estamos\b", t, re.I):
            return _call("hora")
        if re.search(r"\bqu[eé]\s+(?:d[ií]a|fecha)\s+(?:es|estamos)\b|\ba\s+cu[aá]ntos\s+estamos\b"
                     r"|\bfecha\s+de\s+hoy\b|\bqu[eé]\s+d[ií]a\s+es\s+hoy\b", t, re.I):
            return _call("fecha")

    # cronómetro
    if re.search(r"\bcron[oó]metro\b", t, re.I):
        if re.search(r"\b(para|parar|det[eé]n|detener|detenga|termina|pausa|stop)\b", t, re.I):
            return _call("cronometro", orden="parar")
        if re.search(r"\b(reinicia|reiniciar|reset|resetea|a cero|de nuevo)\b", t, re.I):
            return _call("cronometro", orden="reiniciar")
        return _call("cronometro", orden="iniciar")

    # agenda: listar y cancelar
    if re.search(r"\b(cancela|cancelar|elimina|borra|quita|desactiva|apaga)\b.*\b(alarmas?|recordatorios?|pendientes)\b", t, re.I):
        tipo = ("alarma" if re.search(r"alarma", t, re.I) and not re.search(r"recordatorio", t, re.I)
                else "recordatorio" if re.search(r"recordatorio", t, re.I) and not re.search(r"alarma", t, re.I)
                else "todo")
        todas = bool(re.search(r"\b(todas|todos|todo)\b", t, re.I))
        return _call("agenda_cancelar", tipo=tipo, todas=1 if todas else None)
    if re.search(r"\b(qu[eé]|cu[aá]les|cu[aá]ntas?|lista|dime|mu[eé]strame|revisa)\b.*\b(alarmas?|recordatorios?|pendientes|agenda)\b"
                 r"|\b(mis|mi)\s+(alarmas?|recordatorios?|agenda|pendientes)\b", t, re.I):
        return _call("agenda_listar")

    # notas
    if re.search(r"\b(mis notas|lee\s+(?:mis\s+)?notas|qu[eé] anot[eé]|notas guardadas)\b", t, re.I):
        return _call("leer_notas")
    if (m := re.match(r"(?:anota|apunta|guarda(?:\s+(?:esta|una))?\s+nota|toma\s+nota)\b[\s:,]*(?:que|de|sobre)?\s*(.+)$", t, re.I)):
        return _call("nota", texto=m.group(1))

    # evento de calendario (antes que recordatorio: «agenda una reunión» lleva hora)
    if re.search(r"\b(evento|cita|reuni[oó]n)\b", t, re.I) and re.search(
            r"\b(agenda|programa|crea|a[nñ]ade|agrega|pon|ponme|anota|calendario)\b", t, re.I):
        d, resto = tiempo.extraer_cuando(t, ahora, hora_por_defecto=(9, 0))
        if d is not None:
            titulo = re.sub(r"\b(en\s+(?:mi|el)\s+calendario|(?:a|al)\s+mi\s+calendario)\b", "", resto, flags=re.I)
            titulo = re.sub(r"^\s*(?:agenda|programa|crea|a[nñ]ade|agrega|pon|ponme|anota)(?:me)?\s+(?:(?:una|un|el|la)\s+)?", "", titulo.strip(), flags=re.I)
            # «un evento cena con Ana» → «cena con Ana»; «una reunión con Juan» se queda.
            titulo = re.sub(r"^(?:evento|cita)\s*(?:de|para|:)?\s*", "", titulo, flags=re.I)
            titulo = limpiar(titulo.strip(" ,.")) or "Evento"
            return _call("evento_calendario", titulo=titulo[:1].upper() + titulo[1:], inicio=_fecha_llamada(d))

    # recordatorio: «recuérdame … a las 6», «avísame en 20 minutos que …»
    if re.search(r"\b(recu[eé]rdame|recordarme|recu[eé]rdeme|av[ií]same|recordatorio)\b", t, re.I):
        d, resto = tiempo.extraer_cuando(t, ahora, hora_por_defecto=(9, 0))
        if d is not None:
            texto_r = re.sub(r"\b(?:pon(?:me)?\s+(?:un\s+)?recordatorio|recu[eé]rdame|recordarme|recu[eé]rdeme|av[ií]same|recordatorio)\b",
                             "", resto, flags=re.I)
            texto_r = re.sub(r"^\s*(?:de|para|sobre)\s+", "", texto_r.strip(" ,.:"), flags=re.I)
            texto_r = limpiar(texto_r.strip(" ,.:"))
            if texto_r:
                return _call("recordatorio", cuando=_fecha_llamada(d), texto=texto_r)
        return None  # se deja pasar: el modelo puede preguntar qué falta

    # alarma
    if re.search(r"\b(alarma|despi[eé]rtame|despertador)\b", t, re.I):
        d, resto = tiempo.extraer_cuando(t, ahora)
        if d is not None:
            etiqueta_ = re.sub(r"\b(?:pon(?:me)?|programa|crea|activa)?\s*(?:una\s+|la\s+)?(?:alarma|despi[eé]rtame|despertador)(?:\s+para)?\b",
                               "", resto, flags=re.I)
            return _call("alarma", cuando=_fecha_llamada(d), texto=limpiar(etiqueta_.strip(" ,.:")) or None)
        return None

    # YouTube
    if re.search(r"\byou\s?tube\b", t, re.I) and (con_verbo or not trozo):
        q = re.sub(r"\b(?:en|de|desde|por|a)\s+(?:el\s+)?you\s?tube\b|\byou\s?tube\b", " ", t, flags=re.I)
        q = re.sub(r"^\s*(?:abre|abrir|[aá]breme|pon(?:me)?|reproduce|busca(?:me)?|buscar|mu[eé]strame|quiero\s+ver|"
                   r"ver|play|lanza)\b\s*(?:(?:un|una|el|la|los|las|unos|unas)\s+)?(?:video(?:s)?\s+(?:de\s+)?)?", "", q, flags=re.I)
        consulta_yt = limpiar(q.strip(" ,.")) or None
        if _resto_suelto(consulta_yt):
            return None
        return _call("youtube", consulta=consulta_yt)

    # Spotify o «pon música…»
    musica = re.search(r"\b(m[uú]sica|canci[oó]n|canciones|[aá]lbum|playlist|disco|escuchar)\b", t, re.I)
    if (con_verbo or not trozo) and (re.search(r"\bspotify\b", t, re.I) or (musica and re.search(
            r"\b(pon|ponme|reproduce|reproducir|quiero|escuchar|play|busca)\b", t, re.I))):
        destino = "spotify"
        if not re.search(r"\bspotify\b", t, re.I) and ctx.musica == "youtube":
            destino = "youtube"
        q = re.sub(r"\b(?:en|de|desde|por|a)\s+(?:el\s+)?spotify\b|\bspotify\b", " ", t, flags=re.I)
        q = re.sub(r"^\s*(?:abre|abrir|[aá]breme|pon(?:me)?|reproduce(?:me)?|reproducir|busca(?:me)?|buscar|quiero\s+escuchar|"
                   r"escuchar|quiero|play|lanza)\b\s*", "", q, flags=re.I)
        q = re.sub(r"^\s*(?:(?:un|una|el|la|los|las|unos|unas|algo\s+de)\s+)?(?:m[uú]sica|canci[oó]n|canciones|[aá]lbum|playlist|disco)\b"
                   r"(?:\s+de)?\s*", "", q, flags=re.I)
        consulta = limpiar(q.strip(" ,."))
        if _resto_suelto(consulta):
            return None
        return _call(destino, consulta=consulta or None)

    # mapas
    if (m := re.match(r"(?:c[oó]mo\s+llego\s+a|d[oó]nde\s+(?:queda|est[aá])|mapa\s+de|ll[eé]vame\s+a|ruta\s+a|"
                      r"navega\s+a|direcciones\s+a|c[oó]mo\s+ir\s+a)\s+(.+)$", t, re.I)):
        return None if _resto_suelto(m.group(1)) else _call("mapa", consulta=m.group(1))

    # buscar en internet
    if (m := re.match(r"(?:busca(?:me)?|buscar|googlea|investiga)\s+(?:en\s+(?:google|internet|la\s+web)\s+)?(.+)$", t, re.I)):
        return None if _resto_suelto(m.group(1)) else _call("buscar_web", consulta=m.group(1))

    # abrir algo conocido
    if (m := re.match(r"(?:abre|abrir|[aá]breme|abrime|lanza|inicia|ejecuta)\s+(.+)$", t, re.I)):
        k = _clave(m.group(1))
        if k in _ALIAS_APPS or k in _ALIAS_CARPETAS or k in _ALIAS_SITIOS:
            # En otro sistema, las apps de Windows no existen: se deja pasar a las
            # órdenes antiguas (`thunar`, `xfce4-terminal`) en vez de decir «no».
            if k in _ALIAS_APPS and not ctx.windows:
                return None
            return _call("abrir_app", nombre=m.group(1))
        return None

    # Windows: multimedia, volumen, recorte, bloqueo
    if ctx.windows:
        if re.fullmatch(r"(?:reproduce|reproducir|dale\s+play)[\s.!]*", t, re.I):
            return _call("multimedia", orden="play_pausa")
        if re.search(r"\b(pausa|pausar|pausa\s+la\s+m[uú]sica|reanuda|reanudar|contin[uú]a|continuar|play)\b", t, re.I) \
                and not re.search(r"\b(temporizador|cron[oó]metro)\b", t, re.I):
            return _call("multimedia", orden="play_pausa")
        if re.search(r"\b(siguiente|pasa\s+(?:de\s+)?canci[oó]n|salta)\b", t, re.I):
            return _call("multimedia", orden="siguiente")
        if re.search(r"\b(anterior|atr[aá]s|vuelve\s+a\s+la\s+anterior)\b", t, re.I) and re.search(r"canci[oó]n|pista|tema|anterior", t, re.I):
            return _call("multimedia", orden="anterior")
        if re.search(r"\b(silencia|silenciar|mutea|mutear|sin\s+sonido|quita\s+el\s+sonido)\b", t, re.I):
            return _call("volumen", orden="silenciar")
        if re.search(r"\b(sube|subir|aumenta|m[aá]s\s+alto)\b.*\bvolumen\b|\bvolumen\b.*\b(m[aá]s\s+alto|arriba)\b", t, re.I):
            return _call("volumen", orden="subir", pasos=15 if re.search(r"\bmucho\b", t, re.I) else
                         (2 if re.search(r"\bun\s+poco\b", t, re.I) else None))
        if re.search(r"\b(baja|bajar|reduce|menos)\b.*\bvolumen\b|\bvolumen\b.*\b(m[aá]s\s+bajo|abajo)\b", t, re.I):
            return _call("volumen", orden="bajar", pasos=15 if re.search(r"\bmucho\b", t, re.I) else
                         (2 if re.search(r"\bun\s+poco\b", t, re.I) else None))
        if re.search(r"\b(captura|recorte|pantallazo|screenshot)\b", t, re.I):
            return _call("captura")
        if re.search(r"\b(bloquea|bloquear)\b.*\b(pc|computador|computadora|equipo|sesi[oó]n|pantalla)\b", t, re.I):
            return _call("bloquear_pc")
    return None


def entender(texto: str, ctx: Contexto) -> list[dict]:
    """Las llamadas que pide un mensaje, en orden, o `[]` si es conversación.

    Dos intentos, en este orden:

    1. **Un plan**: si el mensaje se parte (por `y`, `luego`, comas…) y **cada**
       tramo es una orden por sí solo, son varias («sube el volumen y abre
       YouTube»). Un solo tramo que no se entienda invalida el plan: ejecutar la
       mitad de lo que alguien dijo, sin avisar, es peor que dejarlo al modelo.
    2. **El mensaje entero** como una orden: así «recuérdame comprar pan y leche a
       las 6» no se parte por la `y` (su primer tramo no tiene hora, así que el
       plan no se forma y se llega aquí).

    Tope: `PASOS_MAX` de `intents`, el mismo que el planificador antiguo.
    """
    if not isinstance(texto, str) or not texto.strip():
        return []
    from .intents import PASOS_MAX, _SEPARA  # el mismo criterio de partir
    trozos = [t for t in _SEPARA.split(texto) if t and t.strip()]
    if len(trozos) > 1:
        plan: list[dict] = []
        for trozo in trozos:
            c = _entender_uno(trozo, ctx, trozo=True)
            if c is None:
                plan = []
                break
            if c not in plan:
                plan.append(c)
        if len(plan) > 1:
            return plan[:PASOS_MAX]
    entera = _entender_uno(texto, ctx)
    return [entera] if entera is not None else []


#: Verbos que se prestan al tramo siguiente de un plan, igual que hacía el
#: planificador antiguo (`intents.match_all`): «abre el bloc de notas» heredando
#: el «abre». Lista cerrada; un tramo heredado vuelve a pasar por `_entender_uno`,
#: así que heredar no abre ninguna puerta que la tabla no abra de por sí.
_VERBO = re.compile(r"^\s*(abre|abrir|[aá]breme|abrime|lanza|inicia|pon|ponme|reproduce|"
                    r"busca|buscar|mu[eé]strame|muestra)\b", re.I)


def entender_plan(texto: str, ctx: Contexto) -> tuple[list[dict], list[str]]:
    """`(llamadas, cabos sueltos)`: qué se puede ejecutar ya, y qué trozos no se
    entendieron, dichos tal cual.

    Es la respuesta al «todo o nada» de `entender`. Allí, un solo tramo
    incomprensible tiraba el plan completo y el mensaje entero caía al modelo,
    que a lo sumo proponía una herramienta: «abre YouTube y cuéntame un chiste»
    no abría YouTube ni contaba el chiste. Aquí se hacen **las partes que se
    entienden** y se nombra lo que sobra, para que el servidor se lo pregunte al
    modelo (o lo diga, sin nube).

    El orden de tentativas es una promesa, y cada una protege algo:
    1. **plan completo por tramos**, con herencia de verbo («abre la
       calculadora y el bloc de notas»): si cada trozo se entiende sin ayuda,
       se delega en `entender` tal cual —ningún camino que antes funcionaba
       cambia por culpa de esta función—;
    2. **cabo ejecutable por la otra pila**: si un trozo que aquí no se
       entiende `intents.match_all` sí lo casa («¿qué hora es y sube el
       volumen?» en Linux), se cede el mensaje al camino antiguo, que al menos
       ejecuta el volumen. Parcializar ahí sería cambiar una orden cumplida por
       media;
    3. **la frase entera** como una sola orden —«pon música de Calle 13 y
       Residente en Spotify» sigue siendo UNA búsqueda: ahí la `y` es parte de
       la consulta, no una separadora—;
    4. y sólo entonces, **plan parcial**: lo entendido se ejecuta, lo que sobra
       se nombra.
    """
    if not isinstance(texto, str) or not texto.strip():
        return [], []
    from .intents import PASOS_MAX, _SEPARA, match_all  # el mismo criterio de partir
    trozos = [t.strip() for t in _SEPARA.split(texto) if t and t.strip()]
    if len(trozos) <= 1:
        c = _entender_uno(texto, ctx)
        return ([c], []) if c else ([], [texto.strip()])
    llamadas: list[dict] = []
    cabos: list[str] = []
    heredo = False
    verbo = ""
    for trozo in trozos:
        c = _entender_uno(trozo, ctx, trozo=True)
        if c is None and verbo:
            c = _entender_uno(f"{verbo} {trozo}", ctx, trozo=True)
            heredo = heredo or c is not None
        if c is None:
            cabos.append(trozo)
            continue
        if c not in llamadas:
            llamadas.append(c)
        v = _VERBO.match(_sin_cortesia(trozo))
        if v:
            verbo = v.group(1).lower()
    if not llamadas:
        return entender(texto, ctx), []      # nada por tramos: la tentativa de siempre
    if not cabos and not heredo:
        return entender(texto, ctx), []      # plan completo del camino antiguo, idéntico
    if any(match_all(cabo) for cabo in cabos):
        return entender(texto, ctx), []      # la otra pila lo hace: se cede el todo
    # Con cabos —o con un plan que sólo se completó heredando el verbo— todavía
    # puede ser UNA sola orden cuyo `y` es parte de la consulta: «pon música de
    # Calle 13 y Residente en Spotify» es una búsqueda, no dos. Se prueba la
    # frase entera antes de decidir partir.
    entera = _entender_uno(texto, ctx)
    if entera is not None:
        return [entera], []
    return llamadas[:PASOS_MAX], cabos
