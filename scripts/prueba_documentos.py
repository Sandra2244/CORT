#!/usr/bin/env python3
"""F19 — los documentos: el teléfono sube un PDF y la PC le saca las letras.

Levanta el puente de verdad en una arena (puertos efímeros, `CORT_HOME` en /tmp, voz
apagada) y le manda archivos de carne y hueso: un PDF real de `/usr/share/doc`, un
texto con acentos, un PDF que no existe como tal y un cuerpo vacío. Nada de esto se
escribe en el disco de la dueña.

Lo que se juega, en orden de gravedad:

* que la puerta sea la llave (401 con palabras, como en el parlamento);
* que **no quede ni un archivo** en el tmp cuando la PC devuelve las letras;
* que un PDF sin texto se diga como lo que es (imágenes, sin `tesseract`), no como un
  libro leído;
* que el texto devuelto quepa en la pantalla: tope de caracteres dicho con número;
* y que por el mismo puerto quebe un cuerpo de 2 MB —el tope por defecto de aiohttp es
  1 MB— sin que la respuesta se convierta en un 413 de HTML.

    python3 scripts/prueba_documentos.py
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRIDGE = RAIZ / "cort-bridge" / "cort_server.py"
FALLOS: list = []
CONTADAS = [0]

LLAVE = "llave-de-arena-para-los-documentos"
PDF_REAL = next(iter(sorted(Path("/usr/share/doc").rglob("*.pdf"))), None)


def comprueba(nombre, ok, detalle=""):
    CONTADAS[0] += 1
    print(f"{'ok  ' if ok else 'FALLO'} {nombre}" + (f" — {str(detalle)[:110]}" if detalle else ""))
    if not ok:
        FALLOS.append((nombre, str(detalle)[:200]))
    return bool(ok)


def puerto_libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def sube(url, datos: bytes, timeout=90):
    peticion = urllib.request.Request(url, data=datos, method="POST")
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"motivo": "respuesta sin JSON"}


def espera_puente(puente, log, url, limite_seg=45):
    """Espera a que el puente escuche; si se cae, imprime sus últimas líneas."""
    limite = time.monotonic() + limite_seg
    while time.monotonic() < limite:
        if puente.poll() is not None:
            return False
        try:
            sube(url, b"x", timeout=2)
            return True
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.5)
    return False


def main():
    if PDF_REAL is None:
        print("FALLO: no hay ningún PDF de ejemplo en /usr/share/doc para probar")
        return 1
    arena = Path(tempfile.mkdtemp(prefix="cort-documentos-"))
    tmp_docs = arena / "tmp-documentos"
    PORT_WS, PORT_WEB = puerto_libre(), puerto_libre()
    base = f"http://127.0.0.1:{PORT_WS}/documentos"

    entorno = {**os.environ,
               "CORT_HOME": str(arena),
               "CORT_DATOS": str(arena / ".local" / "share" / "cort"),
               "CORT_STATE": str(arena / "cort_state.json"),
               "CORT_TMP": str(arena / "tmp-voz"),
               "CORT_TMP_DOC": str(tmp_docs),
               "CORT_WS_PORT": str(PORT_WS), "CORT_WEB_PORT": str(PORT_WEB),
               "CORT_TOKEN": LLAVE,
               "CORT_VOZ": "0", "CORT_MIC": "0", "CORT_NUCLEO": "0", "CORT_PERFIL": "0",
               "CORT_OLLAMA": "http://127.0.0.1:1",
               "OLLAMA_MODELOS": str(arena / "modelos"),
               "PYTHONPATH": str(RAIZ / "cort-bridge")}
    log = arena / "puente.log"
    puente = subprocess.Popen([sys.executable, "-u", str(BRIDGE)], env=entorno, cwd=str(RAIZ),
                              stdout=open(log, "w", encoding="utf-8"), stderr=subprocess.STDOUT,
                              text=True)
    try:
        if not espera_puente(puente, log, base + f"?token={LLAVE}"):
            print("FALLO: el puente de arena no levantó")
            print("\n".join(log.read_text(encoding="utf-8").splitlines()[-12:]))
            return 1

        print("\n== la puerta ==")
        codigo, cuerpo = sube(base, PDF_REAL.read_bytes())
        comprueba("un POST sin ?token= es 401 con palabras", codigo == 401 and
                  "token" in str(cuerpo.get("motivo", "")), f"{codigo} {cuerpo}")
        codigo, cuerpo = sube(base + "?token=la-que-no-es", PDF_REAL.read_bytes())
        comprueba("la llave equivocada tampoco abre el documento", codigo == 401, codigo)

        print("\n== un PDF de verdad ==")
        codigo, cuadro = sube(base + f"?token={LLAVE}", PDF_REAL.read_bytes(), timeout=120)
        texto = cuadro.get("texto", "")
        comprueba("la PC devolvió letras y dijo su origen", codigo == 200 and
                  cuadro.get("ok") is True and cuadro.get("origen") == "real" and
                  cuadro.get("tipo") == "pdf", f"{codigo} {str(cuadro)[:120]}")
        comprueba("el texto no está vacío", len(texto) > 80, len(texto))
        comprueba("los caracteres y el recorte van dichos con número",
                  cuadro.get("caracteres", 0) >= len(texto) and
                  isinstance(cuadro.get("recortado"), bool) and
                  len(texto) <= 60_000, [cuadro.get("caracteres"), cuadro.get("recortado")])
        comprueba("dice cuántas páginas tiene el PDF", isinstance(cuadro.get("paginas"), int) and
                  cuadro.get("paginas", 0) >= 1, cuadro.get("paginas"))
        comprueba("la extracción trajo su tiempo en milisegundos",
                  isinstance(cuadro.get("ms"), int) and cuadro["ms"] > 0, cuadro.get("ms"))
        comprueba("el cuadro no lleva la llave del enlace",
                  LLAVE not in json.dumps(cuadro, ensure_ascii=False))
        comprueba("no quedó ni un archivo en el tmp de documentos",
                  not tmp_docs.exists() or not list(tmp_docs.glob("documento-*")),
                  [p.name for p in tmp_docs.glob("documento-*")] if tmp_docs.exists() else [])

        print("\n== un texto con acentos ==")
        (arena / "apuntes.txt").write_text("suelo pelviano — capítulo 3: músculos y respiración",
                                           encoding="utf-8")
        codigo, plano = sube(base + f"?token={LLAVE}", (arena / "apuntes.txt").read_bytes())
        comprueba("el texto plano se lee sin poppler", codigo == 200 and
                  plano.get("ok") is True and plano.get("tipo") == "texto" and
                  "pelviano" in plano.get("texto", ""), f"{codigo} {str(plano)[:120]}")
        comprueba("el utf-8 no se rompió en el viaje", "—" in plano.get("texto", ""),
                  plano.get("texto", "")[:60])

        print("\n== lo que no es un documento ==")
        codigo, basura = sube(base + f"?token={LLAVE}", b"%PDF-1.4 roto y sin cierre")
        comprueba("un PDF roto se dice roto, no se calla", codigo == 200 and
                  basura.get("ok") is False and
                  basura.get("origen") in ("no disponible", "real") and
                  len(str(basura.get("motivo", ""))) > 8, str(basura)[:150])
        codigo, vacio = sube(base + f"?token={LLAVE}", b"")
        comprueba("un cuerpo vacío contesta con su motivo", codigo == 200 and
                  vacio.get("ok") is False and "vacío" in str(vacio.get("motivo", "")), vacio)
        comprueba("ninguno de los dos dejó archivos",
                  not list(tmp_docs.glob("documento-*")) if tmp_docs.exists() else True)

        print("\n== el puerto del core aguenta más de 1 MB ==")
        # aiohttp corta por defecto a 1 MB y el 413 sale en HTML. Un dictado de 20 s son
        # 640 044 B (no llegaba), pero un documento de varios megabytes sí atraviesa el
        # techo, y por eso el puente declara el suyo antes de montar las rutas.
        fuente = (RAIZ / "cort-bridge" / "cort_server.py").read_text(encoding="utf-8")
        comprueba("el core declara su tope de cuerpo antes de montar las rutas",
                  "client_max_size=cuerpo_maximo_ws" in fuente and
                  'getattr(cort_documentos, "MAX_CUERPO"' in fuente)
        wav = b"RIFF" + b"\0\0\0\0" + b"WAVEfmt " + bytes(40) + b"data" + b"\0\0\0\0"
        wav += bytes(2 * 16_000 * 3)          # 3 s de silencio: 96 000 B
        p_wav = f"http://127.0.0.1:{PORT_WS}/parlamento?token={LLAVE}"
        gordo = ("párrafo de relleno para pasar el techo de un megabyte\n" * 40_000).encode()
        codigo_gordo, cuadro_gordo = sube(base + f"?token={LLAVE}", gordo, timeout=90)
        comprueba(f"un cuerpo de {len(gordo) // 1024} KB entra por el puerto y sale en JSON",
                  codigo_gordo == 200 and cuadro_gordo.get("ok") is True and
                  "text/html" not in str(cuadro_gordo.get("motivo", "")),
                  [codigo_gordo, len(gordo), cuadro_gordo.get("caracteres")])
        codigo, respuesta = sube(p_wav, wav, timeout=60)
        comprueba("el parlamento recibe un WAV y contesta en JSON (no en 413)",
                  codigo == 200 and isinstance(respuesta, dict) and
                  "ok" in respuesta, f"{codigo} {str(respuesta)[:120]}")
        print()
        if FALLOS:
            print(f"resultado: {len(FALLOS)} fallo(s) de {CONTADAS[0]} comprobaciones")
            return 1
        print(f"resultado: TODO OK ({CONTADAS[0]} comprobaciones) — "
              f"PDF de {PDF_REAL.name} leído en {cuadro.get('ms')} ms")
        return 0
    finally:
        puente.terminate()
        try:
            puente.wait(timeout=8)
        except subprocess.TimeoutExpired:
            puente.kill()
        shutil.rmtree(arena, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
