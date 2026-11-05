"""F16 — el parlamento: el teléfono habla, la PC escucha, responde y le devuelve la voz.

Es un hilo de conversación por HTTP, no un segundo cerebro. La frase que sale del
micrófono del teléfono entra por **el mismo despacho que el WebSocket**
(`cort_server.atender_input`), así que lo que CORT contesta desde el móvil es
exactamente lo que contestaría sentada delante del portátil. Si alguna vez hay dos
caminos de respuesta, uno de los dos estará mintiendo.

El contrato (todo en el puerto del core, **8765**, con la misma llave del enlace):

* `POST /parlamento?token=…` — cuerpo: WAV mono, 16 bits (el que arma el teléfono en
  memoria). Devuelve JSON con `oido`, `respuesta`, `audio` (PCM 16 LE en base64),
  `tasa`, `segundos`, `vueltas`, `ms_escucha`, `ms_respuesta`, `ms_voz`, `origen`.
* `GET /parlamento?token=…` — estado del hilo: vueltas, motores, topes.
* `POST /parlamento/colgar?token=…` — suelta el hilo y su historial.

Las cuatro reglas de la casa, escritas aquí y comprobadas en
`scripts/prueba_parlamento.py`:

1. **Sin llave no hay parlamento.** 401 con el motivo dicho con palabras.
2. **El audio no se queda en ninguna parte.** La grabación se escribe en el tmp del
   puente sólo mientras Vosk la lee y se borra en el `finally`; la voz sintetizada se
   lee, se manda en el cuerpo de la respuesta y también se borra. Lo que CORT guarda
   son palabras.
3. **Un hilo, una vuelta a la vez.** El `candado` del historial es el mismo que usa el
   WebSocket; dos teléfonos no se pisan la conversación.
4. **Topes por escrito:** 3 MB de cuerpo (~90 s a 16 kHz mono), 40 vueltas de
   historial, 15 min de inactividad antes de tirar la llamada y 90 caracteres dichos
   por el auricular — el texto completo siempre viaja en `respuesta` y se lee en pantalla.

La voz suena en el auricular del teléfono, no por los altavoces de la PC: el canal
falso lleva `por_auricular = True` y `hablar_por_el_puente` guarda el texto en vez de
reproducirlo. Eso es lo que hace que se sienta como una llamada.
"""

import asyncio
import base64
import io
import os
import time
import wave
from collections import deque
from pathlib import Path

from aiohttp import web

MAX_CUERPO = 3 * 1024 * 1024
HISTORIAL_MAX = 40
VIEJO_SEGUNDOS = 15 * 60

# Medido en el puente de arena con la respuesta honesta de "no hay cerebro" (416
# caracteres): decir 220 de ellos son 22,8 s de voz por el auricular y 1 342 768 bytes
# de base64 dentro del JSON. El techo va por debajo: el auricular dice la primera frase
# y la pantalla del teléfono tiene el texto entero.
AURICULAR_MAX_CARACTERES = 90

HILOS = {}


def para_el_auricular(texto):
    """Recorta la respuesta para que el teléfono la escuche, y dice si recortó.

    Devuelve `(lo_que_habla, recortado)`. Se prefiere la primera frase completa: un
    «no puedo» de una línea suena mejor que el principio de un párrafo partido. Si no
    cabe ninguna frase, corta en el último hueco de palabra, porque una palabra
    partido por la mitad suena a avería y no a conversación.

    El punto sólo cierra frase si le sigue un espacio y no va entre dos dígitos: la
    respuesta honesta de arriba lleva la dirección de Ollama —`127.0.0.1:11434`— y
    partir ahí soltaría por el auricular un «en 127.» que no dice nada.
    """
    if len(texto) <= AURICULAR_MAX_CARACTERES:
        return texto, False
    zona = texto[:AURICULAR_MAX_CARACTERES]
    for i, letra in enumerate(zona):
        if letra not in ".!?" or i == 0:
            continue
        if zona[i + 1:i + 2] not in (" ", "\n"):
            continue      # el punto de `127.0.0.1` no va seguido de ningún espacio
        if zona[i - 1].isdigit():
            continue      # y un número suelto cerrado («3.») tampoco es una frase
        return zona[:i + 1], True
    hueco = max(zona.rfind(" "), zona.rfind("\n"))
    return (zona[:hueco] if hueco > 40 else zona), True


class Hilo:
    """La conversación de una llamada: su historial, su candado, su cuenta de vueltas."""

    def __init__(self, ident):
        self.ident = ident
        self.historial = deque(maxlen=HISTORIAL_MAX)
        self.candado = asyncio.Lock()
        self.vueltas = 0
        self.tocado = time.time()


