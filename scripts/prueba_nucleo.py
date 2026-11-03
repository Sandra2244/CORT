#!/usr/bin/env python3
"""CORT — el núcleo entero por el WebSocket, sin modelo y sin tocar la casa (F9).

Una corrida, tres cosas medidas:

1. Que la frase escrita/llegada por micrófono pasa por el compilador y el plan llega a
   la reja y al ejecutor (con `plan_resultado` en el canal y el archivo movido de verdad).
2. Que lo que el modelo sueña se frena en el puente, no sólo en la prueba unitaria.
3. Que una charla («hola buenos días») NO se convierte en orden: cae al chat normal.

El cerebro lo hace un Ollama simulado en 127.0.0.1 con un puerto al azar: contesta JSON
y anota en disco qué le pidieron, así se comprueba que el puente manda `format:"json"` y
`temperature:0` en vez de dejar que el modelo escriba prosa. Todo ocurre en una arena
(`CORT_HOME` en /tmp): ni un archivo de Sandra se mueve y la voz está apagada.

    python3 scripts/prueba_nucleo.py
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRIDGE = RAIZ / "cort-bridge"


def sin(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# ------------------------------------------------------------- el cerebro simulado ----
PLAN_POR_FRASE = {sin(k): v for k, v in {
    "mueve la carpeta proyectos a descargas":
        {"intencion": "mover_archivo", "argumentos": {"origen": "proyectos", "destino": "Descargas"},
         "necesita_confirmacion": False, "no_entendido": False},
    "qué hay en la carpeta proyectos":
        {"intencion": "listar_archivos", "argumentos": {"carpeta": "proyectos"},
         "necesita_confirmacion": False, "no_entendido": False},
    "investígame en google qué es la toxoplasmosis":
        {"intencion": "investigar", "argumentos": {"tema": "toxoplasmosis"},
         "necesita_confirmacion": False, "no_entendido": False},
    "borra la carpeta proyectos":
        {"intencion": "borrar_archivo", "argumentos": {"origen": "proyectos"},
         "necesita_confirmacion": True, "no_entendido": False},
    "mueve informe.txt a documentos":
        {"intencion": "mover_archivo", "argumentos": {"origen": "Descargas/informe.txt",
                                                     "destino": "Documentos"},
         "necesita_confirmacion": False, "no_entendido": False},
    "hola buenos días": {"intencion": "nada", "no_entendido": True, "argumentos": {}},
    "confirma": {"intencion": "nada", "no_entendido": True, "argumentos": {}},
}.items()}
PEDIDOS: list = []        # lo que el puente le mandó al cerebro


def make_handler():
    class H(BaseHTTPRequestHandler):
        def _responder(self, cuerpo: dict):
            dato = json.dumps(cuerpo).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dato)))
            self.end_headers()
            self.wfile.write(dato)

        def do_GET(self):
            if self.path == "/api/tags":
                self._responder({"models": [{"name": "arena-test:1b"}]})
            else:
                self._responder({})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            cuerpo = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/ps":
                # el modelo ya está en memoria: la puerta de RAM no debe cobrar la carga
                self._responder({"models": [{"name": "arena-test:1b"}]})
            elif self.path == "/api/generate":
                frase = cuerpo.get("prompt") or ""
                PEDIDOS.append({"endpoint": "generate", "format": cuerpo.get("format"),
                                "temperature": (cuerpo.get("options") or {}).get("temperature"),
                                "prompt": frase})
                # las claves de la tabla ya vienen normalizadas: si no, «qué» con
                # tilde no encuentra nada y el simulador devuelve «no entendí»
                plan = PLAN_POR_FRASE.get(sin(frase))
                if plan is None:
                    plan = {"intencion": "nada", "no_entendido": True, "argumentos": {}}
                self._responder({"response": json.dumps(plan, ensure_ascii=False), "done": True})
            elif self.path == "/api/chat":
                PEDIDOS.append({"endpoint": "chat",
                                "prompt": (cuerpo.get("messages") or [{}])[-1].get("content")})
                self._responder({"message": {"role": "assistant",
                                             "content": "Buenos días, Sandra. Todo en orden y en local."}})
            else:
                self._responder({})

        def log_message(self, *a):
            pass

    return H


def puerto_libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ------------------------------------------------------------------------- la arena ----
ARENA = Path(tempfile.mkdtemp(prefix="cort-nucleo-"))
for n in ("Documentos", "Descargas", "Escritorio", "Música"):
    (ARENA / n).mkdir()
(ARENA / "Documentos" / "proyectos").mkdir()
(ARENA / "Documentos" / "proyectos" / "notas.md").write_text("hola")
(ARENA / "Descargas" / "informe.txt").write_text("NUEVO")
(ARENA / "Documentos" / "informe.txt").write_text("VIEJO")

PORT_CEREBRO, PORT_WS, PORT_WEB = puerto_libre(), puerto_libre(), puerto_libre()
# de hilo por petición, como el Ollama real: si no, el lazo de medidas del puente
# (que también pregunta /api/tags y /api/ps) se cruza con la llamada del cerebro.
servidor = ThreadingHTTPServer(("127.0.0.1", PORT_CEREBRO), make_handler())
threading.Thread(target=servidor.serve_forever, daemon=True).start()

ENTORNO = {**os.environ,
           "CORT_HOME": str(ARENA), "CORT_DATOS": str(ARENA / ".local/share/cort"),
           "CORT_OLLAMA": f"http://127.0.0.1:{PORT_CEREBRO}",
           "CORT_WS_PORT": str(PORT_WS), "CORT_WEB_PORT": str(PORT_WEB),
           "CORT_VOZ": "0", "CORT_MIC": "0", "CORT_NUCLEO": "1",
           "PYTHONPATH": str(BRIDGE)}
puente = subprocess.Popen([sys.executable, "-u", str(BRIDGE / "cort_server.py")], env=ENTORNO,
                          stdout=open(ARENA / "puente.log", "w"), stderr=subprocess.STDOUT,
                          text=True)

CASOS = [
    # (frase, se espera en plan_resultado, efecto que hay que verificar en la arena)
    ("mueve la carpeta proyectos a descargas", True,
     lambda: (ARENA / "Descargas" / "proyectos").is_dir() and not (ARENA / "Documentos" / "proyectos").exists()),
    ("qué hay en la carpeta proyectos", True, lambda: True),
    ("borra la carpeta proyectos", False, lambda: (ARENA / "Descargas" / "proyectos").is_dir()),
    ("investígame en google qué es la toxoplasmosis", False, lambda: True),
    ("hola buenos días", None, lambda: True),          # charla: NUNCA debe dar plan_resultado
]


async def main():
    import websockets
    for _ in range(40):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT_WEB}/index.html", timeout=1).read()
            break
        except Exception:
            await asyncio.sleep(0.5)
    else:
        print("el puente de arena no levantó"); return 2

    fallos, vistos = [], []

    async def hablar(texto, espera_plan=True, segundos=25):
        """Un solo lector por conexión: si se ponen dos `recv()` sobre el mismo
        WebSocket, el colector muere antes de oír la respuesta y la prueba reporta
        fantasmas. Una pestaña nueva por frase, porque el turno anterior sigue hablando.
        """
        cola = []
        async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
            async def oir():
                try:
                    while True:
                        cola.append(json.loads(await w.recv()))
                except Exception:
                    return
            escucha = asyncio.create_task(oir())
            await asyncio.sleep(1.2)          # el puente saluda al conectar: saludo fuera
            marca = len(cola)
            await w.send(json.dumps({"type": "user_input", "text": texto}))
            busca = "plan_resultado" if espera_plan else "jarvis_text"
            limite = time.monotonic() + segundos
            while time.monotonic() < limite:
                if any(m.get("type") == busca for m in cola[marca:]):
                    break
                await asyncio.sleep(0.2)
            escucha.cancel()
        return cola[marca:]

    for frase, esperado, verificar in CASOS:
        cola = await hablar(frase, espera_plan=esperado is not None)
        plan = next((m for m in cola if m.get("type") == "plan_resultado"), None)
        charla = [m for m in cola if m.get("type") == "jarvis_text"]
        vistos.append((frase, plan, charla))
        if esperado is None:
            ok = plan is None and bool(charla)
            motivo = "charla: sin plan y con respuesta del chat" if ok else \
                ("hubo plan_resultado en una charla" if plan else "no llegó la respuesta del chat")
        elif plan is None:
            ok = False
            tipos = [m.get("type") or m.get("state") for m in cola][-14:]
            motivo = "no llegó plan_resultado; lo último del canal: " + ",".join(map(str, tipos))
        else:
            ok = (plan.get("valido") is esperado) and bool(verificar())
            motivo = "ok" if ok else f"valido={plan.get('valido')} (se pedía {esperado}) o el efecto no apareció"
        print(f"{'ok  ' if ok else 'FALLO'} {frase[:46]:<48} {motivo[:60]}")
        if not ok:
            fallos.append((frase, motivo, plan))

    # y la confirmación humana: el mismo plan, dicha dos veces
    cola = await hablar("mueve informe.txt a documentos", espera_plan=True)
    pidio = next((m for m in cola if m.get("type") == "plan_resultado"), None)
    rescate_esperado = pidio and pidio.get("valido") is False and "confirmaci" in (pidio.get("motivo") or "").lower()
    print(f"{'ok  ' if rescate_esperado else 'FALLO'} {'sobrescribir pide confirmación':<48} "
          f"{(pidio or {}).get('decir', '')[:60]}")
    if not rescate_esperado:
        fallos.append(("sobrescribir pide confirmación", "no frenó", pidio))
    cola2 = await hablar("confirma", espera_plan=True)
    ok2 = any(m.get("type") == "plan_resultado" and m.get("valido") for m in cola2) and \
        (ARENA / "Documentos" / "informe.txt").read_text() == "NUEVO"
    rescatados = sorted(q.name for q in (ARENA / "Documentos").glob("informe-cort-*"))
    print(f"{'ok  ' if ok2 else 'FALLO'} {'«confirma» ejecuta y rescata lo viejo':<48} "
          f"contenido={(ARENA/'Documentos'/'informe.txt').read_text()} rescate={rescatados}")
    if not ok2:
        fallos.append(("confirma", "no ejecutó o no rescató", cola2))

    print("\nlo que el puente le mandó al cerebro:")
    for p in PEDIDOS[:8]:
        extra = f" format={p.get('format')} temp={p.get('temperature')}" if p["endpoint"] == "generate" else ""
        print(f"  {p['endpoint']:<8} {str(p.get('prompt'))[:48]!r}{extra}")
    genera = [p for p in PEDIDOS if p["endpoint"] == "generate"]
    si_json = all(p.get("format") == "json" for p in genera) and all(p.get("temperature") == 0 for p in genera)
    print(f"{'ok  ' if si_json else 'FALLO'} todas las llamadas a /api/generate con format json y temperatura 0")
    if not si_json:
        fallos.append(("formato del pedido", "sin format/temperature", genera[:3]))

    casa_real = (Path.home() / "Documentos" / "proyectos").exists()
    print(f"\ncasa real intacta (~/Documentos/proyectos existe?): {casa_real} — debe ser False")
    if casa_real:
        fallos.append(("arena", "tocó la casa real", None))

    puente.terminate()
    try:
        puente.wait(timeout=5)
    except subprocess.TimeoutExpired:
        puente.kill()
    servidor.shutdown()
    if fallos:
        log = (ARENA / "puente.log").read_text()
        print("\nFALLOS:", json.dumps([f[0] for f in fallos], ensure_ascii=False))
        print(f"--- consola del puente (arena intacta en {ARENA}) ---")
        print(log[-3000:])
        return 1
    shutil.rmtree(ARENA, ignore_errors=True)
    print("\nTODO OK: frase -> plan -> reja -> ejecución verificada, y la charla sigue siendo charla.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        puente.kill()
        sys.exit(130)
