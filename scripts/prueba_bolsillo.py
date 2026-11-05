#!/usr/bin/env python3
"""F17 — el bolsillo: qué le debe la PC a Sandra, leído desde el teléfono.

Levanta el puente **de verdad** en una arena (`CORT_HOME` en /tmp, puertos propios,
voz apagada), escribe pendientes en el disco de esa arena y baja `GET /bolsillo` con
`urllib`, que es lo que hará la aplicación. No se toca ningún archivo de la dueña.

Lo que se juega, en orden de gravedad:

* que la puerta sea la llave (401 dicho con palabras, como en el parlamento);
* que la llave **no viaje** dentro del cuadro —la regla 1 del enlace—;
* que lo pendiente salga con su tiempo real y ordenado del más cerca al más lejos;
* que los números de la máquina sean medidos (`origen: "real"`), no inventados;
* que los topes estén puestos: el teléfono no puede tragarse un archivo de notas.

Se corre con cualquier python (sólo pide la stdlib):

    python3 scripts/prueba_bolsillo.py

Sale con 0 si todo cuadra y con 1 si algo falta; cada línea está dicha en español.
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

LLAVE = "llave-de-arena-para-el-bolsillo"


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


def pide(url, timeout=6):
    """(código, dict) — un 401 con cuerpo JSON sigue siendo una respuesta legible."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def main():
    arena = Path(tempfile.mkdtemp(prefix="cort-bolsillo-"))
    datos = arena / ".local" / "share" / "cort"
    vida = datos / "vida"
    vida.mkdir(parents=True)
    PORT_WS, PORT_WEB = puerto_libre(), puerto_libre()

    # Dos pendientes y un vencido: el orden y la cuenta de vencidos son lo único que
    # el teléfono no puede deducir solo.
    ahora = time.time()
    (vida / "recordatorios.json").write_text(json.dumps({"items": [
        {"id": 1, "texto": "regar las plantas", "tipo": "recordatorio", "segundos": 3600,
         "para": round(ahora + 3600, 1), "en": "2026-11-04T18:00:00", "vencido": False},
        {"id": 2, "texto": "llamar a la mamá", "tipo": "recordatorio", "segundos": 600,
         "para": round(ahora + 600, 1), "en": "2026-11-04T17:00:00", "vencido": False},
        {"id": 3, "texto": "algo que ya pasó", "tipo": "recordatorio", "segundos": 60,
         "para": round(ahora - 120, 1), "en": "2026-11-04T16:00:00", "vencido": True},
    ]}, ensure_ascii=False), encoding="utf-8")
    (vida / "compras.json").write_text(json.dumps(
        {"items": ["pan", "café", "y" * 400]}), encoding="utf-8")
    (vida / "notas.json").write_text(json.dumps(
        {"suelo pelviano": {"content": "leer el capítulo 3", "hora": "2026-11-04T10:00:00"}}),
        encoding="utf-8")

    entorno = {**os.environ,
               "CORT_HOME": str(arena),
               "CORT_DATOS": str(datos),
               "CORT_STATE": str(arena / "cort_state.json"),
               "CORT_TMP": str(arena / "tmp-voz"),
               "CORT_WS_PORT": str(PORT_WS), "CORT_WEB_PORT": str(PORT_WEB),
               "CORT_TOKEN": LLAVE,
               "CORT_VOZ": "0", "CORT_MIC": "0", "CORT_NUCLEO": "0", "CORT_PERFIL": "0",
               "CORT_OLLAMA": "http://127.0.0.1:1",       # no hay cerebro en esta prueba
               "OLLAMA_MODELOS": str(arena / "modelos"),
               "PYTHONPATH": str(RAIZ / "cort-bridge")}
    log = arena / "puente.log"
    puente = subprocess.Popen([sys.executable, "-u", str(BRIDGE)], env=entorno, cwd=str(RAIZ),
                              stdout=open(log, "w", encoding="utf-8"), stderr=subprocess.STDOUT,
                              text=True)
    base = f"http://127.0.0.1:{PORT_WS}/bolsillo"
    try:
        limite = time.monotonic() + 40
        codigo = None
        while time.monotonic() < limite:
            if puente.poll() is not None:
                break
            try:
                codigo, _ = pide(base + f"?token={LLAVE}", timeout=2)
                if codigo == 200:
                    break
            except Exception:
                time.sleep(0.5)
        if codigo != 200:
            print("FALLO: el puente de arena no respondió a /bolsillo")
            print("\n".join(log.read_text(encoding="utf-8").splitlines()[-10:]))
            return 1

        print("\n== la puerta ==")
        sin_llave, cuerpo_sin = pide(base)
        comprueba("un GET sin ?token= es 401 con palabras", sin_llave == 401 and
                  "token" in str(cuerpo_sin.get("motivo", "")), f"{sin_llave} {cuerpo_sin}")
        malo, cuerpo_malo = pide(base + "?token=la-llave-de-otro")
        comprueba("la llave equivocada tampoco entra", malo == 401 and
                  cuerpo_malo.get("origen") == "no disponible", f"{malo} {cuerpo_malo}")
        comprueba("el 401 no dice cuál es la llave buena",
                  LLAVE not in json.dumps(cuerpo_malo, ensure_ascii=False))

        print("\n== lo pendiente, con su tiempo ==")
        _, cuadro = pide(base + f"?token={LLAVE}")
        pend = cuadro.get("pendientes", [])
        comprueba("la respuesta dice origen real", cuadro.get("ok") is True and
                  cuadro.get("origen") == "real", cuadro.get("origen"))
        comprueba("el cuadro no lleva la llave del enlace",
                  LLAVE not in json.dumps(cuadro, ensure_ascii=False))
        comprueba("están los dos pendientes y no el vencido", len(pend) == 2 and
                  {p["texto"] for p in pend} == {"regar las plantas", "llamar a la mamá"}, pend)
        comprueba("el más cerca sale primero", bool(pend) and
                  pend[0]["texto"] == "llamar a la mamá", [p["texto"] for p in pend])
        comprueba("cada uno trae sus minutos y su hora legible",
                  all(isinstance(p.get("minutos"), int) and p["minutos"] > 0 and
                      len(p.get("cuando", "")) == 11 and p["cuando"][2] == "/"
                      and p["cuando"][5] == " " and p["cuando"][8] == ":"
                      for p in pend), pend[:1])
        comprueba("el de una hora está a ~60 minutos", bool(pend) and
                  58 <= pend[-1]["minutos"] <= 62, pend[-1]["minutos"] if pend else None)
        comprueba("el vencido se cuenta, no se mezcla con los pendientes",
                  cuadro.get("vencidos") == 1, cuadro.get("vencidos"))

        print("\n== la lista, las notas y la máquina ==")
        comprueba("la lista de compras viaja recortada (tope de 200)",
                  "pan" in cuadro.get("compras", []) and
                  max(len(x) for x in cuadro["compras"]) <= 200,
                  [len(x) for x in cuadro.get("compras", [])])
        comprueba("las notas viajan por su título", cuadro.get("notas") == ["suelo pelviano"],
                  cuadro.get("notas"))
        m = cuadro.get("maquina", {})
        comprueba("la máquina se dice medida, no supuesta", m.get("origen") == "real", m)
        comprueba("los números de la máquina son de verdad",
                  isinstance(m.get("cpu"), (int, float)) and 0 <= m.get("cpu", -1) <= 100 and
                  m.get("ram_total_mb", 0) > 0 and m.get("ram_disponible_mb", -1) >= 0 and
                  m.get("nucleos", 0) >= 1 and m.get("despierto_s", 0) > 0, m)
        comprueba("el cuadro cabe en el teléfono (menos de 64 KB)",
                  len(json.dumps(cuadro, ensure_ascii=False).encode()) < 65536,
                  len(json.dumps(cuadro, ensure_ascii=False).encode()))

        print("\n== el tope de filas ==")
        muchos = [{"id": i, "texto": f"pendiente {i}", "tipo": "recordatorio", "segundos": 600,
                   "para": round(ahora + 600 + i, 1), "en": "x", "vencido": False}
                  for i in range(1, 61)]
        (vida / "recordatorios.json").write_text(json.dumps({"items": muchos}), encoding="utf-8")
        _, lleno = pide(base + f"?token={LLAVE}")
        comprueba("60 pendientes no bajan 60 filas: el tope son 40",
                  len(lleno.get("pendientes", [])) == 40, len(lleno.get("pendientes", [])))

        print("\n== sin vida diaria no se miente ==")
        fuente = (RAIZ / "cort-bridge" / "cort_server.py").read_text(encoding="utf-8")
        comprueba("el puente avisa cuando `cort_vida` no cargó en vez de devolver vacío feliz",
                  "la vida diaria no cargó en el puente" in fuente)
        comprueba("la ruta está montada en el puerto del core, junto al parlamento",
                  'add_get("/bolsillo"' in fuente and "PUERTO_WS" in fuente)

        print()
        if FALLOS:
            print(f"resultado: {len(FALLOS)} fallo(s) de {CONTADAS[0]} comprobaciones")
            return 1
        print("resultado: TODO OK")
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
