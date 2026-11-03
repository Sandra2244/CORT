#!/usr/bin/env python3
"""F10 — la palabra de despertar, probada sin micrófono y sin esperar segundos reales.

`filtro_wake` recibe el reloj como argumento justamente para esto: se comprueba la
ventana de escucha con tiempos fingidos. Nada de este archivo enciende el micro.

    .venv/bin/python scripts/prueba_wake.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cort-bridge"))
import cort_server as cs  # noqa: E402

VENTANA = cs.VENTANA_WAKE
casos = []


def comprueba(nombre, texto, despierto_hasta, ahora, esperado):
    d = cs.filtro_wake(texto, despierto_hasta, ahora)
    visto = {k: d[k] for k in esperado}
    ok = visto == esperado
    casos.append((nombre, ok, f"{visto}" if not ok else
                  (f"«{d['texto']}»" if d["texto"] else "(sin resto)")))


comprueba("nombre + orden", "cort mueve la carpeta proyectos", 0.0, 100.0,
          {"atender": True, "texto": "mueve la carpeta proyectos",
           "dijo_nombre": True, "descartado": False})

comprueba("sólo el nombre", "cort", 0.0, 100.0,
          {"atender": False, "texto": "", "dijo_nombre": True, "descartado": False})

comprueba("dentro de la ventana", "qué hora es", 100.0 + VENTANA, 103.0,
          {"atender": True, "texto": "qué hora es",
           "dijo_nombre": False, "descartado": False})

comprueba("fuera de la ventana", "qué hora es", 100.0 + VENTANA, 120.0,
          {"atender": False, "texto": "qué hora es",
           "dijo_nombre": False, "descartado": True})

comprueba("una palabra parecida no despierta", "el cortador de jamón está en el cajón",
          0.0, 100.0, {"atender": False, "texto": "el cortador de jamón está en el cajón",
                       "dijo_nombre": False, "descartado": True})

for variante in ("coat", "cot", "court", "cord", "cortt"):
    comprueba(f"oído como {variante}", f"{variante} abre fotos", 0.0, 100.0,
              {"atender": True, "texto": "abre fotos",
               "dijo_nombre": True, "descartado": False})

d = cs.filtro_wake("cort", 0.0, 500.0)
casos.append(("la ventana se renueva",
              d["despierto_hasta"] == 500.0 + VENTANA, f"{d['despierto_hasta']} s de escucha"))

for nombre, ok, detalle in casos:
    print(f"{'ok  ' if ok else 'FALLO'} {nombre:<26} {detalle[:60]}")
fallos = [c for c in casos if not c[1]]
print(f"\n{len(casos)} casos · fallos: {len(fallos)}")
sys.exit(0 if not fallos else 1)
