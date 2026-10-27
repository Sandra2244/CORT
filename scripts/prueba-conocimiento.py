"""Prueba del índice de conocimiento EN ARENA: no toca la carpeta de la dueña.

Lo que se ejerce es el hueco 2.2 de `docs/ANALISIS-PROMPT-Y-VIDEOS.md`: su prompt prometía
una «carpeta de conocimiento» y un `knowledge.py` que la leyera, y en el repo sólo existía
`/api/lee`, que lee un archivo **si le nombras la ruta**. Aquí se prueba lo que faltaba:
que CORT sepa qué hay en su carpeta sin que se lo digas.

Seis cosas, medidas sobre un directorio prestado (`tempfile`), con `sensors.ROOTS`
redirigido a la arena — el `~/Documentos` de la dueña no se abre ni se escribe:

  1. **El título es la primera línea con letras**, sin adornos de Markdown, y si el
     archivo está vacío el título es su nombre: un hecho, no una invención.
  2. **Lo que no es texto plano se nombra con su motivo** (PDF, .docx, el grande, el que
     no se puede abrir), no se calla ni se cuenta como leído.
  3. **El candado**: `../` y las raíces prohibidas no indexan nada fuera de la raíz.
  4. **La búsqueda es medible**: 3 puntos en el título, 2 en el nombre, 1 en el extracto,
     y el desempate es la fecha. Por eso el `motivo` se puede enseñar sin mentir.
  5. **`responde` cita o confiesa**: sin carpeta dice la ruta exacta que hay que crear; sin
     coincidencia dice en cuántos archivos buscó; y cuando cita, lo que devuelve salió del
     disco.
  6. La caché tiene su llave (`en_caché`) y el botón de refrescar la salta de verdad.

Uso:  python3 scripts/prueba-conocimiento.py     (dos segundos, sin red, sin cerebro)
"""
import os
import pathlib
import sys
import tempfile
import time

ARENA = pathlib.Path(tempfile.mkdtemp(prefix="cort-conocimiento-"))
RAIZ = ARENA / "Documentos" / "conocimiento"
# `CORT_CODIGO` permite probar una COPIA del código (la batería de mutaciones la usa):
# el repo nunca se muta, y sin esa variable se prueba el código de siempre.
CODIGO = pathlib.Path(os.environ.get("CORT_CODIGO")
                      or pathlib.Path(__file__).resolve().parent.parent / "backend" / "app")
sys.path.insert(0, str(CODIGO))

import sensors            # noqa: E402
sensors.ROOTS = {k: ARENA / k for k in sensors.ROOTS}   # el candado, pero en la arena

import conocimiento       # noqa: E402

FALLOS = []


def dice_ok(que, como):
    print(f"  ok   {que:52} {como}")


def falla(que, por):
    print(f"  NO   {que}: {por}")
    FALLOS.append(que)


def espero(que, obtenido, querido):
    if obtenido == querido:
        dice_ok(que, repr(obtenido))
    else:
        falla(que, f"dio {obtenido!r} y tenía que dar {querido!r}")


def cierto(que, obtenido):
    if obtenido:
        dice_ok(que, "sí")
    else:
        falla(que, f"dio {obtenido!r}")


def escribe(rel, texto, dias=0):
    f = RAIZ / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto, encoding="utf-8")
    if dias:
        t = time.time() - dias * 86400
        os.utime(f, (t, t))
    return f


# ── la arena: cinco textos, un PDF, un grande, un vacío, una oculta y un pozo ──
escribe("bioquimica/ciclo-de-la-urea.md",
        "# Ciclo de la Urea\n\nLa urea se forma en el hígado a partir del amoníaco.\n", dias=1)
escribe("bioquimica/repaso-glucolisis.txt",
        "Repaso de glucólisis\nLa glucosa se parte en dos piruvatos.\n", dias=9)
