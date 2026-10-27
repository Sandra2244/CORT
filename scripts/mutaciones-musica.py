#!/usr/bin/env python3
"""Batería de mutaciones de `scripts/prueba-musica.py`: diez errores sembrados de uno en uno.

Una suite verde no vale nada si no muerde. Cada mutación rompe UNA decisión del
núcleo de música — la lista cerrada de etiquetas, la duración `TLEN`, el orden de
la playlist, la reja de `music_path`, no sobrescribir, la honestidad del estado,
el esquema `content://` y el filtro de rutas imposibles — y esta batería comprueba
que la suite se pone roja de verdad.

Cómo se protege el repo (la lección de `feedback-bateria-mutaciones-segura`): **no se
toca ningún archivo del repo**. Se copia `backend/app` entero a `/tmp`, se muta la
copia y `prueba-musica.py` corre con `CORT_CODIGO` apuntando allí. Al final se
imprimen los `md5sum` de los tres archivos del repo para dejar probado que siguen
byte a byte como estaban, aunque este script muera a mitad.

Uso:  python3 scripts/mutaciones-musica.py     (media vuelta por mutación, ~1 min)
"""
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "backend" / "app"
COPIA = pathlib.Path(tempfile.mkdtemp(prefix="cort-mut-musica-")) / "app"
FALLOS_MUT = []

MUTACIONES = [
    ("M1 la lista cerrada de etiquetas se abre",
     'CAMPOS = ("TIT2", "TPE1", "TALB", "TCON", "TLEN")', 'CAMPOS = ("TIT2", "TPE1", "TALB", "TCON", "TLEN", "TSSE", "TPE2")'),
    ("M2 `TLEN` leído como segundos en vez de milisegundos",
     'seg = int(tag.get("TLEN", "0")) // 1000 or 0', 'seg = int(tag.get("TLEN", "0") or 0)'),
    ("M3 la playlist pierde SU orden",
     '        todo.sort(key=lambda t: orden[t["ruta"]])', '        pass'),
    ("M4 `suena` sin la reja de `music_path`",
     '        f = sensors.music_path(rel)\n        if not f:',
     '        f = (sensors.music_path(rel) or (raices()[0][1] / rel)).resolve()\n        if not f:'),
    ("M5 sobrescribir la playlist que ya existe", '    if destino.exists():', '    if False:'),
    ("M6 prometer que suena sin que el aparato lo diga",
     '    return "desconocido"', '    return "reproduciendo"'),
    ("M7 la playlist admite una ruta absoluta que está FUERA de Música",
     '        return f"{nombre}/{rel}".replace("\\\\", "/")\n    return None',
     '        return f"{nombre}/{rel}".replace("\\\\", "/")\n    return str(candidato)'),
    ("M8 listar canciones que `/api/audio` no puede servir",
     '        if not music_path_ok(ruta):', '        if False:'),
    ("M9 la búsqueda no mira el álbum", 'or t in plegar(x["album"])', 'or False'),
    ("M10 `_resuelve` se traga cualquier sufijo o archivo inexistente",
     '    if candidato.suffix.lower() not in AUDIO_EXT or not candidato.is_file():', '    if False:'),
]


def md5(p: pathlib.Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


ANTES = {f: md5(SRC / f) for f in ("musica.py", "sensors.py", "actions.py", "main.py")}
shutil.copytree(SRC, COPIA, ignore=shutil.ignore_patterns("__pycache__"))

env = {**__import__("os").environ, "CORT_CODIGO": str(COPIA)}


def ejecuta():
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "prueba-musica.py")],
                       capture_output=True, text=True, cwd=str(REPO), env=env, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


st, salida = ejecuta()
print("\n· base sin mutar (tiene que dar 0):", end=" ")
if st != 0:
    print("ROJA — nada que probar")
    print("\n".join(l for l in salida.splitlines()
                    if "FALLA" in l or "Traceback" in l or "Error" in l)[:900])
    FALLOS_MUT.append("la base no estaba verde")
else:
    print("verde ·", sum(1 for l in salida.splitlines() if "  ok " in l), "comprobaciones")

for nombre, viejo, nuevo in MUTACIONES:
    ruta = COPIA / "musica.py"
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
    rojos = [l.strip() for l in salida.splitlines() if "FALLA" in l]
    if st == 0:
        print(f"  ESCAPA   {nombre}: la suite siguió verde")
        FALLOS_MUT.append(nombre)
    else:
        print(f"  mordida  {nombre}: {len(rojos)} roja(s) · {rojos[0][:96] if rojos else 'no hay FALLA (se cayó antes)'}")

print("\n· los archivos del repo, sin tocar:")
for f, d in ANTES.items():
    igual = md5(SRC / f) == d
    print(f"  {'intacto' if igual else 'PISADO '} {f} · {d[:12]}")
    if not igual:
        FALLOS_MUT.append(f"{f} modificado")

shutil.rmtree(COPIA.parent, ignore_errors=True)
print(f"\n{'todo mordido y el repo intacto' if not FALLOS_MUT else 'ESCAPAN / HAY DAÑO: ' + str(FALLOS_MUT)}")
sys.exit(1 if FALLOS_MUT else 0)
