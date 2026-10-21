"""La prueba de `organiza.py`, decisiva y barata: sin servidor, sin red, sin riesgos.

Monta una falsa carpeta de Documentos en `/tmp/cort-organiza-XXXX` (pdf, docx,
jpg, mp3, mp4, txt, un archivo sin extensión, uno ya colocado dentro de
`PDF/` y dos que se llaman igual), monkeyparchea `sensors.ROOTS` para que
apunte ahí y comprueba las cinco promesas del contrato:

  (a) `plan()` NO mueve nada: mismo inventario (rutas + mtimes) antes y después;
  (b) una raíz fuera de ROOTS se rechaza con texto humano;
  (c) un token equivocado (o inexistente) se rechaza: sin plan no hay órdenes;
  (d) tras `aplicar()` con el token bueno cada archivo está en su carpeta
      prevista y el NÚMERO TOTAL de archivos no cambia: nada borrado, nada
      duplicado;
  (e) los dos `doble.pdf` no se comen entre sí: el segundo gana ` (2)`.

Uso:  python3 scripts/prueba-organiza.py     (una fracción de segundo)
"""
from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend" / "app"))

import organiza                              # noqa: E402
import sensors                               # noqa: E402

FALLOS: list[str] = []


def dice_ok(label: str, detalle: str) -> None:
    print(f"  ok  {label}: {detalle}")


def falla(label: str, detalle: str) -> None:
    FALLOS.append(f"{label}: {detalle}")
    print(f"  NO  {label}: {detalle}")


def inventario(base: pathlib.Path) -> dict:
    """Cada archivo del árbol con su mtime: si algo se mueve, se copia o se
    borra, aquí se nota. Los mtimes redondeados evalan falsos cambios."""
    out: dict[str, float] = {}
    for carpeta, _dirs, archivos in os.walk(base):
        for a in archivos:
            p = pathlib.Path(carpeta) / a
            out[p.relative_to(base).as_posix()] = round(p.stat().st_mtime, 3)
    return out


# ── la casa falsa en /tmp ────────────────────────────────────────────────────
print("\n[0] el decorado")
CASA = pathlib.Path(tempfile.mkdtemp(prefix="cort-organiza-", dir="/tmp"))
DOC = CASA / "Documentos"
# 8 sueltos + un par de gemelos en subcarpetas + uno ya en su sitio (PDF/)
FALSOS = ("informe.pdf", "notas.docx", "foto.jpg", "cancion.mp3",
          "pelicula.mp4", "apuntes.txt", "LICENSE", "chiste.txt",
          "sub1/doble.pdf", "sub2/doble.pdf", "PDF/ya-esta.pdf")
for rel in FALSOS:
    p = DOC / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"contenido de prueba: {rel}", encoding="utf-8")

# el monkeypatch: organize lee sensors.ROOTS EN CADA LLAMADA, así basta con
# cambiarle el dict y nada toca los Documentos reales de la dueña
sensors.ROOTS = {"Documentos": DOC, "Música": CASA / "Musica"}
antes = inventario(DOC)
dice_ok("decorado", f"{len(antes)} archivos falsos en {CASA}")

# ── (a) el plan no mueve nada ────────────────────────────────────────────────
print("\n[a] plan(): mira, no toca")
p = organiza.plan("Documentos", "tipo")
if not p.get("ok"):
    falla("plan", f"devolvió {p.get('error')!r}")
else:
    despues = inventario(DOC)
    if antes == despues:
        dice_ok("intocable", f"los {len(antes)} archivos siguen donde estaban "
                             f"(mismas rutas, mismos mtimes)")
    else:
        falla("intocable", f"el plan movió algo antes de tiempo: "
                           f"{set(antes) ^ set(despues)}")
    if p["total"] == len(p["entradas"]) and p["total"] == len(FALSOS) - 1:
        dice_ok("total", f"{p['total']} movimientos propuestos (el que ya estaba "
                         "en PDF/ no cuenta: movimiento vacío)")
    else:
        falla("total", f"se esperaban {len(FALSOS) - 1} entradas, hay {p['total']}")
    vacio = [e for e in p["entradas"] if e["de"] == e["a"]]
    if vacio:
        falla("movimiento vacío", f"entradas que no mueven nada: {vacio[:2]}")
    else:
        dice_ok("movimiento vacío", "ninguna entrada propone quedarse quieta")
    absolutas = [e for e in p["entradas"] if e["de"].startswith("/") or e["a"].startswith("/")]
    if absolutas:
        falla("rutas relativas", f"el plan filtró rutas absolutas: {absolutas[:2]}")
    else:
        dice_ok("rutas relativas", "todas las «de» y «a» son relativas a la raíz")

