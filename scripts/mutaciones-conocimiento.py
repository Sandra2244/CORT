#!/usr/bin/env python3
"""Batería de mutaciones de `scripts/prueba-conocimiento.py`: siete errores sembrados de uno en uno.

Una suite verde no vale nada si no muerde. Cada mutación rompe UNA decisión del índice de
conocimiento — que no se invente una respuesta cuando el tema no está, que los puntos de la
búsqueda sean 3/2/1 y no parejos, que el título salga de la primera línea, que el `../` no
suba, que una raíz prohibida se niegue, que un archivo vacío no cuente como leído y que la
caché exista — y esta batería comprueba que la suite se pone roja de verdad.

Cómo se protege el repo (la lección de `mutaciones-musica.py`): **no se toca ningún archivo
del repo**. Se copia `backend/app` entero a `/tmp`, se muta la copia y `prueba-conocimiento.py`
corre con `CORT_CODIGO` apuntando allí. Al final se imprimen los `md5sum` de los archivos del
repo para dejar probado que siguen byte a byte como estaban, aunque este script muera a mitad.

Uso:  python3 scripts/mutaciones-conocimiento.py     (un par de segundos por mutación)
"""
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "backend" / "app"
COPIA = pathlib.Path(tempfile.mkdtemp(prefix="cort-mut-conoc-")) / "app"
FALLOS_MUT = []

MUTACIONES = [
    ("M1 responde inventa cuando el tema NO está",
     '        return {"ok": False, "modo": "no-esta", "dice":',
     '        return {"ok": True, "modo": "citado", "dice":'),
    ("M2 los puntos de la búsqueda se vuelven parejos (3 → 1)",
     "                g += 3", "                g += 1"),
    ("M3 el título deja de leer la primera línea",
     "            return limpio[:90]", "            return Path(nombre).stem[:90]"),
    ("M4 el `../` se deja pasar",
     '    if any(p in (".", "..") for p in parts):', "    if False:"),
    ("M5 una raíz que no está entre las seis se acepta",
     "    if not parts or parts[0] not in sensors.ROOTS:", "    if not parts:"),
    ("M6 un archivo vacío cuenta como leído",
     "            if not limpio:\n                vaciar += 1",
     "            if not limpio:\n                pass"),
    ("M7 la caché se desactiva (la cara volvería a medir el disco cada vez)",
     "    if visto and not fuerza and (time.time() - visto[0]) < TTL_CACHE:",
     "    if False and not fuerza:"),
]


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


ANTES = {f: md5(SRC / f) for f in ("conocimiento.py", "sensors.py")}

shutil.copytree(SRC, COPIA, ignore=shutil.ignore_patterns("__pycache__"))
print(f"· copia mutante en {COPIA}")


def ejecuta():
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "prueba-conocimiento.py")],
                       capture_output=True, text=True, timeout=600,
                       env={"CORT_CODIGO": str(COPIA), "PATH": "/usr/bin:/bin",
                            "HOME": str(COPIA.parent)})
    return r.returncode, (r.stdout + r.stderr)


st, salida = ejecuta()
if st != 0:
    print("LA COPIA SIN MUTAR YA FALLA — nada que probar:")
    print("\n".join(salida.splitlines()[-14:]))
    sys.exit(1)
else:
    print("verde ·", sum(1 for l in salida.splitlines() if "  ok " in l), "comprobaciones")

for nombre, viejo, nuevo in MUTACIONES:
    ruta = COPIA / "conocimiento.py"
    texto = ruta.read_text(encoding="utf-8")
    if viejo not in texto:
        print(f"  INVÁLIDA {nombre}: el patrón no está en la copia")
        FALLOS_MUT.append(nombre)
        continue
    ruta.write_text(texto.replace(viejo, nuevo, 1), encoding="utf-8")
    try:
        st, salida = ejecuta()
    finally:
        ruta.write_text(texto, encoding="utf-8")
    rojos = [l.strip() for l in salida.splitlines() if "NO " in l or "FALLA" in l]
    if st == 0:
        print(f"  ESCAPA   {nombre}: la suite siguió verde")
        FALLOS_MUT.append(nombre)
    else:
        print(f"  mordida  {nombre}: {len(rojos)} roja(s) · "
              + (rojos[0][:96] if rojos else "se cayó antes de terminar"))

print("\n· los archivos del repo, sin tocar:")
for f, d in ANTES.items():
    igual = md5(SRC / f) == d
    print(f"  {'intacto' if igual else 'PISADO '} {f} · {d[:12]}")
    if not igual:
        FALLOS_MUT.append(f"{f} modificado")

shutil.rmtree(COPIA.parent, ignore_errors=True)
print(f"\n{'todo mordido y el repo intacto' if not FALLOS_MUT else 'ESCAPAN / HAY DAÑO: ' + str(FALLOS_MUT)}")
sys.exit(1 if FALLOS_MUT else 0)
