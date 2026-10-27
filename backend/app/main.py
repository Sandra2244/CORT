"""CORT backend — FastAPI.

Endpoints:
  POST /api/chat    {message}            -> {reply, source}
  POST /api/command {message}            -> {reply, source, done[]} (acciones del sistema)
  GET  /api/status                       -> estado del cerebro híbrido + sistema
  GET  /api/port                         -> en qué puerto vive este backend
  GET  /api/history                      -> últimas respuestas recordadas
  POST /api/profile   {clave, valor}     -> memoria de preferencias
  GET/POST /api/config                  -> cerebro y voz, leídos al vuelo (claves en máscara)
  GET  /api/brain/test                  -> prueba cada proveedor, con ms y modelo
  POST /api/open     {path}              -> abre un archivo/carpeta permitido en su visor
  POST /api/launch   {app}               -> lanza una app de la lista blanca (youtube, navegador…)
  GET  /api/files?path=                  -> explorador de carpetas (raíces seguras)
  GET  /api/tree?path=                   -> hijos de una carpeta con conteos (árbol lateral)
  GET  /api/memories                     -> muro de recuerdos (notas + conversaciones)
  GET  /api/weather?lugar=               -> clima actual (Open-Meteo, cacheado)
  GET  /api/voice                        -> qué boca tiene este equipo y sus timbres
  POST /api/voice/say {texto,voz,tono,velocidad} -> WAV hablado (o 503 con el motivo)
  GET  /api/support                      -> contacto y soporte de la ventana 09
  GET  /api/models                       -> catálogo Ollama + si cabe en este equipo
  GET  /api/models/progreso              -> avance de las descargas en curso
  POST /api/models/pull|rm|use|ollama    -> descargar, borrar, usar u encender Ollama
  POST /api/models/cancel                -> cortar una descarga o quitarla de la fila
  GET  /api/optimize                     -> quién come RAM y cuánta caché hay que borrar
  POST /api/optimize/clean|kill          -> vaciar cachés seguras / cerrar un proceso
  GET  /api/letras?artista=&titulo=&duracion= -> letra (LRCLIB) sincronizada o plana
  GET  /api/music?q=&genero=&carpeta=&lista=  -> discoteca del PC: etiquetas ID3,
                                  carpetas como estilo, playlists y reproductor real
  GET  /api/audio?ruta=                        -> el archivo de música (sólo Música/)
  POST /api/play          {ruta}               -> abre el REPRODUCTOR DEL SISTEMA
  GET  /api/play/estado                        -> ¿suena de verdad? (playerctl o nada)
  POST /api/music/lista   {nombre, rutas}      -> guarda una playlist (409 si existe)
  POST /api/organizar    {raiz, criterio}          -> PLAN de orden (no toca nada)
  POST /api/organizar/aplicar {raiz, criterio, token} -> ejecutar el plan confirmado
  GET  /api/copiloto                    -> qué comandos puede ejecutar solo CORT
  POST /api/copiloto/plan    {objetivo}            -> PLAN de pasos (no ejecuta nada)
  POST /api/copiloto/ejecuta {token, indice}       -> correr UN paso sólo si es de sólo lectura
  GET  /api/update                       -> qué CORT tengo y qué hay en GitHub
  POST /api/update/aplicar {asset}       -> descargar/preparar el instalador nuevo

Si CORT_SERVE_UI=1 (o el ejecutor lo pide), el mismo backend reparte también la
interfaz en `http://<host>:<puerto>/` — un solo proceso, cero puertos extra.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# carga .env antes de importar brain
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

import actions                                  # noqa: E402
import actualiza                                # noqa: E402  (GitHub: versión y reparación)
from brain import brain_status, think          # noqa: E402
import brain                                    # noqa: E402  (test_all / recarga de config)
import config_store                             # noqa: E402
import copiloto                                 # noqa: E402  (copiloto de terminal: sólo lectura)
import letras                                   # noqa: E402  (LRCLIB, sin clave)
import memory                                   # noqa: E402
import musica                                   # noqa: E402  (discoteca del PC: carpetas, etiquetas, listas)
import local_commands                           # noqa: E402
import models                                   # noqa: E402  (Ollama: catálogo y descargas)
import organiza                                 # noqa: E402  (plan de orden, sin borrar)
import optimize                                 # noqa: E402  (RAM y caché del equipo)
import sensors                                  # noqa: E402
import voz                                      # noqa: E402  (la boca del escritorio: espeak-ng)

from fastapi import FastAPI, Request           # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles     # noqa: E402
from pydantic import BaseModel                  # noqa: E402

VERSION = "0.2.0"
app = FastAPI(title="CORT", version=VERSION)

# El holograma habla con el backend solo desdelocalhost, pero puede vivir en
# cualquier puerto (Electron empaquetado usa uno aleatorio, la app de Android
# reporta https://localhost). Por eso se aceptan todos los localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_origins=["null"],
    allow_methods=["*"], allow_headers=["*"],
)


@app.middleware("http")
async def sin_cache_en_api(request, call_next):
    """Los sensores y el estado del equipo cambian cada segundo: si el navegador
    (o el WebView de Android, o Electron) guarda la respuesta en caché, CORT se
    queda viendo datos viejos. La API siempre se responde sin caché.

    La cara se sirve aquí sólo en el portátil (`CORT_SERVE_UI=1`): sus módulos ES
    también van sin caché. El APK ya manda `Cache-Control: no-store` en
    `MainActivity.sirve()`; sin esto, el navegador seguía ejecutando el `hud.js`
    viejo después de una actualización del repo (medido el 2026-10-24: un
    `reload` normal no invalidaba el mapa de módulos de Chromium)."""
    respuesta = await call_next(request)
    ruta = request.url.path
    if (ruta.startswith("/api/") or ruta.startswith(("/js/", "/css/", "/vendor/"))
            or ruta.endswith(".html")):
        respuesta.headers["cache-control"] = "no-store"
    return respuesta


class Msg(BaseModel):
    message: str


class Perfil(BaseModel):
    clave: str
    valor: str


@app.post("/api/chat")
def chat(msg: Msg):
    question = msg.message.strip()
    if not question:
        return {"reply": "¿En qué puedo ayudarte?", "source": "local"}
    hist = memory.history()
    reply, source = think(question, hist)
    memory.remember("user", question)
    memory.remember("assistant", reply, source)
    return {"reply": reply, "source": source}


@app.post("/api/command")
def command(msg: Msg):
    """Órdenes que tocan el sistema (nota, abrir carpeta/archivo, sitio, música).
    Acepta varias en una frase («apunta esto y abre Documentos») y devuelve
    {reply, source, done:[acciones]} para que la pantalla reaccione a cada una."""
    return actions.run_command(msg.message)


@app.get("/api/status")
def status():
    return {"brain": brain_status(), "system": local_commands.system_stats(),
            "battery": local_commands.battery(), "version": VERSION}


@app.get("/api/port")
def port(request: Request):
    """Desde qué puerto está sirviendo ESTE backend. La pantalla lo consulta
    cuando no está en el :8080 de costumbre (Electron empaquetado, Termux…)."""
    return {"port": request.url.port, "base": str(request.base_url)}


# Contacto que muestra la ventana 09 · Ayuda (y el README, en la sección
# "Soporte"). Editar aquí es suficiente: la pantalla lo lee al arrancar.
SUPPORT = {
    "proyecto": "C.O.R.T. — Cognitive Orchestrator / Real-Time. Proyecto personal, "
                "abierto y sin fines de lucro: si quieres hablar de él, colaborar o "
                "apoyar el trabajo, escribe a cualquiera de estos correos.",
    "contacto": [
        {"correo": "sandrasofialopezgomez3@gmail.com", "rol": "creadora del proyecto"},
        {"correo": "carlosa3325@gmail.com", "rol": "colaborador"},
    ],
    "nota": "¿Eres programador y quieres sumar una función, un idioma o un cerebro "
            "nuevo? Escríbenos con el asunto «CORT» y te contamos por dónde seguir.",
    "donaciones": [],          # añade aquí Mercado Pago / PayPal si quieres recibir apoyo
    "plataformas": ["Windows", "Linux", "macOS", "Android"],
    "version": VERSION,
}


@app.get("/api/support")
def support():
    return SUPPORT


@app.get("/api/history")
def history(n: int = 10):
    with memory._conn() as c:
        rows = c.execute(
            "SELECT rol, texto, fuente, t FROM conversacion ORDER BY id DESC LIMIT ?",
            (n,)).fetchall()
    return [{"rol": r, "texto": t, "fuente": f, "t": ts} for r, t, f, ts in rows[::-1]]


@app.post("/api/profile")
def profile(p: Perfil):
    memory.set_profile(p.clave, p.valor)
    return {"ok": True}


@app.get("/api/profile")
def profile_get():
    return memory.get_profile()


# ------------------------------------------------------------------ config
# La ventana PERFIL puede cambiar cerebro y voz SIN tocar el .env ni
# reiniciar: se guarda en backend/cort_config.json y se lee en cada petición.
@app.get("/api/config")
def config_get():
    return config_store.masked()


@app.post("/api/config")
def config_set(p: Perfil):
    ok = config_store.set_value(p.clave, p.valor)
    return {"ok": ok, "clave": p.clave}


@app.get("/api/brain/test")
def brain_test():
    """«Probar cerebro»: responde cada proveedor y mide cuánto tardó."""
    return {"resultados": brain.test_all()}


class Nota(BaseModel):
    texto: str


@app.get("/api/notes")
def notes():
    return memory.list_notes()


@app.post("/api/notes")
def notes_add(n: Nota):
    if not n.texto.strip():
        return {"error": "nota vacía"}
    return {"id": memory.add_note(n.texto)}


@app.delete("/api/notes/{note_id}")
def notes_del(note_id: int):
    return {"ok": memory.delete_note(note_id)}


@app.get("/api/files")
def files(path: str = ""):
    return sensors.list_dir(path)


@app.get("/api/lee")
def lee(path: str = "", maximo: int = 6000):
    """Contenido de un archivo de texto para **adjuntarlo a la charla**.

    No es un lector nuevo: es `sensors.leer_texto`, la misma función que usa «lee el
    documento X», con el mismo candado (sólo dentro de Documentos/Escritorio/
    Descargas/Imágenes/Música/Videos, y `../` bloqueado). El tope se limita por aquí
    porque el portátil de la dueña tiene 1,8 GiB: un `log` de 40 MB no puede entrar
    en un prompt. Lo que no es texto plano (PDF, docx, imágenes) devuelve `ok:false`
    con el motivo, y la cara lo dice tal cual en vez de inventar un resumen.
    """
    return sensors.leer_texto(path, max(200, min(int(maximo or 6000), 20000)))


@app.get("/api/tree")
def tree(path: str = ""):
    """Hijos de una carpeta con sus conteos — para expandir el árbol lateral."""
    return sensors.tree(path)


@app.get("/api/memories")
def memories(n: int = 24):
    """Muro de recuerdos (notas + conversaciones) para la ventana Cerebro."""
    return {"recuerdos": memory.memories(n)}


class RecuerdosReq(BaseModel):
    recuerdos: list[str] = []          # lo que CORT guardó en el teléfono


@app.post("/api/memories")
def memories_subir(r: RecuerdosReq):
    """La otra mitad de «sincroniza con el PC»: el APK baja sus recuerdos por la
    Wi-Fi para que el portátil sea la memoria grande. Entran como nota, en la
    misma mesa de la ventana Cerebro, y **no se repite** lo que ya se sabía: si la
    frase exacta ya está en el muro, se cuenta como ignorada en vez de duplicar.

    Sin esta puerta la sincronía era de una sola dirección — el teléfono leía,
    pero lo que aprendía se quedaba sólo en el aparato (y se perdía al cambiar de
    móvil). NOMBRES Y FORMAS = CONTRATO con `Sincroniza.java` del APK."""
    ya_esta = {m["texto"].strip().casefold() for m in memory.memories(400)}
    nuevos = ignorados = 0
    for texto in r.recuerdos[:200]:                 # techo honesto por petición
        limpio = (texto or "").strip()
        if len(limpio) < 3 or limpio.casefold() in ya_esta:
            ignorados += 1
            continue
        memory.add_note(limpio)
        ya_esta.add(limpio.casefold())
        nuevos += 1
    return {"ok": True, "guardados": nuevos, "ignorados": ignorados}


@app.get("/api/weather")
def weather(lugar: str = ""):
    """Clima con Open-Meteo. Sin `lugar` es el de la IP (la ventana de entorno);
    con nombre —«Sevilla», «Gijón»— se buscan primero las coordenadas en el
    geocoder gratuito y se contesta con el sitio que se encontró escrito."""
    return sensors.weather(lugar=lugar.strip() or None)


@app.get("/api/voice")
def voice_estado():
    """Qué boca tiene este equipo.

    En Linux el navegador de escritorio no da ninguna voz (medido:
    `speechSynthesis.getVoices()` = 0 y `voiceschanged` no trae nada), así que la
    cara pregunta aquí antes de pintar el desplegable de 07 · Perfil: si `motor`
    viene con un nombre, la boca es la del núcleo y `voces` son los timbres que
    este equipo **de verdad pronuncia**; si viene `null`, la cara lo dice en vez de
    ofrecer deslizadores mudos.
    """
    return voz.estado()


class Decir(BaseModel):
    texto: str = ""
    voz: str = ""
    tono: float = 1.0
    velocidad: float = 1.0


@app.post("/api/voice/say")
def voice_say(d: Decir):
    """Habla por el motor del equipo y devuelve el WAV.

    Responde 503 con `{"error": …}` cuando no puede hablar: el silencio sin motivo
    fue justo lo que hizo dudar de toda la sección de voz, y la cara enseña la
    palabra de error en la consola.
    """
    r = voz.sintetiza(d.texto, voz=d.voz, tono=d.tono, velocidad=d.velocidad)
    if not r.get("ok"):
        return JSONResponse({"ok": False, "error": r.get("error", "sin-motor"),
                             "motivo": r.get("motivo", "")}, status_code=503)
    return Response(content=r["wav"], media_type="audio/wav",
                    headers={"x-cort-voz": r.get("voz") or "natural",
                             "x-cort-pitch": str(r.get("pitch")),
                             "x-cort-wpm": str(r.get("wpm"))})


@app.get("/api/music")
def music(q: str = "", genero: str = "", carpeta: str = "", lista: str = "",
          limite: int = 400, refrescar: bool = False):
    """La discoteca del PC entera, o filtrada, con lo que de verdad se pudo leer.

    El cuerpo lo arma `musica.informe` (fuera de FastAPI, para que las pruebas de
    Actions puedan comprobar el contrato sin instalar el framework). `canciones`
    conserva los campos de siempre — `nombre`, `artista`, `ruta`, `dur` — para que
    la cara vieja siga valiendo, y añade `album`, `genero`, `carpeta`, `seg`,
    `video` y `letra`. `vacio` dice por qué no hay nada: no es lo mismo «no tienes
    carpeta de Música» que «nada encaja con tu filtro».
    """
    return musica.informe(q=q, genero=genero, carpeta=carpeta, lista=lista,
                          limite=limite, refrescar=refrescar)


@app.get("/api/audio")
def audio(ruta: str):
    from fastapi.responses import FileResponse
    f = sensors.music_path(ruta)
    if not f:
        return {"error": "archivo no encontrado o fuera de Música"}
    return FileResponse(f)


class Play(BaseModel):
    ruta: str = ""


@app.post("/api/play")
def play(p: Play):
    """Ejecutor de música en el SISTEMA: abre el reproductor predeterminado
    (VLC u otro) con una canción; sin ruta, elige una al azar de ~/Música.

    Devuelve el programa que respondió por el archivo (`reproductor`, consultado
    con `xdg-mime` en este equipo) y `estado`, que sólo dice `reproduciendo` si
    `playerctl` lo confirmó; si no, dice `desconocido` y la cara lo enseña así.
    """
    return musica.suena(p.ruta)


@app.get("/api/play/estado")
def play_estado():
    """Si de verdad está sonando algo, según el propio sistema."""
    return {"estado": musica.estado_real(),
            "reproductor": musica.reproductor_predeterminado()}


class Lista(BaseModel):
    nombre: str = ""
    rutas: list[str] = []


@app.post("/api/music/lista")
def music_lista(L: Lista):
    """Guarda una playlist de CORT en `~/.cort/listas/`. Nunca sobrescribe: si el
    nombre ya existe, devuelve el error y la cara lo dice con esas palabras."""
    r = musica.pon_lista(L.nombre, L.rutas)
    return JSONResponse(r, status_code=409 if r.get("existe") else 200)


class Launch(BaseModel):
    app: str = ""


@app.post("/api/launch")
def launch(l: Launch):
    """«Abre YouTube» → lanza la app de la LISTA BLISTA con el navegador
    predeterminado (referencia: APPLICATION LANCÉE del video francés)."""
    return sensors.launch_app(l.app)


class Open(BaseModel):
    path: str = ""


@app.post("/api/open")
def open_file(o: Open):
    """Abre un archivo o carpeta de las raíces permitidas con su visor
    del sistema (documentos, imágenes, audio, video y comprimidos).
    Nunca ejecuta: las extensiones de programa están bloqueadas."""
    return sensors.open_path(o.path)


# ─────────────────────────── modelos locales (Ollama) ───────────────────────
class Modelo(BaseModel):
    modelo: str = ""


class Ollama(BaseModel):
    accion: str = "start"              # start | stop


@app.get("/api/models")
def models_estado():
    """Catálogo con el peso de cada modelo, si te cabe en la RAM de ESTE
    equipo y cuáles ya están descargados."""
    return models.estado_completo()


@app.get("/api/models/progreso")
def models_progreso():
    """Avance al 1 % de cada descarga en curso."""
    return models.progreso()


@app.post("/api/models/pull")
def models_pull(m: Modelo):
    """Apunta la descarga (`ollama pull`) y devuelve al instante: no bloquea la
    interfaz ni espera a que Ollama despierte (eso lo hace el hilo)."""
    return models.descargar(m.modelo)


@app.post("/api/models/cancel")
def models_cancel(m: Modelo):
    """Corta una descarga en curso o la quita de la fila."""
    return models.cancelar(m.modelo)


@app.post("/api/models/rm")
def models_rm(m: Modelo):
    return models.borrar(m.modelo)


@app.post("/api/models/use")
def models_use(m: Modelo):
    """Lo deja como modelo local activo del cerebro."""
    return models.usar(m.modelo)


@app.post("/api/models/ollama")
def models_ollama(o: Ollama):
    return models.arrancar_servidor() if o.accion == "start" else models.detener_servidor()


# ─────────────────────────── optimización del equipo ────────────────────────
class Nivel(BaseModel):
    nivel: str = "seguro"              # seguro | todo


class Proceso(BaseModel):
    pid: int = 0


@app.get("/api/optimize")
def optimizar_informe(fresco: bool = False):
    """Qué come la RAM ahora mismo y cuánta caché borrable hay en el disco.
    `fresco=1` fuerza a volver a contar (tarda unos segundos)."""
    return optimize.informe(fresco=fresco)


@app.post("/api/optimize/clean")
def optimizar_limpia(n: Nivel):
    """Vacía cachés dentro de la carpeta personal (nunca documentos ni la base
    de datos de CORT). Devuelve los MB liberados."""
    return optimize.limpiar(n.nivel)


@app.post("/api/optimize/kill")
def optimizar_cierra(p: Proceso):
    """Cierra UN proceso propio. Se niega a tocar el escritorio, el audio o
    el propio CORT."""
    return optimize.cerrar(p.pid)


# ────── letras, organizar archivos, copiloto de terminal y actualización ──────
# Cuatro funciones que la dueña pidió con la boca pequeña y la cara grande:
# «ponme mis Documentos en orden» (sin que desaparezca nada), «léeme la letra
# de esta canción», «guíame como copiloto y ejecuta los comandos tú solo» y
# «comprueba si hay un CORT nuevo». Las cuatro viven en módulos propios
# por el mismo motivo: `organiza` confirma antes de mover, `letras`
# cachea para no martillar LRCLIB, `copiloto` sólo ejecuta comandos de
# sólo lectura —el mismo backend escucha por Wi-Fi y un `rm` automático
# desde el teléfono sería un desastre— y `actualiza` jamás descarga 100 MB dentro
# de una petición — el portátil es de 1,8 GiB y no debe congelarse.
# NOMBRES Y FORMAS = CONTRATO con la cara de JS: no renombrar.
class OrganizaReq(BaseModel):
    raiz: str = "Documentos"
    criterio: str = "tipo"                 # tipo | anio | mes


class OrganizaAplicar(BaseModel):
    raiz: str = "Documentos"
    criterio: str = "tipo"
    token: str = ""


class ActualizaReq(BaseModel):
    asset: str = ""                        # vacío = el instalador de escritorio


class CopilotoPlanReq(BaseModel):
    objetivo: str = ""


class CopilotoEjecutaReq(BaseModel):
    token: str = ""
    indice: int = 0


@app.get("/api/letras")
def letras_buscar(artista: str, titulo: str, duracion: int = 0):
    """Letra de LRCLIB: sincronizada si existe, plana si no, cacheada siempre."""
    return letras.letra(artista, titulo, duracion)


@app.post("/api/organizar")
def organizar_plan(r: OrganizaReq):
    """La PROPUESTA de orden con su token: mira, clasifica y no mueve nada."""
    return organiza.plan(r.raiz, r.criterio)


@app.post("/api/organizar/aplicar")
def organizar_aplicar(r: OrganizaAplicar):
    """Ejecuta el último plan cuyo token coincida. Sin plan, o con token viejo,
    se niega: aquí nadie ordena la casa de la dueña a traición."""
    return organiza.aplicar(r.raiz, r.criterio, r.token)


@app.get("/api/copiloto")
def copiloto_permisos():
    """Lo que la cara enseña: la lista de comandos que CORT puede correr solo
    (sólo lectura), los negados siempre y lo que la dueña haya añadido a mano."""
    return copiloto.estado()


@app.post("/api/copiloto/plan")
def copiloto_plan(r: CopilotoPlanReq):
    """La PROPUESTA del copiloto con su token: piensa los pasos y no ejecuta ninguno."""
    return copiloto.plan(r.objetivo)


@app.post("/api/copiloto/ejecuta")
def copiloto_ejecuta(r: CopilotoEjecutaReq):
    """Corre UN paso del último plan, y sólo si el comando es de sólo lectura.
    Con token caducado, o si el paso escribe/borra, se niega y lo dice."""
    return copiloto.ejecutar(r.token, r.indice)


@app.get("/api/update")
def update_comprobar():
    """Versión instalada vs. última Release de GitHub, con notas y enlaces."""
    return actualiza.comprobar()


@app.post("/api/update/aplicar")
def update_aplicar(r: ActualizaReq):
    """Prepara la reparación del escritorio: descarga liviana o `scripts/actualiza.sh`.
    El APK de Android se responde con el enlace, no con una instalación."""
    return actualiza.aplicar(r.asset)


# ─────────────────────────── interfaz en el mismo puerto ────────────────────
# Con CORT_SERVE_UI=1 el backend reparte también el holograma, así que basta
# un solo proceso y una sola dirección: http://127.0.0.1:8000/
# (lo usa el instalador de escritorio, que no necesita abrir el puerto 8080).
def _ui_dir() -> Path | None:
    here = Path(__file__).resolve().parent          # .../backend/app
    for cand in (here.parent.parent / "ui",        # repo:  CORT/ui
                 here.parent.parent.parent / "ui",  # empaquetado: resources/backend/app → resources/ui
                 Path(here.parent.parent.parent) / "ui",
                 Path(os.environ.get("CORT_UI_DIR", "")) if os.environ.get("CORT_UI_DIR") else None):
        if cand and cand.is_dir() and (cand / "index.html").is_file():
            return cand
    return None


UI_DIR = _ui_dir()
if UI_DIR and os.environ.get("CORT_SERVE_UI") == "1":
    app.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="cort-ui")
