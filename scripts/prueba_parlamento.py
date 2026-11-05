#!/usr/bin/env python3
"""F16 — el parlamento: el contrato entre el teléfono que habla y la PC que escucha.

No enciende ningún micrófono ni carga el modelo de Vosk: levanta el puente de mentira
en un puerto de arena, con un oído, una boca y un despacho falsos, y comprueba lo que
se rompe en silencio cuando el teléfono empieza a hablar.

Lo que se juega aquí, en orden de gravedad:

* que la puerta sea la llave (401 dicho con palabras, no un cascarón vacío);
* que lo que sube sea audio de verdad y quepa en el tope escrito;
* que la frase del teléfono entre por **el mismo despacho que el WebSocket** —si hay
  dos caminos de respuesta, uno miente—;
* que la voz vuelva como PCM con su tasa, para el auricular, y que la PC no suene;
* y que ningún WAV se quede en el disco: ni la grabación ni la voz sintetizada.

Se corre con el python del entorno del puente (necesita `aiohttp`):

    .venv/bin/python scripts/prueba_parlamento.py

Sale con 0 si todo cuadra y con 1 si algo falta; cada línea está dicha en español.
"""

import asyncio
import base64
import io
import os
import sys
import wave
from collections import deque
from pathlib import Path

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "cort-bridge"))

os.environ.setdefault("CORT_TMP", "/tmp/cort-voz-prueba")

import cort_enlace      # noqa: E402
import cort_parlamento  # noqa: E402

LLAVE = "llave-de-prueba-para-la-suite"
RESPUESTA = "respuesta para el auricular"
RESULTADOS = []


def prueba(nombre, ok, detalle=""):
    RESULTADOS.append((nombre, bool(ok), detalle))
    print("  [%s] %s%s" % ("ok  " if ok else "FAIL", nombre,
                           (" — " + str(detalle)) if detalle else ""))