class Canal:
    """Hace de conexión para el código del puente, pero sin WebSocket.

    `enviar(ws, datos)` busca la bandeja en `SALIDA[ws]`, así que basta con registrar
    una cola aquí. `closed` y `send_json` existen porque el redactor también los mira.
    """

    def __init__(self, hilo, SALIDA):
        self.hilo = hilo
        self.cola = []
        self.closed = False
        self.por_auricular = True   # la voz va en el cuerpo de la respuesta, no al altavoz
        self.auricular_texto = ""

    def __hash__(self):
        return id(self)

    async def send_json(self, datos):
        self.cola.append(datos)

    def vaciar(self, bandeja):
        try:
            while True:
                datos, _pausa = bandeja.get_nowait()
                self.cola.append(datos)
        except asyncio.QueueEmpty:
            pass


def _hilo_para(ident):
    _limpiar()
    if ident:
        h = HILOS.get(ident)
        if h is not None:
            return h
    nuevo = Hilo(ident or ("llamada-%d" % int(time.time() * 1000)))
    HILOS[nuevo.ident] = nuevo
    if len(HILOS) > 8:
        viejos = sorted(HILOS.values(), key=lambda h: h.tocado)[:-8]
        for h in viejos:
            HILOS.pop(h.ident, None)
    return nuevo


def _limpiar():
    ahora = time.time()
    for ident in [i for i, h in HILOS.items() if ahora - h.tocado > VIEJO_SEGUNDOS]:
        HILOS.pop(ident, None)


