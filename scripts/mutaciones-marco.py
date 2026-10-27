#!/usr/bin/env python3
"""Batería de mutaciones de `scripts/prueba-marco.mjs`: doce errores sembrados de uno en uno.

Una suite verde no vale nada si no muerde. `marco.js` es justamente el archivo donde una
comprobación de texto se deja engañar: los diez `export let` viajan como enlaces vivos, el
router recorre cuatro registros en un orden que nadie escribió, y `montables()` filtra con
dos condiciones que se parecen. Cambiar una de esas decisiones en el código NO cambia ni una
palabra del texto que buscan otras suites, así que hace falta ejecutarlo.

Cómo se protege el repo (la lección de `feedback-bateria-mutaciones-segura`): **no se toca
ningún archivo del repo**. Se copia `ui/js` (2,3 MB) y el arnés a `/tmp`, se muta la copia y
`prueba-marco.mjs` corre desde allí, donde `RAIZ` es el `/tmp` y el `import` apunta al marco
mutado. El repo no se abre ni a escribir; si este script muere a mitad, en `/tmp` muere.

Cada mutación rompe UNA decisión del marco:
  1  `ir()` no despacha el registro de entrada     → las hojas se abrirían vacías
  2  el orden: repintar antes de cerrar            → el cajón marcaría la hoja vieja
  3  `ir()` no quita la clase de la hoja anterior  → dos hojas encendidas a la vez
  4  `ir()` no emite `cort-pantalla`               → `hud.js` no se enteraría del cambio
  5  `visibles()` deja lo escondido                → «Letra» volvería al cajón
  6  `montables()` ignora `telefono`               → Música y Equipo en el PC
  7  `montables()` ignora el puente                → Equipo con un APK viejo, botón mudo
  8  `puede()` mira el objeto y no el método       → ídem por la otra puerta
  9  `llama()` sin `typeof`                        → `TypeError` en el WebView de la dueña
  10 `llama()` sin `try/catch`                     → Java tose y la cara se corta
  11 `hayNucleo()` pregunta cada vez               → un `/api/port` por cada frase
  12 `abreCajon()` no repinta                      → el cajón ofrece un puente que ya cambió

Uso:  python3 scripts/mutaciones-marco.py     (~15 s las doce)
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
CAJA = pathlib.Path(tempfile.mkdtemp(prefix="cort-mut-marco-"))
UI = CAJA / "ui" / "js"
SCRIPTS = CAJA / "scripts"
ORIGINAL = (REPO / "ui" / "js" / "marco.js").read_text(encoding="utf-8")

# El arnés no puede vivir en /tmp a secas: calcula la raíz desde su propia ubicación, así
# que se copia con su carpeta y el marco que va a importar queda dentro de la caja.
shutil.copytree(REPO / "ui" / "js", UI)
SCRIPTS.mkdir(parents=True)
shutil.copy(REPO / "scripts" / "prueba-marco.mjs", SCRIPTS / "prueba-marco.mjs")
shutil.copy(REPO / "scripts" / "lib-cara.mjs", SCRIPTS / "lib-cara.mjs")
ARCHIVO = UI / "marco.js"

# (nombre, cadena que se busca, cadena que la sustituye)
MUTACIONES = [
    ("ir() no despacha el registro de entrada",
     "ENTRADAS.get(actual)?.();", "/* sembrado: se abre la hoja y nadie la pinta */"),
    ("el orden cambiado: repinta DESPUÉS de arrancar la hoja",
     "  REPINTOS.forEach(fn => fn());\n  ENTRADAS.get(actual)?.();",
     "  ENTRADAS.get(actual)?.();\n  REPINTOS.forEach(fn => fn());"),
    ("ir() deja la clase de la hoja anterior",
     "montables().forEach(x => raiz.classList.remove('p-' + x.id));",
     "/* sembrado: no quita las clases viejas */"),
    ("ir() no avisa a hud.js",
     "window.dispatchEvent(new CustomEvent('cort-pantalla', { detail: actual }));",
     "/* sembrado: la cara cambia sin que nadie se entere */"),
    ("visibles() ofrece lo escondido",
     "const visibles = () => montables().filter(p => !p.escondida);",
     "const visibles = () => montables();"),
    ("montables() ignora que sea de teléfono",
     "const montables = () => PANTALLAS.filter(p => (!p.telefono || enTelefono())",
     "const montables = () => PANTALLAS.filter(p => (!p.telefono || true)"),
    ("montables() ignora el puente que hace falta",
     "&& (!p.puente || puede(p.puente)));", "&& (true));"),
    ("puede() mira el puente y no el método",
     "return !!p && typeof p[nombre] === 'function';", "return !!p;"),
    ("llama() llama sin preguntar (sin typeof)",
     "if (!p || typeof p[nombre] !== 'function') return null;", "if (!p) return null;"),
    ("llama() sin try/catch",
     "try { return p[nombre](...args); } catch (e) { ctx?.term?.('el puente dijo: ' + e, 'puente'); return null; }",
     "return p[nombre](...args);"),
    ("hayNucleo() no recuerda el éxito",
     "if (nucleo) return nucleo;", "/* sembrado: pregunta cada frase */"),
    ("abreCajon() no repinta antes de abrir",
     "  REPINTOS.forEach(fn => fn());\n  document.documentElement.classList.add('cajon-abierto');",
     "  document.documentElement.classList.add('cajon-abierto');"),
]


def corre() -> tuple[int, str]:
    r = subprocess.run([sys.executable and "node", str(SCRIPTS / "prueba-marco.mjs")],
                       capture_output=True, text=True, timeout=120, cwd=str(CAJA))
    return r.returncode, (r.stdout + r.stderr)


def restablecer():
    ARCHIVO.write_text(ORIGINAL, encoding="utf-8")


rojas = 0
print(f"caja de mutaciones: {CAJA}  (el repo no se toca)")
codigo, salida = corre()
if codigo != 0:
    print("NO VALE: la suite ya estaba roja ANTES de sembrar nada. Salida:\n" + salida[-1500:])
    sys.exit(1)
print("base verde · " + salida.strip().splitlines()[-1])

for nombre, viejo, nuevo in MUTACIONES:
    if viejo not in ORIGINAL:
        print(f"  ✗ {nombre}: la cadena a mutar no está en el marco (hay que reescribir la batería)")
        continue
    ARCHIVO.write_text(ORIGINAL.replace(viejo, nuevo, 1), encoding="utf-8")
    try:
        codigo, salida = corre()
    except subprocess.TimeoutExpired:
        codigo, salida = 1, "timeout: el arnés se colgó con esta mutación"
    finally:
        restablecer()
    mordida = [l.strip()[5:] for l in salida.splitlines() if l.strip().startswith("NO ")]
    if codigo != 0:
        rojas += 1
        print(f"  ✔ muerde · {nombre}\n      → {mordida[0] if mordida else salida.strip()[-120:]}")
    else:
        print(f"  ✗ NO MUERDE · {nombre}: la suite quedó verde con el marco roto")

restablecer()
shutil.rmtree(CAJA, ignore_errors=True)
actual = (REPO / "ui" / "js" / "marco.js").read_text(encoding="utf-8")
print(f"\n{rojas}/{len(MUTACIONES)} mutaciones cortadas por la suite")
if actual != ORIGINAL:
    print("CUIDADO: el marco del repo no coincide con el que se leyó al principio")
    sys.exit(1)
sys.exit(0 if rojas == len(MUTACIONES) else 1)