def wav_bytes(segundos=1.0, tasa=16000):
    """Un WAV mono de 16 bits: lo que armaría el teléfono en memoria."""
    m = io.BytesIO()
    with wave.open(m, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(tasa)
        w.writeframes(b"\x00\x00" * int(tasa * segundos))
    return m.getvalue()


class Boca:
    """Voz de mentira: escribe un WAV de verdad en el tmp y dice dónde está."""

    def __init__(self, tmp):
        self.tmp = tmp
        self.llamadas = []

    def hablar(self, texto, reproducir=True):
        self.llamadas.append((texto, reproducir))
        ruta = self.tmp / ("decir-%d.wav" % (len(self.llamadas) * 1000))
        with wave.open(str(ruta), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(22050)
            w.writeframes(b"\x01\x02" * 2205)
        return {"ok": True, "archivo": str(ruta), "motor": "falso",
                "caracteres": len(texto)}


def montar_app(texto_oido="hola cort", falla_oido=False):
    """App con el parlamento montado sobre un oído, una boca y un despacho falsos."""
    tmp = Path(os.environ["CORT_TMP"])
    tmp.mkdir(parents=True, exist_ok=True)
    trazas = {"oido": [], "despacho": [], "boca": Boca(tmp)}

    def transcribir(ruta):
        trazas["oido"].append(Path(ruta))
        if falla_oido:
            return {"ok": False, "origen": "no disponible", "motivo": "no hay modelo"}
        return {"ok": True, "texto": texto_oido, "motor": "vosk-falso",
                "segundos_audio": 1.0}

    SALIDA = {}

    async def despacho(canal, texto, historial, candado):
        """Imita a `atender_input`: deja la respuesta en la bandeja y habla por el puente."""
        trazas["despacho"].append((texto, type(historial).__name__,
                                   type(candado).__name__, len(historial)))
        canal.auricular_texto = RESPUESTA
        SALIDA[canal].put_nowait(({"type": "jarvis_text", "text": RESPUESTA,
                                   "origen": "real"}, 0.0))
        historial.append({"role": "user", "content": texto})

    app = web.Application(client_max_size=6 * 1024 * 1024)
    cort_parlamento.montar(app, LLAVE, despacho=despacho, voz=trazas["boca"],
                           transcribir=transcribir, autorizada=cort_enlace.autorizada,
                           SALIDA=SALIDA)
    return app, trazas, SALIDA


async def llamar(sesion, base, ruta="/parlamento", cuerpo=None, metodo="POST",
                 hilo=None, token=LLAVE, sin_token=False):
    """`base` es la raiz que da TestServer, con su puerto de arena."""
    url = str(base).rstrip("/") + ruta
    params = {} if sin_token else {"token": token}
    if hilo:
        params["hilo"] = hilo
    if metodo == "POST":
        async with await sesion.post(url, params=params, data=cuerpo) as r:
            return r.status, await r.json()
    async with await sesion.get(url, params=params) as r:
        return r.status, await r.json()


def limpiar_tmp(tmp):
    if tmp.is_dir():
        for p in tmp.iterdir():
            try:
                p.unlink()
            except OSError:
                pass


def restos(tmp):
    return sorted(p.name for p in tmp.iterdir()) if tmp.is_dir() else []


async def correr():
    tmp = Path(os.environ["CORT_TMP"])
    limpiar_tmp(tmp)
    audio = wav_bytes()

    app, trazas, _ = montar_app()
    servidor = TestServer(app)
    await servidor.start_server()
    puerto = servidor.make_url("/")

    try:
        async with aiohttp.ClientSession() as sesion:
            print("\n== la puerta ==")
            estado, cuerpo = await llamar(sesion, puerto, cuerpo=audio, sin_token=True)
            prueba("el teléfono sin llave no abre la boca: 401", estado == 401,
                   "%s %s" % (estado, cuerpo.get("motivo", "")))
            prueba("y lo dice con palabras, no con un hueco",
                   "sin llave" in (cuerpo.get("motivo") or ""), cuerpo.get("motivo"))
            estado, _ = await llamar(sesion, puerto, metodo="GET", sin_token=True)
            prueba("el estado del hilo también pide llave", estado == 401)
            estado, _ = await llamar(sesion, puerto, ruta="/parlamento/colgar",
                                     cuerpo=b"", sin_token=True)
            prueba("y colgar también: una ruta abierta sería un micro siempre encendido",
                   estado == 401)

            print("\n== lo que sube el teléfono ==")
            estado, cuerpo = await llamar(sesion, puerto, cuerpo=b"no es audio")
            prueba("cuerpo corto: dice que no llegó audio",
                   "no llegó audio" in cuerpo.get("motivo", ""), cuerpo.get("motivo"))
            estado, cuerpo = await llamar(sesion, puerto,
                                          cuerpo=b"RIFF" + b"\0" * 4 + b"XXXX" + b"\0" * 40)
            prueba("si no es WAVE lo dice, en vez de transcribir basura",
                   "no es un WAV" in cuerpo.get("motivo", ""), cuerpo.get("motivo"))
            gordo = wav_bytes(1.0)[:44] + b"\0" * (cort_parlamento.MAX_CUERPO + 10)
            estado, cuerpo = await llamar(sesion, puerto, cuerpo=gordo)
            tope = str(cort_parlamento.MAX_CUERPO // (1024 * 1024))
            prueba("y si pasa del tope, lo dice con el número del tope",
                   tope in cuerpo.get("motivo", "") and "MB" in cuerpo.get("motivo", ""),
                   cuerpo.get("motivo"))
            prueba("el tope está escrito en el módulo, no en la cabeza de nadie",
                   cort_parlamento.MAX_CUERPO == 3 * 1024 * 1024 and
                   cort_parlamento.HISTORIAL_MAX == 40)

            print("\n== la vuelta de conversación ==")
            limpiar_tmp(tmp)
            estado, cuerpo = await llamar(sesion, puerto, cuerpo=audio)
            prueba("un turno feliz contesta 200 con `origen: real`",
                   estado == 200 and cuerpo.get("origen") == "real",
                   "%s %s" % (estado, cuerpo.get("motivo", "")))
            prueba("el oído es el de la PC y la voz se va al auricular",
                   cuerpo.get("oido_en") == "PC (Vosk)" and
                   cuerpo.get("voz_en") == "auricular del teléfono")
            prueba("la frase entra por el mismo despacho que el WebSocket",
                   len(trazas["despacho"]) == 1 and trazas["despacho"][0][0] == "hola cort",
                   trazas["despacho"][0] if trazas["despacho"] else "nadie llamó")
            prueba("y recibe el historial (deque) y el candado (Lock) de la llamada",
                   trazas["despacho"][0][1] == "deque" and
                   trazas["despacho"][0][2] == "Lock",
                   trazas["despacho"][0])
            modulo = (RAIZ / "cort-bridge" / "cort_parlamento.py").read_text(encoding="utf-8")
            prueba("no hay doble candado: el parlamento no toma el que ya toma `atender_input`",
                   "async with h.candado" not in modulo)
            prueba("la respuesta es la que salió del despacho, no un eco",
                   cuerpo.get("respuesta") == RESPUESTA, cuerpo.get("respuesta"))
            pcm = base64.b64decode(cuerpo.get("audio") or "")
            prueba("la voz vuelve como PCM sin cabecera, con su tasa y sus segundos",
                   cuerpo.get("tasa") == 22050 and len(pcm) == 4410 and
                   cuerpo.get("segundos") == 0.1,
                   "tasa=%s bytes=%s s=%s" % (cuerpo.get("tasa"), len(pcm),
                                              cuerpo.get("segundos")))
            prueba("y la boca de la PC no sonó por el altavoz: reproducir=False",
                   trazas["boca"].llamadas[-1] == (RESPUESTA, False),
                   trazas["boca"].llamadas[-1])

            print("\n== el audio no se queda en ninguna parte ==")
            prueba("en el tmp del puente no queda ni la grabación ni la voz sintetizada",
                   not any(n.startswith("parlamento-") or n.startswith("decir-")
                           for n in restos(tmp)), restos(tmp)[:6])
            h_id = cuerpo.get("hilo")
            estado, cuerpo2 = await llamar(sesion, puerto, cuerpo=audio, hilo=h_id)
            prueba("el mismo `hilo` sostiene la conversación: la segunda vuelta cuenta dos",
                   cuerpo2.get("vueltas") == 2 and cuerpo2.get("hilo") == h_id,
                   "%s %s" % (cuerpo2.get("vueltas"), cuerpo2.get("hilo")))
            prueba("y el despacho ve las dos frases de la dueña en el historial",
                   trazas["despacho"][1][3] == 1, trazas["despacho"][1])

            print("\n== el estado y la colgada ==")
            estado, cuerpo3 = await llamar(sesion, puerto, metodo="GET", hilo=h_id)
            prueba("GET /parlamento dice vueltas y topes por escrito",
                   estado == 200 and cuerpo3.get("vueltas") == 2 and
                   cuerpo3.get("topes", {}).get("cuerpo_MB") == 3, cuerpo3.get("topes"))
            estado, cuerpo4 = await llamar(sesion, puerto, ruta="/parlamento/colgar",
                                           cuerpo=b"", hilo=h_id)
            prueba("POST /parlamento/colgar suelta el hilo",
                   estado == 200 and cuerpo4.get("colgada") is True)
            estado, cuerpo5 = await llamar(sesion, puerto, metodo="GET", hilo=h_id)
            prueba("y colgada la llamada, la conversación empieza de cero",
                   cuerpo5.get("vueltas") == 0, cuerpo5.get("vueltas"))

        print("\n== cuando el oído falla ==")
        app2, trazas2, _ = montar_app(falla_oido=True)
        servidor2 = TestServer(app2)
        await servidor2.start_server()
        async with aiohttp.ClientSession() as sesion2:
            estado, cuerpo6 = await llamar(sesion2, servidor2.make_url("/"), cuerpo=audio)
            prueba("si Vosk dice que no, el teléfono recibe `no disponible` con el motivo",
                   estado == 200 and cuerpo6.get("origen") == "no disponible" and
                   "no hay modelo" in cuerpo6.get("motivo", ""), cuerpo6)
            prueba("y no se llamó al despacho: no se inventa una respuesta sin oír",
                   not trazas2["despacho"])
            prueba("aunque falle, la grabación no se queda en el disco",
                   not any(n.startswith("parlamento-") for n in restos(tmp)),
                   restos(tmp)[:6])
        await servidor2.close()

        app3, _, _ = montar_app(texto_oido="   ")
        servidor3 = TestServer(app3)
        await servidor3.start_server()
        async with aiohttp.ClientSession() as sesion3:
            estado, cuerpo7 = await llamar(sesion3, servidor3.make_url("/"), cuerpo=audio)
            prueba("audio que no dice palabras: `no se entendió ninguna palabra`, no un silencio",
                   "no se entendió" in cuerpo7.get("motivo", ""), cuerpo7.get("motivo"))
        await servidor3.close()

        print("\n== la integración con el puente de verdad ==")
        server = (RAIZ / "cort-bridge" / "cort_server.py").read_text(encoding="utf-8")
        prueba("el server importa y monta el parlamento con su propio despacho",
               "import cort_parlamento" in server and "despacho=atender_input" in server)
        prueba("le pasa la SALIDA real, la llave del enlace y el oído de la PC",
               "SALIDA=SALIDA" in server and "autorizada=cort_enlace.autorizada" in server
               and "transcribir=cort_voz.transcribir_wav" in server)
        paso = server[server.index("async def hablar_por_el_puente"):]
        prueba("la voz del puente se desvía al auricular cuando pregunta el teléfono",
               'getattr(ws, "por_auricular"' in paso[:900] and
               "ws.auricular_texto = texto" in paso[:900])
        prueba("el canal del teléfono se anuncia como auricular",
               "self.por_auricular = True" in modulo)
        prueba("la puerta se apoya en la misma comparación de tiempo constante del enlace",
               "cort_enlace.autorizada" in server and
               "autorizada(request.query.get(\"token\"), llave)" in modulo)
    finally:
        await servidor.close()


def main():
    asyncio.run(correr())
    totales = len(RESULTADOS)
    buenos = sum(1 for _, ok, _ in RESULTADOS if ok)
    print("\nresultado: %d/%d comprobaciones" % (buenos, totales))
    if buenos != totales:
        print("sin pasar:")
        for nombre, ok, detalle in RESULTADOS:
            if not ok:
                print("  - %s%s" % (nombre, (" (%s)" % detalle) if detalle else ""))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
