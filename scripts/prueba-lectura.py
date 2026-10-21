"""Prueba decisiva de la lectura en voz alta, sin tocar el backend ni su base real.

Se compran tres cosas de una vez:
  1. `tengo que …` guarda una pendiente y `listo N` la cierra.
  2. `lee mis notas` / `lee mis tareas` devuelven texto hablado (no un silencio).
  3. `lee el documento X` saca el texto dentro de las raíces y se corta por palabra.

Nada de esto abre el navegador ni habla con la nube: las órdenes que **tocan el
sistema** (`abre youtube`, `muéstrame la carpeta …`) se compran con `_one`, que
devuelve el parejero (acción, frase) sin ejecutarlas. `memory.DB` y `sensors.ROOTS`
se mueven a un directorio temporal: el `cort_memory.db` de la dueña y sus carpetas
reales no se leen ni se escriben.

Uso:  python3 scripts/prueba-lectura.py      (un segundo, sin servidor)
"""
import pathlib
import sys
import tempfile

TRAJO = pathlib.Path(tempfile.mkdtemp(prefix="cort-prueba-"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backend" / "app"))

import memory          # noqa: E402
import sensors         # noqa: E402
memory.DB = TRAJO / "cort_memory.db"
sensors.ROOTS = {"Documentos": TRAJO / "Documentos"}
(sensors.ROOTS["Documentos"] / "notas").mkdir(parents=True)
(sensors.ROOTS["Documentos"] / "notas" / "recibo.txt").write_text(
    "Recibo de la luz de septiembre.\n\nSon 41,20 euros y el plazo vence el día 12.",
    encoding="utf-8")
(sensors.ROOTS["Documentos"] / "notas" / "factura.pdf").write_bytes(b"%PDF-1.4 mentira")

import actions         # noqa: E402
actions.memory = memory
actions.sensors = sensors

HABLADAS = [
    "tengo que llamar al dentista",
    "tengo que comprar leche",
    "lee mis tareas",
    "listo 1",
    "lee mis tareas",
    "apunta que el wifi de la vecina se cae a las ocho",
    "lee mis notas",
    "lee el documento recibo",
    "lee la factura.pdf",
    "lee mis mensajes de whatsapp",
]
for frase in HABLADAS:
    r = actions.run_command(frase)
    print(f"[{','.join(r['done']) or '—':>10}] {frase}\n            → {r['reply'][:160]}")

print("\n── lo que NO es una lectura (se va al cerebro, no a la boca) ──")
# Sólo se mira `_one` con frases que **no ejecutan nada**: «muéstrame la carpeta …»
# abriría el explorador de verdad, y esta prueba no tiene permiso para eso.
for frase in ["cuéntame un chiste de robots", "lee los modelos", "lee la carpeta Documentos"]:
    print(f"  {frase!r} → {actions._one(frase)}")

print("\npendientes abiertas:", memory.list_tasks())
print("notas:", [n["texto"][:40] for n in memory.list_notes()])
print("leer_texto directo:", sensors.leer_texto("Documentos/notas/recibo.txt")["texto"][:60])
print("fuera de raíz:", sensors.leer_texto("Documentos/../../etc/passwd")["error"])
print("vacío:", sensors.leer_texto("Documentos/notas/no-existe.txt")["error"])
