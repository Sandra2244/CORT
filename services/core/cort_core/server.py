import asyncio
import os
import re
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn

# El `.env` se lee **antes** del resto de los imports del paquete: `memory/store.py`
# fija su `DB_PATH` al importarse, y una ruta leída después llegaría tarde.
from .env import load_env
load_env()

from .actions import perform
from .brain import think
from .intents import match_intent
from .memory.facts import extract
from .memory.store import MemoryStore
from .outfit import pick_outfit
from .status import build as status_payload
from . import weather
from . import avatars
from . import initiative
from . import security
from . import timer

app = FastAPI(title="CORT core")


@app.on_event("startup")
async def _start_weather() -> None:
    # Con `CORT_CITY` sin configurar `keep_updating` sale al instante: sin ciudad
    # no sale ni una petición de la máquina, y así quiere seguir CORT por defecto.
    app.state.weather = asyncio.create_task(weather.keep_updating())

# Cuántos segundos pasan entre dos miradas al reloj, y cuántos tiene que llevar
# la usuaria sin decir nada para que CORT se atreva a hablar primero. El segundo
# valor es lo que convierte la iniciativa en cortesía: sin él, un aviso a los
# treinta segundos interrumpiría una frase a medias.
INICIATIVA_S = float(os.getenv("CORT_INITIATIVE_INTERVAL_S", "30"))
INICIATIVA_QUIET_S = float(os.getenv("CORT_INITIATIVE_QUIET_S", "90"))

# Cuántos recuerdos se conservan. No es sólo higiene del disco: `context_for`
# puede llegar a meter los más recientes en el prompt, y evaluar el prompt es lo
# caro de esta máquina (2 núcleos). Sin techo, la base de datos se haría grande y
# cada turno más lento.
MEMORY_KEEP = int(os.getenv("CORT_MEMORY_KEEP", "200"))

memory = MemoryStore()
memory.prune(keep=MEMORY_KEEP)

WHO_AM_I = re.compile(r"\b(cómo|como)\s+me\s+llamo\b|\b¿?qui[ée]n\s+soy\b|\bmi nombre\b", re.I)

def state(thinking=False):
    # El clima se lee de la caché, nunca se pide aquí: `state()` corre dentro del
    # bucle del WebSocket y una petición HTTP bloqueante pararía a todos los
    # clientes mientras el servicio de turno contesta.
    clima = weather.snapshot()
    temp = float(os.getenv("CORT_CITY_TEMP_C", "22")) if clima is None else clima["temp_c"]
    frame = {"type": "state", "outfit": pick_outfit(datetime.now().hour, temp),
             "mood": "calm", "thinking": thinking}
    if clima is not None:
        frame["city"] = clima["city"]
        frame["temp_c"] = clima["temp_c"]
    return frame

def autorizada(conexion) -> bool:
    """Si este lazo puede abrirse: local, o trayendo el token de la red.

    Un solo criterio para el WebSocket y para `GET /avatars/{nombre}`, que es lo
    que evita que una de las dos puertas se quede abierta por descuido. El host y
    el token se leen **en cada petición** y no al importar el módulo: así cambiar
    el `.env` no exige reinventar el servidor, y así las pruebas los ponen y los
    quitan sin recargar nada.
    """
    peer = conexion.client.host if conexion.client else None
    return security.autorizado(security.host_de_escucha(), peer,
                               security.token_configurado(),
                               conexion.query_params.get("token"))


