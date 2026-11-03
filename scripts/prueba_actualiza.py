#!/usr/bin/env python3
"""U1 — prueba del canal de actualización contra un GitHub falso.

Se comprueba lo que de verdad le importa a la usuaria: que avise sólo cuando la
etiqueta remota es más nueva, que diga el comando, y que cuando el repo no existe
o no tiene etiquetas lo diga con el motivo en vez de inventarse una versión.

    .venv/bin/python scripts/prueba_actualiza.py
"""
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cort-bridge"))
import cort_actualiza  # noqa: E402

RESPUESTAS = {}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        datos = RESPUESTAS.get(self.path, {"error": "no existe"})
        cuerpo = json.dumps(datos).encode()
        self.send_response(200 if "error" not in datos else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)


def main():
    arena = Path(tempfile.mkdtemp(prefix="cort-version-"))
    os.environ["CORT_ACTUALIZA_estado"] = str(arena / "estado.json")
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), H)
    puerto = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    api = f"http://127.0.0.1:{puerto}"

    casos = []

    def corre(repo, etiquetas, local, espera):
        os.environ["CORT_REPO"] = repo
        os.environ["CORT_API_GITHUB"] = api
        os.environ["CORT_VERSION"] = local
        RESPUESTAS[f"/repos/{repo}/tags"] = etiquetas
        r = cort_actualiza.registrar(cort_actualiza.consultar())
        if espera == "nueva":
            ok = r.get("hay_nueva") is True and r.get("remota") == "v0.10.0" and "git checkout v0.10.0" in r.get("como", "")
            motivo = "avisa y da el comando" if ok else f"contestó {r}"
        elif espera == "al-dia":
            ok = r.get("hay_nueva") is False and r.get("ok") is True
            motivo = "no molesta cuando no hay nada nuevo" if ok else f"contestó {r}"
        elif espera == "sin-etiquetas":
            ok = r.get("ok") is False and "ninguna etiqueta" in (r.get("motivo") or "")
            motivo = "dice que el repo aún no etiqueta" if ok else f"contestó {r}"
        else:  # mal-formado
            ok = r.get("origen") == "no disponible" and "no tiene forma válida" in (r.get("motivo") or "")
            motivo = "rechaza un nombre de repo imposible" if ok else f"contestó {r}"
        casos.append((espera, ok, motivo))
        return r

    tres = [{"name": n} for n in ("v0.9.0", "v0.10.0", "v0.8.1")]
    corre("pepe/cort", tres, "0.9.0", "nueva")
    corre("pepe/cort", [{"name": "v0.9.0"}], "0.9.0", "al-dia")
    corre("pepe/cort", [], "0.9.0", "sin-etiquetas")
    corre("..\\..\\etc", tres, "0.9.0", "mal")

    # El repo se deriva del remoto real de este proyecto, no de un valor fijo.
    os.environ.pop("CORT_REPO", None)
    os.environ.pop("CORT_VERSION", None)
    version, repo, _ = cort_actualiza.config()
    derivado = ("/" in repo and not repo.startswith(".")) if repo else False
    casos.append(("repo derivado del remoto", derivado, f"repo={repo or '(sin remoto)'} version={version}"))

    # Y que el registro quedó en disco, para que el aviso sobreviva al reinicio.
    guardado = cort_actualiza.ultimo() or {}
    casos.append(("registro en disco", bool(guardado.get("version_local")), str(guardado)[:60]))

    servidor.shutdown()
    for nombre, ok, motivo in casos:
        print(f"{'ok  ' if ok else 'FALLO'} {nombre:<20} {motivo[:70]}")
    fallos = [c for c in casos if not c[1]]
    print(f"\n{len(casos)} casos · fallos: {len(fallos)}")
    return 0 if not fallos else 1


if __name__ == "__main__":
    sys.exit(main())
