#!/usr/bin/env python3
"""S4 — la memoria, la constitución y la autocrítica, por el WebSocket y en arena.

Qué se comprueba, en el orden en que le pasa a Sandra:

1. Al conectar, CORT se presenta y propone algo con lo que ya está medido
   (`iniciativa`), y dice dónde guarda su memoria.
2. «recuerda que …» se escribe en el disco de la ARENA y se puede releer.
3. Lo recordado **entra en el prompt** del modelo: el Ollama simulado anota el
   system que recibió, y ahí tienen que estar la constitución y el apunte.
4. «no me digas X, dime Y» y «llámame …» se guardan como preferencias.
5. Una orden disfrazada de gusto («prefiero que cierres la ventana») NO se guarda.
6. El control previo a hablar limpia el markdown y tumba un «ya cerré la ventana»
   que ningún programa cerró (origen del modelo, no del sistema).

Todo ocurre con `CORT_HOME` en /tmp y la voz apagada: ni un archivo real de Sandra
se escribe, y el modelo es un simulador en 127.0.0.1 que registra lo que le pidieron.

    .venv/bin/python scripts/prueba_memoria.py
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRIDGE = RAIZ / "cort-bridge"
FALLOS: list = []
PEDIDOS: list = []          # lo que el puente le mandó al cerebro simulado


def sin(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def comprueba(nombre, ok, detalle=""):
    print(f"{'ok  ' if ok else 'FALLO'} {nombre}" + (f" — {str(detalle)[:90]}" if detalle else ""))
    if not ok:
        FALLOS.append((nombre, str(detalle)[:200]))
    return bool(ok)


# ------------------------------------------------------------- el cerebro simulado ----
RESPUESTA_MALA = ("- **Ya cerré la ventana** y la dejé lista.\n"
                  "- además copié el archivo en dos sitios")


def _respuesta_chat(user_content):
    """El simulador contesta mal a propósito en una frase: es la que prueba el control."""
    if "ventana" in sin(user_content) and "muestrame" in sin(user_content):
        return RESPUESTA_MALA
    return "Aquí tienes lo que pediste, corto y en español."


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
            self._responder({"models": [{"name": "arena-mem:1b"}]})
        else:
            self._responder({})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        cuerpo = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/api/ps":
            self._responder({"models": [{"name": "arena-mem:1b"}]})
        elif self.path == "/api/generate":
            PEDIDOS.append({"endpoint": "generate", "prompt": cuerpo.get("prompt") or ""})
            self._responder({"response": json.dumps(
                {"intencion": "nada", "no_entendido": True, "argumentos": {}}), "done": True})
        elif self.path == "/api/chat":
            msj = cuerpo.get("messages") or [{}]
            PEDIDOS.append({"endpoint": "chat",
                            "system": (msj[0] or {}).get("content") or "",
                            "prompt": (msj[-1] or {}).get("content") or ""})
            self._responder({"message": {"role": "assistant",
                                         "content": _respuesta_chat((msj[-1] or {}).get("content") or "")}})
        else:
            self._responder({})

    def log_message(self, *a):
        pass


def puerto_libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ------------------------------------------------------------------------- la arena ----
ARENA = Path(tempfile.mkdtemp(prefix="cort-memoria-"))
(ARENA / "modelos").mkdir()      # inventario de Ollama vacío: la arena no escanea su disco real
PORT_CEREBRO, PORT_WS, PORT_WEB = puerto_libre(), puerto_libre(), puerto_libre()
servidor = ThreadingHTTPServer(("127.0.0.1", PORT_CEREBRO), H)
threading.Thread(target=servidor.serve_forever, daemon=True).start()

ENTORNO = {**os.environ,
           "CORT_HOME": str(ARENA), "CORT_DATOS": str(ARENA / ".local/share/cort"),
           # El config del puente (modelo elegido, ciudad) también en la arena: si no,
           # un test leería el smollm2:135m que Sandra eligió de verdad y la puerta de
           # RAM lo tumbaría aquí, no por error de S4 sino por invadir su config.
           "CORT_STATE": str(ARENA / "cort_state.json"),
           "CORT_OLLAMA": f"http://127.0.0.1:{PORT_CEREBRO}",
           "CORT_WS_PORT": str(PORT_WS), "CORT_WEB_PORT": str(PORT_WEB),
           "CORT_VOZ": "0", "CORT_MIC": "0", "CORT_NUCLEO": "1", "CORT_PERFIL": "0",
           "PYTHONPATH": str(BRIDGE), "OLLAMA_MODELOS": str(ARENA / "modelos")}
puente = subprocess.Popen([sys.executable, "-u", str(BRIDGE / "cort_server.py")], env=ENTORNO,
                          stdout=open(ARENA / "puente.log", "w"), stderr=subprocess.STDOUT,
                          text=True)
MEMORIA = ARENA / ".local/share/cort/memoria.json"


async def oir_todo(w, seg):
    """Un lector por conexión: dos recv() sobre el mismo WebSocket matan el turno."""
    cola = []
    fin = time.time() + seg
    while time.time() < fin:
        try:
            cola.append(json.loads(await asyncio.wait_for(w.recv(), timeout=max(0.1, fin - time.time()))))
        except asyncio.TimeoutError:
            break
        except Exception:
            break
    return cola


async def main():
    import websockets
    for _ in range(40):
        try:
            socket.create_connection(("127.0.0.1", PORT_WS), 1).close()
            break
        except Exception:
            await asyncio.sleep(0.5)
    else:
        print("el puente de arena no levantó")
        print((ARENA / "puente.log").read_text()[-2000:])
        return 2

    # 1) al conectar: iniciativa y constitución
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        msgs = await oir_todo(w, 3.0)
    ini = next((m for m in msgs if m.get("type") == "iniciativa"), None)
    comprueba("el puente empuja `iniciativa` al conectar", ini is not None,
              [m.get("type") for m in msgs][:8])
    if ini:
        comprueba("el saludo sale con nombre y hora", bool(ini.get("saludo")), ini.get("saludo"))
        comprueba("dice dónde guarda la memoria", str(ini.get("memoria", {}).get("ruta", "")).startswith(str(ARENA)),
                  ini.get("memoria"))
        comprueba("la iniciativa viene con origen real", ini.get("origen") == "real")

    # 2) recordar de verdad
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        await w.send(json.dumps({"type": "user_input",
                                 "text": "recuerda que mi examen de suelo pelviano es el 12 de noviembre"}))
        msgs = await oir_todo(w, 4.0)
    dicho = next((m.get("text") for m in msgs if m.get("type") == "jarvis_text"), "")
    comprueba("«recuerda que…» contesta que guardó", "Guardado" in dicho, dicho[:80])
    comprueba("el apunte está en el disco de la arena",
              MEMORIA.exists() and "suelo pelviano" in MEMORIA.read_text(encoding="utf-8"))
    comprueba("la casa real de Sandra no se tocó",
              not (Path.home() / ".local/share/cort/memoria.json").exists() or
              "suelo pelviano" not in (Path.home() / ".local/share/cort/memoria.json").read_text(encoding="utf-8"))

    # 3) nombre y corrección
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        await w.send(json.dumps({"type": "user_input", "text": "llámame Askher"}))
        await oir_todo(w, 2.5)
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        await w.send(json.dumps({"type": "user_input", "text": "no me digas «usuario», dime «jefa»"}))
        msgs = await oir_todo(w, 2.5)
    txt = MEMORIA.read_text(encoding="utf-8")
    comprueba("el nombre quedó guardado", '"Askher"' in txt, json.loads(txt)["preferencias"])
    comprueba("la corrección quedó guardada", "jefa" in txt)

    # 4) una orden disfrazada NO se guarda como gusto
    hechos_antes = len(json.loads(txt)["hechos"])
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        await w.send(json.dumps({"type": "user_input", "text": "prefiero que cierres la ventana"}))
        await oir_todo(w, 6.0)
    despues = json.loads(MEMORIA.read_text(encoding="utf-8"))
    comprueba("la orden disfrazada no se guardó como gusto",
              len(despues["hechos"]) == hechos_antes and
              all("cierres" not in g for g in despues["preferencias"].get("gustos", [])),
              despues["preferencias"])

    # 5) la memoria y la constitución entran en el prompt del modelo
    PEDIDOS.clear()
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        await w.send(json.dumps({"type": "user_input", "text": "explícame en una frase cuándo toca el examen"}))
        await oir_todo(w, 8.0)
    chat = next((p for p in PEDIDOS if p["endpoint"] == "chat"), None)
    comprueba("hubo una llamada al cerebro", chat is not None, [p["endpoint"] for p in PEDIDOS])
    if chat:
        sysp = chat["system"]
        comprueba("la constitución va en el system", "PRINCIPIOS DE CORT" in sysp, len(sysp))
        comprueba("el apunte de la memoria va en el system", "suelo pelviano" in sysp, sysp[-160:])
        comprueba("el nombre guardado va en el system", "Askher" in sysp)
        comprueba("la corrección va en el system", "jefa" in sysp)

    # 6) la recuperación es dirigida: una pregunta que no tiene que ver NO arrastra
    #    el apunte (si siempre se pegara todo, la memoria sería ruido y comería tokens)
    PEDIDOS.clear()
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        await w.send(json.dumps({"type": "user_input", "text": "dime una receta rápida con arroz"}))
        await oir_todo(w, 8.0)
    chat2 = next((p for p in PEDIDOS if p["endpoint"] == "chat"), None)
    comprueba("una pregunta ajena no arrastra el apunte",
              chat2 is not None and "suelo pelviano" not in chat2["system"],
              (chat2 or {}).get("system", "")[-120:])

    # 7) la autocrítica: el modelo miente y el control lo frena antes de hablar
    PEDIDOS.clear()
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        await w.send(json.dumps({"type": "user_input", "text": "muéstrame la ventana"}))
        msgs = await oir_todo(w, 10.0)
    control = next((m for m in msgs if m.get("type") == "autocritica"), None)
    final = next((m.get("text") for m in msgs if m.get("type") == "jarvis_text"), "")
    comprueba("el control emitió su informe", control is not None,
              [m.get("type") for m in msgs][:10])
    comprueba("la respuesta hablada sale sin markdown", "*" not in final and "\n-" not in final, final[:90])
    comprueba("una promesa que nadie verificó se corrigió", "No puedo afirmar" in final, final[:120])

    # 8) «¿qué sabes de mí?» responde con lo suyo, no con humo
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        await w.send(json.dumps({"type": "user_input", "text": "¿qué sabes de mí?"}))
        msgs = await oir_todo(w, 5.0)
    dicho = next((m.get("text") for m in msgs if m.get("type") == "jarvis_text"), "")
    comprueba("resume lo guardado", "Askher" in dicho and "examen" in dicho, dicho[:110])

    # 9) orden de memoria suelta: estado por WebSocket
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        await w.send(json.dumps({"type": "memoria_estado", "text": "cuándo es el examen"}))
        msgs = await oir_todo(w, 3.0)
    est = next((m for m in msgs if m.get("type") == "memoria_estado"), None)
    comprueba("`memoria_estado` responde con origen real", est and est.get("origen") == "real",
              est and est.get("datos"))
    comprueba("el contexto de una pregunta llega listo",
              est and "suelo pelviano" in (est.get("contexto") or ""), est and est.get("contexto"))

    # 9b) el panel se abre sin escribir nada: ahí una búsqueda por vacío mostraría
    # «no sé nada» teniendo apuntes. Sin texto tiene que salir el resumen entero.
    async with websockets.connect(f"ws://127.0.0.1:{PORT_WS}/ws") as w:
        await w.send(json.dumps({"type": "memoria_estado"}))
        msgs = await oir_todo(w, 3.0)
    vacio = next((m for m in msgs if m.get("type") == "memoria_estado"), None)
    comprueba("abrir la tarjeta sin consulta muestra el resumen",
              vacio and "suelo pelviano" in (vacio.get("contexto") or ""),
              vacio and vacio.get("contexto"))

    puente.terminate()
    try:
        puente.wait(timeout=5)
    except subprocess.TimeoutExpired:
        puente.kill()
    servidor.shutdown()
    if FALLOS:
        print("\nFALLOS:", json.dumps([f[0] for f in FALLOS], ensure_ascii=False))
        print("--- consola del puente ---")
        print((ARENA / "puente.log").read_text()[-3000:])
        return 1
    print(f"\nTODO OK: memoria, constitución y control funcionando en {ARENA.name}")
    shutil.rmtree(ARENA, ignore_errors=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        puente.kill()
        sys.exit(130)