@app.get("/avatars/{nombre}")
async def get_avatar(nombre: str, solicitud: Request):
    """
    Los bytes de un atuendo, sólo si `CORT_AVATAR_DIR` está activado y el nombre
    es un archivo de esa carpeta.

    Es el único endpoint de archivos: el **listado** viaja por el WebSocket, no
    por HTTP. La página se sirve en `:8780` y el core escucha en `:8765`, así que
    un `fetch` al listado necesitaría CORS declarado — y declararlo en toda la API
    sería regalarle a cualquier pestaña del navegador algo que leer.

    Los bytes salen por HTTP con `Access-Control-Allow-Origin: *` **en esta ruta y
    en ninguna más**. No es una concesión nueva: el WebSocket ya acepta cualquier
    origen (no hay cookies ni sesión que robar, y un lazo no lo protege CORS), así
    que quien alcanza `:8765` ya puede pedir este archivo escribiendo la URL. El
    CORS abierto cambia de sitio el riesgo cero y no lo aumenta.

    Lo que sí cambió: un `.vrm` no se puede colgar de una etiqueta `<img>`. Se lee
    con `fetch` hacia `GLTFLoader`, y **medido el 2026-10-09** el navegador lo
    cortó con `blocked by CORS policy` — el cuerpo 3D no se cargaba **en ningún
    arranque real**, tampoco en el de la usuaria.

    Desde que el core puede escuchar en la red (`--lan` con `CORT_LAN_TOKEN`) el
    token se pide **aquí también**: esta ruta es la única que devuelve archivos,
    y la carpeta de atuendos es la que tiene las fotos y los modelos de una
    persona. Va por `?token=` porque la piden un `<img>` y un `fetch` del
    navegador, y ninguno de los dos puede mandar una cabecera propia.
    """
    if not autorizada(solicitud):
        # 401 y no 404: aquí lo que falta no es el archivo, es la llave, y un
        # cliente que no la tiene necesita saberlo para pedírsela a quien lo
        # arrancó. La existencia del nombre no se revela igual: se comprueba el
        # token **antes** de tocar el disco.
        raise HTTPException(status_code=401, detail="falta el token de la red")
    ruta = avatars.ruta_segura(nombre)
    if ruta is None:
        # 404 y no 403: un 403 confirmaría que el nombre existe en algún sitio.
        raise HTTPException(status_code=404, detail="atuendo no disponible")
    return FileResponse(ruta, media_type=avatars.tipo_de(ruta),
                        headers={"Access-Control-Allow-Origin": "*"})


async def _cuidar_iniciativa(sock: WebSocket, actividad: dict) -> None:
    """El turno de reloj de una conexión: mira, propone y calla. **No ejecuta nada.**

    Vive atada al lazo que atiende a esa usuaria, y se cancela con él — por eso
    `dichas` es local: al reconectar, CORT vuelve a no haber dicho nada, que es
    lo honesto con una conversación que también empieza de cero en el log.

    Lee la temperatura de la **caché del clima**, nunca del valor de reserva: un
    «abrígate» sacado de los 22° que PONE el `.env` cuando no hay ciudad medida
    sería un consejo mentiroso.
    """
    if not initiative.enabled() or INICIATIVA_S <= 0:
        return
    dichas: set[str] = set()
    try:
        while True:
            await asyncio.sleep(INICIATIVA_S)
            if actividad.get("ocupada") or time.monotonic() - actividad["ultimo"] < INICIATIVA_QUIET_S:
                continue
            clima = weather.snapshot()
            m = initiative.ahora(memory.count(),
                                 clima["temp_c"] if clima else None)
            sug = initiative.sugerir(m, dichas)
            if sug is None:
                continue
            dichas.add(sug.clave)
            await sock.send_json({"type": "proactive", "text": sug.texto,
                                  "mood": "calm", "clave": sug.clave})
    except (WebSocketDisconnect, RuntimeError):
        # RuntimeError: el lazo se cerró entre el `sleep` y el envío. No es un
        # fallo de CORT, es que la pestaña se cerró; callar y salir.
        return


async def _correr_cuenta(sock: WebSocket, segundos: int) -> None:
    """La única tarea que el temporizador tiene: existe mientras cuenta.

    Es un `Task` por conexión y **una sola a la vez**: en reposo no hay reloj, ni
    `setInterval`, ni memoria reservada, que es lo que pidió la dueña del proyecto.
    Al acabar avisa por el log; si se cancela, `CancelledError` se propaga sin
    limpiar nada, porque no hay estado que limpiar.
    """
    try:
        await timer.correr(lambda cuadro: sock.send_json(cuadro), segundos)
    except (WebSocketDisconnect, RuntimeError):
        # El lazo se cerró a mitad de la cuenta: el `finally` de la conexión ya
        # habrá cancelado esta tarea. No hay a quién avisar.
        return
    await sock.send_json({"type": "effect", "kind": "pulse"})
    await sock.send_json({"type": "assistant_message", "text": "Se acabó el tiempo.", "mood": "calm"})