def _pcm_de_wav(bytes_wav):
    """Separa el PCM de su cabecera y dice la tasa: el teléfono reproduce crudos."""
    with wave.open(io.BytesIO(bytes_wav), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("la voz sintetizada no es mono de 16 bits")
        n = w.getnframes()
        return w.readframes(n), w.getframerate(), round(n / float(w.getframerate()), 2)


def _ultima_respuesta(cola):
    for datos in reversed(cola):
        if datos.get("type") == "jarvis_text":
            return (datos.get("text") or "").strip()
    return ""


def montar(app, llave, despacho, voz, transcribir, autorizada, SALIDA):
    """Registra las tres rutas en el core. `despacho` es `cort_server.atender_input`.

    El oído, la boca y el despacho entran por parámetro a propósito: así la suite
    prueba el contrato con un oído y una boca de mentira, sin cargarse el modelo de
    Vosk en los 228 MB libres de esta PC y sin tocar el micrófono de la dueña.
    """
    tmp = Path(getattr(voz, "TMP", "/tmp/cort-voz"))

    async def parlamento(request):
        if not autorizada(request.query.get("token"), llave):
            return web.json_response(
                {"ok": False, "origen": "no disponible",
                 "motivo": "sin llave no hay parlamento: el enlace pide ?token=…"}, status=401)
        cuerpo = await request.read()
        if len(cuerpo) < 44:
            return web.json_response({"ok": False, "origen": "no disponible",
                                      "motivo": "no llegó audio"})
        if cuerpo[:4] != b"RIFF" or cuerpo[8:12] != b"WAVE":
            return web.json_response({"ok": False, "origen": "no disponible",
                                      "motivo": "lo que subió el teléfono no es un WAV"})
        if len(cuerpo) > MAX_CUERPO:
            return web.json_response(
                {"ok": False, "origen": "no disponible",
                 "motivo": "la grabación pasa de %d MB: cuelga y habla más corto"
                           % (MAX_CUERPO // (1024 * 1024))})
        if transcribir is None or voz is None:
            return web.json_response(
                {"ok": False, "origen": "no disponible",
                 "motivo": "esta PC no tiene el oído (Vosk) o la boca cargados: "
                           "el parlamento contesta por texto cuando el puente los tiene"})

        h = _hilo_para(request.query.get("hilo", ""))
        canal = Canal(h, SALIDA)
        bandeja = asyncio.Queue(maxsize=512)
        SALIDA[canal] = bandeja
        grabacion = tmp / ("parlamento-%d.wav" % os.getpid())
        sintetizada = None
        t0 = time.time()
        try:
            tmp.mkdir(parents=True, exist_ok=True)
            grabacion.write_bytes(cuerpo)
            tf = time.time()
            esc = await asyncio.get_event_loop().run_in_executor(None, transcribir, grabacion)
            ms_escucha = int((time.time() - tf) * 1000)
            if not esc.get("ok"):
                return web.json_response({
                    "ok": False, "origen": esc.get("origen", "no disponible"),
                    "motivo": esc.get("motivo", "el oído no produjo texto"),
                    "ms_escucha": ms_escucha, "hilo": h.ident})
            oido = (esc.get("texto") or "").strip()
            if not oido:
                return web.json_response({
                    "ok": False, "origen": "real", "motivo": "no se entendió ninguna palabra",
                    "ms_escucha": ms_escucha, "hilo": h.ident,
                    "segundos_audio": esc.get("segundos_audio")})

            # Sin candado alrededor: `atender_input` toma el suyo nada más entrar, y
            # tomarlo dos veces en el mismo hilo es un abrazo que no se suelta.
            t1 = time.time()
            await despacho(canal, oido, h.historial, h.candado)
            canal.vaciar(bandeja)
            respuesta = _ultima_respuesta(canal.cola)
            h.vueltas += 1
            h.tocado = time.time()
            ms_respuesta = int((time.time() - t1) * 1000)

            audio_b64, tasa, segundos, ms_voz = "", 0, 0.0, 0
            recortado, dichos = False, 0
            if respuesta:
                t2 = time.time()
                try:
                    dicho, recortado = para_el_auricular(
                        canal.auricular_texto or respuesta)
                    dichos = len(dicho)
                    hecho = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: voz.hablar(dicho, reproducir=False))
                    sintetizada = (hecho or {}).get("archivo")
                    if sintetizada and os.path.isfile(sintetizada):
                        with open(sintetizada, "rb") as f:
                            pcm, tasa, segundos = _pcm_de_wav(f.read())
                        audio_b64 = base64.b64encode(pcm).decode("ascii")
                    elif hecho and not hecho.get("ok"):
                        print("[CORT] el parlamento no pudo sintetizar: %s"
                              % hecho.get("motivo"))
                except Exception as e:
                    print("[CORT] la voz del parlamento cayó (%s: %s)"
                          % (type(e).__name__, e))
                ms_voz = int((time.time() - t2) * 1000)

            return web.json_response({
                "ok": True, "origen": "real", "oido": oido, "respuesta": respuesta,
                "audio": audio_b64, "tasa": tasa, "segundos": segundos,
                "hilo": h.ident, "vueltas": h.vueltas, "ms_escucha": ms_escucha,
                "ms_respuesta": ms_respuesta, "ms_voz": ms_voz,
                "ms_total": int((time.time() - t0) * 1000),
                "motor_oido": esc.get("motor", "vosk"),
                "oido_en": "PC (Vosk)", "voz_en": "auricular del teléfono",
                "auricular_recortado": recortado,
                "caracteres_auricular": dichos,
            })
        except Exception as e:
            return web.json_response({"ok": False, "origen": "no disponible",
                                      "motivo": "el parlamento cayó (%s: %s)"
                                                % (type(e).__name__, e),
                                      "hilo": h.ident})
        finally:
            SALIDA.pop(canal, None)
            for ruta in (grabacion, sintetizada):
                if ruta:
                    try:
                        os.unlink(ruta)
                    except OSError:
                        pass
            _limpiar()

    async def estado(request):
        if not autorizada(request.query.get("token"), llave):
            return web.json_response({"ok": False, "motivo": "sin llave no hay estado"}, status=401)
        _limpiar()
        h = HILOS.get(request.query.get("hilo", ""))
        return web.json_response({
            "ok": True, "origen": "real", "llamadas": len(HILOS),
            "vueltas": h.vueltas if h else 0,
            "oido": transcribir.__name__ if transcribir else "sin oído",
            "boca": bool(voz),
            "topes": {"cuerpo_MB": MAX_CUERPO // (1024 * 1024),
                      "historial": HISTORIAL_MAX, "inactividad_s": VIEJO_SEGUNDOS,
                      "auricular_caracteres": AURICULAR_MAX_CARACTERES},
        })

    async def colgar(request):
        if not autorizada(request.query.get("token"), llave):
            return web.json_response({"ok": False, "motivo": "sin llave no hay colgada"}, status=401)
        ident = request.query.get("hilo", "")
        h = HILOS.pop(ident, None)
        return web.json_response({"ok": True, "origen": "real", "colgada": bool(h),
                                  "hilo": ident, "llamadas": len(HILOS)})

    app.router.add_post("/parlamento", parlamento)
    app.router.add_get("/parlamento", estado)
    app.router.add_post("/parlamento/colgar", colgar)
    return llave