escribe("MORFO-3/notas-clase.txt", "Tema de hoy: bioquímica, el ciclo de la urea\n", dias=2)
escribe("apunte-vacio.md", "", dias=3)
escribe("suelo.md", "Lista de materiales del laboratorio de MORFO 3\n", dias=0)
escribe("factura.pdf", "%PDF-1.4 no soy texto\n", dias=0)
escribe("gigante.log", "línea " * 90000, dias=0)          # > 400 KB: se declara fuera
escribe(".oculta/no-me-veas.md", "oculto\n", dias=0)
escribe("hondo/a/b/c/d/secreto.md", "demasiado hondo\n", dias=0)   # pasa de LIMITE_PROFUNDIDAD

print("\n· el título sale de la primera línea con letras (y no se inventa)")
espero("«# Ciclo de la Urea» sin el almohadilla", conocimiento.titula("# Ciclo de la Urea\nx", "n.md"),
       "Ciclo de la Urea")
espero("«**Repaso**» sin asteriscos",
       conocimiento.titula("**Repaso** de bioquímica", "n.md"), "Repaso de bioquímica")
espero("un archivo vacío se queda con su nombre", conocimiento.titula("", "apunte-vacio.md"),
       "apunte-vacio")
espero("y unos símbolos sueltos tampoco son título", conocimiento.titula("### --- \n\n##", "r.txt"), "r")
espero("«Bioquímica» y «bioquimica» son la misma palabra",
       conocimiento.normaliza("  BioQUÍMICA  ") == "bioquimica", True)

print("\n· escanea: qué entró, qué se quedó fuera y por qué")
idx = conocimiento.escanea(RAIZ)
rutas = [a["ruta"] for a in idx["archivos"]]
espero("cinco textos indexados", idx["total"], 5)
# El orden es el del recorrido: primero los sueltos de la raíz (en orden de nombre) y
# después las carpetas, también ordenadas. Es determinista, y eso es lo que se firma.
espero("la ruta es relativa y con barras", rutas,
       ["apunte-vacio.md", "suelo.md", "MORFO-3/notas-clase.txt",
        "bioquimica/ciclo-de-la-urea.md", "bioquimica/repaso-glucolisis.txt"])
cierto("el PDF está fuera con su motivo",
       any(f["ruta"] == "factura.pdf" and "no es texto" in f["motivo"] for f in idx["fuera"]))
cierto("el grande también, con su tamaño declarado",
       any(f["ruta"] == "gigante.log" and "grande" in f["motivo"] for f in idx["fuera"]))
espero("el vacío se cuenta como vacío, no como leído", idx["vaciar"], 1)
cierto("la oculta no se ve", not any(".oculta" in r for r in rutas))
cierto("y el pozo más profundo tampoco", not any("secreto" in r for r in rutas))
espero("el título del de urea es el que se leyó",
       next(a["titulo"] for a in idx["archivos"] if "urea" in a["ruta"]), "Ciclo de la Urea")
espero("su fecha tiene pinta de fecha", len(next(a["modificado"] for a in idx["archivos"]
                                                 if "urea" in a["ruta"])), 10)

print("\n· sin carpeta no hay índice, y se dice la ruta que falta")
vacio = conocimiento.escanea(ARENA / "Documentos" / "no-existe")
espero("ok en falso", vacio["ok"], False)
espero("existe en falso", vacio["existe"], False)
cierto("el aviso nombra la ruta exacta", "no-existe" in vacio["dice"] and "créala" in vacio["dice"])
espero("y no hay archivos que pintar", vacio["archivos"], [])

print("\n· busca: puntos que se pueden enseñar, y desempate por fecha")
top = conocimiento.busca("¿el ciclo de la urea donde se forma?", idx)
espero("el primero es el archivo de urea", top[0]["ruta"], "bioquimica/ciclo-de-la-urea.md")
cierto("su motivo nombra las palabras", "urea" in top[0]["motivo"] and "ciclo" in top[0]["motivo"])
espero("con una palabra: 3 título + 2 nombre + 1 extracto",
       conocimiento.busca("urea", idx)[0]["puntos"], 6)
