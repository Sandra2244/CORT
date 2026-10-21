"""Prueba de la mudanza de los datos: las claves y las notas ya no viven dentro
del programa, así que actualizar el instalador no se las lleva puestas.

Corre en un sandbox (`mktemp` + `CORT_HOME`) y **no toca** su `~/.cort` real, ni
su `backend/cort_config.json`, ni su `cort_memory.db`.

Uso:  python3 scripts/prueba-datos.py     (una fracción de segundo)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SANDBOX = Path(tempfile.mkdtemp(prefix="cort-datos-"))
BACKEND = RAIZ / "backend"

# Se simula el peor caso: la dueña tiene sus archivos viejos dentro de `backend/`
# (donde vivían), que es exactamente lo que un instalador nuevo sustituye.
FAKE_BACKEND = SANDBOX / "app" / "backend"
FAKE_BACKEND.mkdir(parents=True)
CLAVES = {"groq_key": "gsk_FAKETEST", "mode": "online"}
(FAKE_BACKEND / "cort_config.json").write_text(json.dumps(CLAVES), encoding="utf-8")

# La base de datos vieja: se copia la estructura real creando una nueva con una
# nota, para no leer nunca la suya de verdad.
NUEVO = SANDBOX / "datos"
env = dict(os.environ, CORT_HOME=str(NUEVO))

FAKE_OLD = SANDBOX / "sin-nada"
FAKE_OLD.mkdir(parents=True)

# 1 · el módulo resuelve la carpeta personal (en un proceso aparte: así el
#     `CORT_HOME` se lee de verdad, sin heredar el de otra prueba, y `CODIGO`
#     apunta a una carpeta vacía para no mirar nunca sus archivos reales).
script = f"""
import sys, json
sys.path.insert(0, {str(BACKEND / 'app')!r})
import rutas
rutas.CODIGO = __import__('pathlib').Path({str(FAKE_OLD)!r})
print(json.dumps({{"carpeta": str(rutas.DATOS),
                   "config": str(rutas.archivo("cort_config.json")),
                   "memoria": str(rutas.archivo("cort_memory.db"))}}))
"""
r = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
assert r.returncode == 0, r.stderr
resuelto = json.loads(r.stdout.strip().splitlines()[-1])
assert Path(resuelto["carpeta"]) == NUEVO, resuelto
print("  ok  CORT_HOME manda:", NUEVO)

# 2 · la mudanza real: con el archivo viejo delante, se copia y se conserva
script2 = f"""
import sys, json
sys.path.insert(0, {str(BACKEND / 'app')!r})
import rutas
rutas.CODIGO = __import__('pathlib').Path({str(FAKE_BACKEND)!r})
p = rutas.archivo("cort_config.json")
print(json.dumps({{"ruta": str(p), "migrados": rutas.MIGRADOS,
                   "contenido": json.loads(p.read_text(encoding='utf-8'))}}))
"""
r2 = subprocess.run([sys.executable, "-c", script2], env=env, capture_output=True, text=True)
assert r2.returncode == 0, r2.stderr
dato = json.loads(r2.stdout.strip().splitlines()[-1])
assert Path(dato["ruta"]) == NUEVO / "cort_config.json", dato
assert dato["migrados"] == ["cort_config.json"], dato
assert dato["contenido"] == CLAVES, dato
print("  ok  mudanza: el cort_config.json de backend/ se copia a la carpeta personal")
print("      y la clave sigue leyéndose igual:", list(dato["contenido"].values()))

# 3 · y la memoria: se puede escribir y leer en la base nueva. Se cambia
#     `rutas.CODIGO` **antes** de importar `memory`, porque `memory.py` resuelve
#     su ruta al importarse: si no, la prueba copiaría su base real al sandbox y
#     mediría cualquier cosa (medido: salían 20 recuerdos que no eran de aquí).
script3 = f"""
import sys, pathlib
sys.path.insert(0, {str(BACKEND / 'app')!r})
import rutas
rutas.CODIGO = pathlib.Path({str(FAKE_OLD)!r})          # nada viejo: base nueva
import memory
memory.DB = rutas.archivo("cort_memory.db")
memory.remember("user", "prueba de la mudanza")
print(memory.DB.parent == pathlib.Path({str(NUEVO)!r}), len(memory.history()))
"""
r3 = subprocess.run([sys.executable, "-c", script3], env=env, capture_output=True, text=True)
assert r3.returncode == 0, r3.stderr
assert r3.stdout.strip() == "True 1", r3.stdout
print("  ok  memoria: base nueva en la carpeta personal, escribe y lee (1 recuerdo)")

# 4 · dónde vive la ruta por defecto cuando no hay `CORT_HOME`, dicho sin crear
#     nada. La rama de Windows (`%APPDATA%\CORT`) no se puede probar aquí:
#     `pathlib` no deja instanciar un `WindowsPath` en Linux, y fingirlo con
#     `os.name = "nt"` daría una prueba que no prueba nada. Se deja escrita en
#     `rutas.py` y se comprueba en el primer arranque de la dueña en Windows.
script4 = f"""
import sys; sys.path.insert(0, {str(BACKEND / 'app')!r})
import rutas
print(rutas._carpeta_por_defecto())
"""
r4 = subprocess.run([sys.executable, "-c", script4],
                    env={k: v for k, v in env.items() if k != "CORT_HOME"},
                    capture_output=True, text=True)
assert r4.returncode == 0, r4.stderr
assert r4.stdout.strip().endswith("/.cort"), r4.stdout
print("  ok  sin CORT_HOME (Linux/macOS):", r4.stdout.strip())

shutil.rmtree(SANDBOX, ignore_errors=True)
print("\ndatos a salvo: actualizar el instalador ya no borra la clave de Groq.")