@app.websocket("/ws")
async def ws(sock: WebSocket):
    # El candado va **antes** de `accept()`: cerrar después de aceptar sería
    # regalarle a cualquiera un lazo abierto, una tarea de iniciativa y un
    # saludo hasta el `finally`. Cerrando antes Starlette responde 403 al
    # apretón de manos y del otro lado no se abre nada.
    if not autorizada(sock):
        await sock.close(code=4401)
        return
    await sock.accept()
    history: list[dict] = []
    name = memory.name_of_user()
    # El reloj de la conexión: cuándo habló por última vez quien está al otro
    # lado. Es un `dict` porque lo escribe el bucle del WebSocket y lo lee la
    # tarea de iniciativa; una variable suelta no se puede reasignar desde el
    # bucle sin atar un `nonlocal` a dos sitios a la vez.
    actividad = {"ultimo": time.monotonic()}
    tarea = asyncio.create_task(_cuidar_iniciativa(sock, actividad))
    # La cuenta atrás en marcha, o `None`. Un solo hueco y no una lista: dos
    # temporizadores a la vez se verían como dos reloles peleando en la pantalla,
    # y en esta máquina cada uno es una tarea y cuadros por segundo.
    cuenta: dict = {"tarea": None}
    await sock.send_json(state())
    # `greeting` y no `assistant_message`: el saludo es lo que CORT dice al
    # *presentarse*, y una reconexión no es una presentación. Medido en el
    # navegador: la pestaña que sobrevive a varios reinicios del core muestra el
    # reintento cada tres segundos, y acumuló cuatro «Hola, soy CORT.» seguidos.
    # La interfaz sólo pinta éste si el registro está vacío.
    await sock.send_json({"type": "greeting",
                          "text": f"Hola de nuevo, {name}." if name else "Hola, soy CORT.",
                          "mood": "calm"})
    # Después del saludo, no antes: `count()` es una lectura al disco, y lo
    # primero que debe notar quien abre la página es que CORT contesta.
    await sock.send_json(status_payload(memory, MEMORY_KEEP))
    try:
        while True:
            msg = await sock.receive_json()
            if msg.get("type") == "list_avatars":
                # Se pide aquí y no con `fetch` por el motivo escrito en el
                # endpoint: el listado no necesita CORS si viaja por el cable que
                # la usuaria ya abrió, y así no hay que declarar orígenes.
                await sock.send_json({"type": "avatars", "items": avatars.listar()})
                continue
            if msg.get("type") != "user_message":
                continue
            text = msg.get("text", "").strip()
            if not text:
                continue
            # Desde aquí cuenta el reloj de cortesía: la iniciativa no habla
            # mientras la usuaria está escribiendo o esperando su respuesta.
            actividad["ultimo"] = time.monotonic()
            for fact in extract(text):
                memory.remember(fact)
            # El temporizador se mira **antes** que los intents locales y que el
            # LLM: «pon un temporizador de 5 minutos» no es una orden al sistema
            # (no pasa por `actions`, no ejecuta nada) y preguntarle a Ollama por
            # una cuenta atrás costaría 15-60 s de CPU en esta máquina.
            en_marcha = cuenta["tarea"] is not None and not cuenta["tarea"].done()
            if en_marcha and timer.quiere_cancelar(text):
                # Solo se interfiere si hay algo que cancelar: «cancela» dicho
                # sin temporizador sigue su camino normal, hacia el LLM.
                cuenta["tarea"].cancel()
                cuenta["tarea"] = None
                await sock.send_json({"type": "timer", "estado": "cancela",
                                      "restante": 0, "total": 0})
                await sock.send_json({"type": "assistant_message",
                                      "text": "Temporizador cancelado.", "mood": "calm"})
                continue
            segundos = timer.parse(text)
            if segundos:
                if en_marcha:
                    await sock.send_json({"type": "assistant_message",
                                          "text": "Ya hay una cuenta atrás en marcha; "
                                                  "di «cancela el temporizador» y empiezo otra.",
                                          "mood": "calm"})
                    continue
                cuenta["tarea"] = asyncio.create_task(_correr_cuenta(sock, segundos))
                await sock.send_json({"type": "assistant_message",
                                      "text": f"Cuenta atrás de {timer.texto(segundos)}.",
                                      "mood": "calm"})
                continue
            intent = match_intent(text)
            if intent:
                await sock.send_json({"type": "intent", **intent})
                ok, said = await perform(intent)
                # La onda marca el momento en que algo se ejecutó de verdad y el
                # rasgón cuando no: un holograma que parpadea todo el tiempo no
                # comunica nada.
                await sock.send_json({"type": "effect", "kind": "pulse" if ok else "glitch"})
                await sock.send_json({"type": "assistant_message",
                                      "text": said if ok else f"No pude: {said}.",
                                      "mood": "calm"})
                # Los hechos de un mensaje se guardan antes de mirar los intents,
                # así que el contador puede haber cambiado incluso sin LLM.
                await sock.send_json(status_payload(memory, MEMORY_KEEP))
                continue
            if WHO_AM_I.search(text):
                # Se responde desde la memoria, sin LLM: funciona aunque Ollama no esté.
                known = memory.name_of_user()
                reply = f"Te llamas {known}." if known else "Aún no me has dicho tu nombre."
                await sock.send_json({"type": "assistant_message", "text": reply, "mood": "calm"})
                continue
            history.append({"role": "user", "content": text})
            await sock.send_json(state(thinking=True))
            relevant = memory.context_for(text)
            context = [{"role": "system", "content": "Datos del usuario: " + "; ".join(relevant)}] if relevant else []
            # Un turno con Ollama en esta máquina dura entre 15 y 60 s medidos.
            # Sin este marcador, la iniciativa podría colar un «¿café?» delante de
            # la respuesta que la usuaria está esperando.
            actividad["ocupada"] = True
            try:
                reply = await think([*context, *history[-20:]])
            finally:
                actividad["ocupada"] = False
            history.append({"role": "assistant", "content": reply})
            await sock.send_json({"type": "assistant_message", "text": reply, "mood": "calm"})
            # **La respuesta se siente, no sólo se lee.** El temblor va en el marco
            # del HUD (`arrastre.ts` lo separó a propósito: el `shake` escribe
            # `transform` y el arrastre también) y es lo que pidió la dueña del
            # proyecto: «el orbe responde y vibra al responder». Sale **después** del
            # mensaje y no antes, para que la sacudida coincida con el texto que ya
            # está en pantalla y no con un vacío que anuncia algo. El saludo
            # (`greeting`) **no** la dispara: se emite en cada reconexión y una
            # pantalla que tiembla al levantar el servidor es ruido, no respuesta.
            await sock.send_json({"type": "effect", "kind": "shake"})
            await sock.send_json(state())
            # Después de `think()` es cuando `brain.last_model()` tiene algo que
            # decir: el panel nombra el modelo que acaba de contestar.
            await sock.send_json(status_payload(memory, MEMORY_KEEP))
    except WebSocketDisconnect:
        pass
    finally:
        # La tarea de reloj muere con su conexión. Dejarla suelta sería dejar a
        # CORT hablando hacia una pestaña que ya no está — y una tarea por cada
        # pestaña abierta y cerrada, acumulada de por vida.
        tarea.cancel()
        # Lo mismo con la cuenta atrás: sin esto, un temporizador de una hora
        # seguiría enviando cuadros a una conexión cerrada durante una hora.
        if cuenta["tarea"] is not None:
            cuenta["tarea"].cancel()

if __name__ == "__main__":
    # 127.0.0.1 por defecto, y no 0.0.0.0: el core no tiene autenticación ni TLS.
    # Publicarlo en la red es decisión explícita de quien arranca (`cort.py --lan`),
    # no un regalo del valor por defecto.
    host = os.getenv("CORT_HOST", "127.0.0.1")
    motivo = security.rechazo_de_arranque(host, security.token_configurado())
    if motivo:
        # Se niega y sale con código 1: el lanzador ya avisa de que el core murió
        # y la usuaria lee el motivo en la terminal. Un servidor que arranca
        # "aunque le falte el token" es justo el que nadie nota abierto.
        print(f"CORT no arranca: {motivo}", flush=True)
        raise SystemExit(1)
    uvicorn.run(app, host=host, port=int(os.getenv("CORT_PORT", "8765")))
