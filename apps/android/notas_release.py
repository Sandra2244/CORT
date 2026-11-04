#!/usr/bin/env python3
"""Rellena `NOTAS_RELEASE.md` con lo medido en la corrida y saca las notas de la release.

Existe porque las notas estaban escritas a mano dentro del YAML del workflow y el
2026-11-04, al publicar la 0.13.0, salieron contando lo de la 0.12.0: decían que
`/memoria/puente` no lo servía esta rama y que la cámara del teléfono no se usaba,
y las dos cosas ya eran mentira. El texto vivo se corrige en un archivo de markdown
del repo; el YAML sólo mete los números.

Cada `{{LAVE}}` del plantilla tiene que salir del entorno (`NOTAS_*`). Si falta una,
si queda un `{{...}}` sin rellenar o si el archivo no está, el script cae: una release
con un hueco a la vista miente mejor que una con un hueco silencioso.
"""

import os
import re
import sys
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent
PLANTILLA = RAIZ / "NOTAS_RELEASE.md"

# nombre del hueco en la plantilla -> variable de entorno
VAR = {
    "VERSION": "NOTAS_VERSION",
    "CODE": "NOTAS_CODE",
    "PESO": "NOTAS_PESO",
    "MB": "NOTAS_MB",
    "SHA": "NOTAS_SHA",
    "OIDO": "NOTAS_OIDO",
    "LLAVE": "NOTAS_LLAVE",
    "HUELLA": "NOTAS_HUELLA",
    "MODEL": "NOTAS_MODEL",
    "CHECS": "NOTAS_CHECS",
}


def principal():
    if not PLANTILLA.is_file():
        sys.stderr.write("no existe %s\n" % PLANTILLA)
        return 1
    texto = PLANTILLA.read_text(encoding="utf-8")

    faltan = []
    for hueco, variable in VAR.items():
        valor = os.environ.get(variable, "").strip()
        if not valor:
            faltan.append("%s (%s)" % (hueco, variable))
            valor = "?"
        texto = texto.replace("{{%s}}" % hueco, valor)
    if faltan:
        sys.stderr.write("sin medir: %s\n" % ", ".join(faltan))
        return 1

    sobran = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", texto)))
    if sobran:
        sys.stderr.write("huecos que nadie rellena: %s\n" % ", ".join(sobran))
        return 1

    if "--titulo" in sys.argv:
        # La primera línea de la plantilla es el título de la release.
        print(texto.split("\n", 1)[0].lstrip("# ").strip())
        return 0

    sys.stdout.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