# ── (b) fuera de ROOTS no se entra ───────────────────────────────────────────
print("\n[b] raíces desconocidas")
fuera = organiza.plan("Cancillería", "tipo")
if fuera.get("ok") or "fuera de tus carpetas conocidas" not in fuera.get("error", ""):
    falla("fuera de ROOTS", f"devolvió {fuera!r}")
else:
    dice_ok("fuera de ROOTS", fuera["error"][:60] + "…")

# ── (c) sin token bueno no hay órdenes ───────────────────────────────────────
print("\n[c] el token manda")
malo = organiza.aplicar("Documentos", "tipo", "deadbeefdeadbeef")
if malo.get("ok") or "no hay plan que confirmar" not in malo.get("error", ""):
    falla("token equivocado", f"aplicar aceptó un token inventado: {malo!r}")
else:
    dice_ok("token equivocado", malo["error"])
if inventario(DOC) != antes:
    falla("token equivocado", "y además movió archivos: aplicar sin token no debe tocar nada")

# ── (d) aplicar con el token del último plan ─────────────────────────────────
print("\n[d] aplicar(): los movimientos confirmados")
r = organiza.aplicar("Documentos", "tipo", p["token"])
if not r.get("ok"):
    falla("aplicar", f"devolvió {r.get('error')!r}")
elif r.get("errores"):
    falla("aplicar", f"errores sueltos: {r['errores']}")
elif r["movidos"] != p["total"]:
    falla("aplicar", f"movió {r['movidos']} de {p['total']} propuestas")
else:
    dice_ok("aplicar", f"{r['movidos']} archivos movidos, cero errores")
esperados = {"PDF/informe.pdf", "DOCX/notas.docx", "IMG/foto.jpg",
             "AUDIO/cancion.mp3", "VIDEO/pelicula.mp4", "TXT/apuntes.txt",
             "TXT/chiste.txt", "OTROS/LICENSE", "PDF/ya-esta.pdf",
             "PDF/doble.pdf", "PDF/doble (2).pdf"}
reales = set(inventario(DOC))
if reales == esperados:
    dice_ok("destinos", "cada extensión en su carpeta (sin extensión → OTROS)")
else:
    falla("destinos", f"de sobran {sorted(reales - esperados)}, faltan {sorted(esperados - reales)}")
if len(reales) == len(FALSOS):
    dice_ok("nada borrado", f"{len(reales)} archivos antes y después: "
                            "aplicar mueve, no traga")
else:
    falla("nada borrado", f"había {len(FALSOS)}, ahora {len(reales)}")
sobrantes = [q for q in reales
             if not (DOC / q).is_file() or (DOC / q).stat().st_size == 0]
if not sobrantes:
    dice_ok("nada duplicado/vacío", "todos los destinos son archivos con contenido")
else:
    falla("nada duplicado/vacío", f"rarezas: {sobrantes}")

# ── (e) los gemelos no se comen entre sí ─────────────────────────────────────
print("\n[e] dos doble.pdf")
g1, g2 = DOC / "PDF/doble.pdf", DOC / "PDF/doble (2).pdf"
if g1.is_file() and g2.is_file() and g1.read_text() != g2.read_text():
    dice_ok("sufijo (2)", "los dos gemelos sobrevivieron con su contenido intacto")
else:
    falla("sufijo (2)", f"se comieron entre sí: {g1.is_file()=}, {g2.is_file()=}")

# el plan consumido ya no vale: aplicar otra vez debe rechazar
reaplicar = organiza.aplicar("Documentos", "tipo", p["token"])
if reaplicar.get("ok"):
    falla("plan consumido", "aplicar aceptó el token por segunda vez")
else:
    dice_ok("plan consumido", reaplicar["error"])

# ── limpieza y veredicto ─────────────────────────────────────────────────────
shutil.rmtree(CASA, ignore_errors=True)
print()
if FALLOS:
    print(f"FALTA {len(FALLOS)} COSA(S):")
    for f in FALLOS:
        print("  ·", f)
    sys.exit(1)
print("organiza cosido: plan → confirmar → mover, y ni un archivo de menos.")
