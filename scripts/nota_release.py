#!/usr/bin/env python3
"""Sacar de `docs/RELEASE-NOTES.md` la nota que corresponde a una etiqueta.

Existe porque la página de Release de GitHub la publica Actions (regla: desde
esta máquina no hay sesión de `gh` ni token, medido tres veces), y la nota ya
está escrita a mano en el repo. Duplicarla en el YAML sería tener dos verdades:
la del documento y la del pipeline, y siempre se desincroniza una.

Uso:  scripts/nota_release.py v0.10.1 cuerpo.md titulo.txt

Devuelve 0 si la sección existe, 2 si no (y entonces el pipeline cae a
`--generate-notes` en vez de publicar una Release vacía). Código en inglés no
aplica: esto es una herramienta de repo, y su salida es texto de interfaz en
español, que es lo que se lee en la página.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
NOTAS = RAIZ / "docs" / "RELEASE-NOTES.md"

# Una sección empieza con el nivel dos y la etiqueta entre acentos graves:
#   ## `v0.10.1` — las pruebas dejan de depender del apodo de tu carpeta
PREFIJO = "## `"
SEPARADOR = "\n---\n"


def buscar_seccion(texto: str, etiqueta: str) -> tuple[str, str] | None:
    """Devuelve `(título, cuerpo)` de la sección de `etiqueta`, o None.

    El título es lo que va después de la raya: en GitHub la etiqueta ya se ve
    sola en la cabecera de la Release, y repetir `v0.10.1` dos veces es ruido.
    """
    blanco = PREFIJO + etiqueta + "`"
    lineas = texto.splitlines()
    for i, linea in enumerate(lineas):
        if not linea.startswith(blanco):
            continue
        titulo = linea[len(blanco):].lstrip(" —-").strip()
        cuerpo: list[str] = []
        for siguiente in lineas[i + 1:]:
            # La próxima sección, o la raya que las separa, cierran la actual.
            if siguiente.startswith(PREFIJO) or siguiente.strip() == "---":
                break
            cuerpo.append(siguiente)
        return titulo, "\n".join(cuerpo).strip()
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 64
    etiqueta, ruta_cuerpo, ruta_titulo = argv[1], Path(argv[2]), Path(argv[3])
    if not NOTAS.is_file():
        print(f"no existe {NOTAS}", file=sys.stderr)
        return 2
    encontrada = buscar_seccion(NOTAS.read_text(encoding="utf-8"), etiqueta)
    if encontrada is None:
        print(f"`{etiqueta}` no tiene sección en {NOTAS.name}", file=sys.stderr)
        return 2
    titulo, cuerpo = encontrada
    # Cada sección de `docs/RELEASE-NOTES.md` ya termina con su línea **Zip**,
    # así que aquí no se arma ninguna URL: la nota es el texto, y el texto manda.
    ruta_titulo.write_text(titulo, encoding="utf-8")
    ruta_cuerpo.write_text(cuerpo, encoding="utf-8")
    print(f"nota de {etiqueta}: {len(cuerpo)} caracteres, título «{titulo}»")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