espero("el de clase entra después porque sólo tiene título y extracto",
       conocimiento.busca("urea", idx)[1]["ruta"], "MORFO-3/notas-clase.txt")
espero("con una sola palabra, menos candidatos", len(conocimiento.busca("glucólisis", idx)), 1)
espero("y con puras palabras cortas, ninguno", conocimiento.busca("de la el", idx), [])
espero("un índice vacío no busca", conocimiento.busca("urea", {"archivos": []}), [])
# El desempate por fecha: dos apuntes con los MISMOS puntos, y gana el más reciente.
escribe("laboratorio-viejo.md", "Laboratorio de química: matraz y probeta\n", dias=7)
escribe("laboratorio-nuevo.md", "Laboratorio de química: microscopio\n", dias=1)
otro = conocimiento.escanea(RAIZ)
espero("los dos puntúan igual, y ese empate es lo que se prueba",
       [a["puntos"] for a in conocimiento.busca("laboratorio química", otro)[:2]], [10, 10])
espero("con los mismos puntos gana el más reciente",
       conocimiento.busca("laboratorio química", otro)[0]["ruta"], "laboratorio-nuevo.md")

print("\n· el candado: ni un paso fuera de la raíz")
espero("la raíz por defecto vive dentro de Documentos",
       str(conocimiento.raiz_resuelta()).startswith(str(ARENA / "Documentos")), True)
negada = conocimiento.indice("Documentos/../../etc")
espero("una raíz con `../` no se indexa", negada["ok"], False)
cierto("y el motivo se puede leer en pantalla", ".." in negada["dice"])
espero("sin archivos que pintar", negada["archivos"], [])
fuera = conocimiento.indice("Sistema/conocimiento")
espero("una raíz que no está entre las seis, tampoco", fuera["ok"], False)
cierto("y dice cuáles son las que sí", "Documentos" in fuera["dice"])
try:
    conocimiento.raiz_resuelta("Documentos/../../etc")
    falla("`raiz_resuelta` se niega en voz alta", "no lanzó nada")
except ValueError:
    dice_ok("`raiz_resuelta` se niega en voz alta", "ValueError")

print("\n· la caché tiene su llave y el refrescar la salta")
conocimiento._CACHE.clear()
primera = conocimiento.indice()
segunda = conocimiento.indice()
espero("la primera midió el disco", primera["en_caché"], False)
espero("la segunda no", segunda["en_caché"], True)
espero("y forzar vuelve a medir", conocimiento.indice(fuerza=True)["en_caché"], False)
espero("estado() dice cuántos hay", conocimiento.estado()["total"],
       conocimiento.indice(fuerza=True)["total"])

print("\n· responde: cita lo que leyó, o confiesa lo que no hizo")
r = conocimiento.responde("¿en dónde se forma la urea?")
espero("con fundamento", r["ok"], True)
espero("en modo citado", r["modo"], "citado")
cierto("el dice nombra el título y la ruta",
       "Ciclo de la Urea" in r["dice"] and "bioquimica/ciclo-de-la-urea.md" in r["dice"])
cierto("la cita salió del disco", "hígado" in r["cita"])
cierto("y enseña los demás candidatos", "MORFO-3/notas-clase.txt" in r["candidatos"])
n = conocimiento.responde("¿qué es la fotosíntesis?")
espero("si no está, no lo inventa", n["ok"], False)
espero("dice que buscó y en cuántos", n["modo"], "no-esta")
cierto("con el número de archivos por delante", str(n["total"]) in n["dice"])
sin = conocimiento.responde("urea", rel="Documentos/no-existe")
espero("sin carpeta lo dice antes de preguntar", sin["modo"], "sin-carpeta")

print()
if FALLOS:
    print(f"conocimiento: {len(FALLOS)} FALLA(S) -> {', '.join(FALLOS)}")
    sys.exit(1)
print("conocimiento cosido: sabe qué hay en su carpeta, cita lo que leyó y lo que no, lo dice.")
