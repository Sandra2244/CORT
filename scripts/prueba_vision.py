#!/usr/bin/env python3
"""S2 — la mirada: cuadros fingidos → gesto → ventana real movida.

Tres tramos, cada uno con su prueba:

1. un **worker falso** (un guion que escribe cuadros YUY2 sintéticos por stdout)
   dentro de `Mirada`: así se prueba el hilo de lectura, el recorte de cuadros y el
   disparo del gesto sin pedirle la cámara a nadie;
2. el **mapeo** gesto → orden, comprobado contra la lista real de acciones;
3. dos **ventanas de prueba** abiertas por esta prueba (xfce4-terminal con nombre
   propio) y cerradas al final: `cambiar_ventana` tiene que mover el foco de una a
   otra y `maximizar` tiene que dejar el estado `_NET_WM_STATE` en xprop.

No se toca ninguna ventana que no haya abierto esta prueba.

    .venv/bin/python scripts/prueba_vision.py
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cort-bridge"))
import cort_vision    # noqa: E402
import cort_acciones  # noqa: E402

ANCHO, ALTO = cort_vision.ANCHO, cort_vision.ALTO
RESULTADOS = []


def comprueba(nombre, ok, detalle=""):
    RESULTADOS.append((nombre, bool(ok), str(detalle)[:78]))
    return bool(ok)


WORKER_FALSO = r'''
import sys, time
# argv: [guion, "captura", dispositivo, ancho, alto, fps] — los mismos que usa el puente
ANCHO = int(sys.argv[3]) if len(sys.argv) > 3 else 320
ALTO = int(sys.argv[4]) if len(sys.argv) > 4 else 240
R = 22
def cuadro(cx, cy):
    plano = bytearray(b"\x5a\x80\x5a\x80" * (ALTO * (ANCHO // 2)))
    x = int(cx * (ANCHO // 2)); y = int(cy * ALTO)
    for fila in range(max(0, y - R), min(ALTO, y + R)):
        base = fila * (ANCHO // 2) * 4
        for col in range(max(0, x - R // 2), min(ANCHO // 2, x + R // 2)):
            i = base + col * 4
            plano[i] = plano[i + 2] = 150
            plano[i + 1] = 128 - 30
            plano[i + 3] = 128 + 25
    return bytes(plano)
# un barrido de izquierda a derecha, cuadro a cuadro, a 10 fps
for i in range(26):
    sys.stdout.buffer.write(cuadro(0.12 + (i % 13) * 0.06, 0.5))
    sys.stdout.buffer.flush()
    time.sleep(0.1)
'''


def tramo_worker():
    arena = Path(tempfile.mkdtemp(prefix="cort-vision-"))
    guion = arena / "worker_falso.py"
    guion.write_text(WORKER_FALSO, encoding="utf-8")
    os.environ["CORT_VISION_WORKER"] = str(guion)
    os.environ["CORT_PYTHON_GST"] = sys.executable      # el venv basta: no hay GStreamer de por medio

    vistos = []
    avisos = []
    m = cort_vision.Mirada(dispositivo=str(guion), fps=10,
                           al_gesto=lambda g: vistos.append(g),
                           al_estado=lambda e: avisos.append(e))
    r = m.arrancar()
    comprueba("el worker arranca con un conducto falso", r.get("ok"), r.get("motivo"))
    t0 = time.time()
    while time.time() - t0 < 5 and not vistos:
        time.sleep(0.2)
    estado = m.estado()
    m.apagar()
    comprueba("llegan cuadros por el conducto", estado["cuadros"] >= 6,
              f"{estado['cuadros']} cuadros · cálculo {estado['ms_calculo']} ms · "
              f"intervalo {estado['ms_por_cuadro']} ms")
    comprueba("el barrido se reconoce solo", any(v["gesto"] == "barrido_derecha" for v in vistos),
              vistos[0]["por"] if vistos else "ningún gesto")

    # Y el camino inverso: un worker que no da un solo cuadro tiene que decirse solo,
    # sin que nadie tenga que preguntar. Es el fallo que la cámara real dio a los
    # 6 s la primera vez que se probó S2 (framerate clavado → la tubería en failure).
    muerta = arena / "worker_muerto.py"
    muerta.write_text("import sys\nsys.exit(2)\n", encoding="utf-8")
    os.environ["CORT_VISION_WORKER"] = str(muerta)
    m2 = cort_vision.Mirada(dispositivo=str(muerta), al_estado=lambda e: avisos.append(e))
    m2.arrancar()
    t0 = time.time()
    while time.time() - t0 < 5 and not avisos:
        time.sleep(0.2)
    m2.apagar()
    comprueba("sin cuadros lo avisa sin que se le pregunte",
              bool(avisos) and not avisos[-1]["mirando"] and "sin dar cuadros" in avisos[-1]["motivo"],
              avisos[-1]["motivo"] if avisos else "ningún aviso")
    # y lo contrario: una escena QUIETA con un bulto de piel grande y centrado arriba
    # (la usuaria sentada delante de la cámara, medida: área 15 %, y 0,28, mov 0,0000)
    # no tiene derecho a disparar ni un gesto. Con la regla vieja disparaba ocho en
    # ocho segundos y cada uno maximizaba una ventana.
    quieta = arena / "worker_quieto.py"
    quieta.write_text(WORKER_FALSO.replace(
        "for i in range(26):\n    sys.stdout.buffer.write(cuadro(0.12 + (i % 13) * 0.06, 0.5))",
        "for i in range(75):\n    sys.stdout.buffer.write(cuadro(0.53, 0.28))").replace(
        "R = 22", "R = 60"), encoding="utf-8")
    os.environ["CORT_VISION_WORKER"] = str(quieta)
    vistos_q = []
    m3 = cort_vision.Mirada(dispositivo=str(quieta), fps=15,
                             al_gesto=lambda g: vistos_q.append(g))
    m3.arrancar()
    time.sleep(5.0)
    e3 = m3.estado()
    m3.apagar()
    comprueba("una persona quieta no dispara gestos", not vistos_q and e3["cuadros"] >= 15,
              f"{len(vistos_q)} gestos con {e3['cuadros']} cuadros" +
              (f" · {vistos_q[0]['gesto']}" if vistos_q else ""))
    os.environ.pop("CORT_VISION_WORKER", None)


def tramo_mapeo():
    desconocidas = [nombre for nombre, _ in cort_vision.GESTO_A_ACCION.values()
                    if nombre not in ("cambiar_ventana", "maximizar", "minimizar_activa", "restaurar")]
    comprueba("todo gesto tiene orden conocida", not desconocidas, desconocidas)
    # con una sola ventana no hay a dónde cambiar: se dice, no se mueve otra cosa
    if len(cort_acciones.ventanas()) < 2:
        r = cort_acciones.cambiar_ventana("siguiente")
        comprueba("sin dos ventanas se niega", not r.get("ok"), r.get("detalle"))


def tramo_ventanas():
    nombre = "cort-prueba-s2"
    procesos = []
    ids = []
    for i in range(2):
        p = subprocess.Popen(["xfce4-terminal", "--geometry=220x120", f"--title={nombre}-{i}"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procesos.append(p)
    t0 = time.time()
    while time.time() - t0 < 12 and len(ids) < 2:
        time.sleep(0.5)
        ids = [w["id"] for w in cort_acciones.ventanas() if nombre in w["titulo"]]
    comprueba("dos ventanas de prueba abiertas", len(ids) == 2, f"ids {ids}")
    if len(ids) != 2:
        for p in procesos:
            p.terminate()
        return
    try:
        antes = cort_acciones.ventana_activa()
        subprocess.run(["wmctrl", "-i", "-a", ids[0]], capture_output=True)
        time.sleep(0.6)
        activa = cort_acciones.ventana_activa()
        comprueba("la ventana activa se puede leer", activa == ids[0], f"{activa} vs {ids[0]}")
        r = cort_acciones.cambiar_ventana("siguiente")
        time.sleep(0.6)
        despues = cort_acciones.ventana_activa()
        comprueba("barrido → foco en la otra ventana",
                  r.get("ok") and despues == ids[1], f"{despues} esperado {ids[1]}")
        r2 = cort_acciones.accion_sobre_activa("maximizar")
        time.sleep(0.8)
        x = subprocess.run(["xprop", "-id", ids[1], "_NET_WM_STATE"],
                           capture_output=True, text=True).stdout
        comprueba("palma → la ventana queda maximizada",
                  r2.get("ok") and "MAXIMIZED_VERT" in x, x.strip()[:70])
        r3 = cort_acciones.accion_sobre_activa("restaurar")
        time.sleep(0.6)
        x2 = subprocess.run(["xprop", "-id", ids[1], "_NET_WM_STATE"],
                            capture_output=True, text=True).stdout
        comprueba("empujar → vuelve a su tamaño",
                  r3.get("ok") and "MAXIMIZED_VERT" not in x2, x2.strip()[:60])
    finally:
        for vid in ids:
            subprocess.run(["wmctrl", "-i", "-c", vid], capture_output=True)
        for p in procesos:
            p.terminate()
        time.sleep(1.0)
        restantes = [w for w in cort_acciones.ventanas() if nombre in w["titulo"]]
        comprueba("la prueba no deja ventanas detrás", not restantes, f"quedan {len(restantes)}")


def main():
    t0 = time.time()
    tramo_worker()
    tramo_mapeo()
    tramo_ventanas()
    for nombre, ok, detalle in RESULTADOS:
        print(f"{'ok  ' if ok else 'FALLO'} {nombre:<38} {detalle}")
    fallos = [r for r in RESULTADOS if not r[1]]
    print(f"\n{len(RESULTADOS)} casos · fallos: {len(fallos)} · {time.time() - t0:.1f} s")
    return 0 if not fallos else 1


if __name__ == "__main__":
    sys.exit(main())
