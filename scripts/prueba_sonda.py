#!/usr/bin/env python3
"""M2 — prueba de la auto-sonda: CORT se mide sola cuando la RAM lo permite.

Levanta un Ollama falso (con un modelo de 1 MB en un disco de arena), arranca el
puente con CORT_AUTOSONDA=1 y mira si escribe `medicion-cerebro.json` con el
número real de milisegundos. No se le pide ninguna orden al equipo: la sonda sólo
pregunta y mide.

    .venv/bin/python scripts/prueba_sonda.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRIDGE = RAIZ / "cort-bridge" / "cort_server.py"

PLAN = {"intencion": "mover_archivo",
        "argumentos": {"origen": "proyectos", "destino": "Documentos"},
        "necesita_confirmacion": False, "no_entendido": False}


def make_handler(state):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _dicta(self, cuerpo):
            datos = json.dumps(cuerpo).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def do_GET(self):
            if self.path == "/api/tags":
                self._dicta({"models": [{"name": "mini:1m"}]})
            else:
                self._dicta({})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            cuerpo = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/generate":
                state["llamadas"].append({"model": cuerpo.get("model"),
                                          "format": cuerpo.get("format"),
                                          "options": cuerpo.get("options")})
                self._dicta({"response": json.dumps(PLAN), "eval_count": 42})
            elif self.path == "/api/ps":
                self._dicta({"models": []})
            else:
                self._dicta({})
    return H


def main():
    arena = Path(tempfile.mkdtemp(prefix="cort-sonda-"))
    mediciones = arena / "mediciones"
    modelos = arena / "ollama"
    (modelos / "manifests" / "registry" / "ollama" / "mini").mkdir(parents=True)
    (modelos / "blobs").mkdir(parents=True)
    (modelos / "blobs" / "sha256-mini").write_bytes(b"x" * (1024 * 1024))
    (modelos / "manifests" / "registry" / "ollama" / "mini" / "1m").write_text(
        json.dumps({"layers": [{"digest": "sha256:mini"}]}))

    estado = {"llamadas": []}
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(estado))
    puerto = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    env = {**os.environ,
           "CORT_HOME": str(arena),
           "CORT_DATOS": str(arena / "datos"),
           # el config del puente (modelo, ciudad) también en la arena: sin esto la
           # sonda escribe en cort-bridge/cort_state.json, que es el archivo vivo
           "CORT_STATE": str(arena / "cort_state.json"),
           "CORT_WS_PORT": "8798", "CORT_WEB_PORT": "8799",
           "CORT_VOZ": "0", "CORT_NUCLEO": "1",
           "CORT_OLLAMA": f"http://127.0.0.1:{puerto}",
           "OLLAMA_MODELOS": str(modelos),
           "CORT_AUTOSONDA": "1",
           "CORT_AUTOSONDA_UMBRAL": "1",          # la ventana de RAM siempre está abierta aquí
           "CORT_AUTOSONDA_CICLO": "2",
           "CORT_AUTOSONDA_REPITA": "0",
           "CORT_MEDICIONES": str(mediciones)}
    (arena / "datos").mkdir(parents=True)
    puente = subprocess.Popen([sys.executable, "-u", str(BRIDGE)], env=env,
                              cwd=str(RAIZ),
                              stdout=open(arena / "puente.log", "w", encoding="utf-8"),
                              stderr=subprocess.STDOUT, text=True)
    archivo = mediciones / "medicion-cerebro.json"
    mediciones.mkdir(parents=True, exist_ok=True)
    ok = False
    porton_de_s1 = False
    try:
        limite = time.monotonic() + 45
        while time.monotonic() < limite:
            if archivo.exists():
                break
            if puente.poll() is not None:
                break
            time.sleep(1)
        contenido = json.loads(archivo.read_text()) if archivo.exists() else None
        if contenido:
            llamada = estado["llamadas"][-1] if estado["llamadas"] else {}
            ok = (contenido.get("ok") is True and contenido.get("ms", 0) > 0 and
                  contenido.get("valido") is True and
                  llamada.get("format") == "json" and
                  (llamada.get("options") or {}).get("temperature") == 0)
            print(f"medición: {contenido.get('modelo')} respondió en {contenido.get('ms')} ms "
                  f"({contenido.get('tok_s')} tok/s) · reja: "
                  f"{'acepta' if contenido.get('valido') else 'rechaza'}")
            print(f"petición al modelo: format={llamada.get('format')} "
                  f"temperature={(llamada.get('options') or {}).get('temperature')}")
            print(f"segunda vuelta: la sonda ya no se repite -> "
                  f"{'sigue habiendo un solo archivo' if len(list(mediciones.glob('*.json'))) == 1 else 'se duplicó'}")
        else:
            lineas = (arena / "puente.log").read_text(encoding="utf-8").splitlines()
            porton = [l for l in lineas if "auto-sonda parada sin probar" in l]
            if porton:
                # S1 antes de gastar el disparo: sin AVX ningún binario de llama.cpp
                # corre aquí, y parar con el motivo medido vale más que insistir. En
                # esta máquina (Atom sin AVX, medido) la prueba no puede más que
                # pasar por ese portón; decirlo con su línea evita que el rojo
                # permanente tape un fallo de verdad.
                print(porton[-1])
                print("la sonda no disparó porque el chip no trae AVX: portón de S1, no avería")
                ok = porton_de_s1 = True
            else:
                print("FALLO: no apareció la medición.")
                print("\n".join(lineas[-8:]))
    finally:
        puente.terminate()
        try:
            puente.wait(5)
        except subprocess.TimeoutExpired:
            puente.kill()
        servidor.shutdown()
        shutil.rmtree(arena, ignore_errors=True)
    print("\nTODO OK: CORT se midió sola y guardó el número." if ok and not porton_de_s1 else
          ("\nSIN DISPARO: el portón de S1 frenó la sonda antes de gastar el intento."
           if porton_de_s1 else "\nHAY FALLOS."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
