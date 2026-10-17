#!/usr/bin/env python3
"""Empaquetar CORT **desde lo versionado**, nunca desde la carpeta a pelo.

Por qué existe este script, con sus dos heridas detrás:

1. **La fuga.** El 2026-10-17 se encontró un ZIP del proyecto con un `.env` de
   26 variables **con valores reales** y un `data/rechazos.jsonl` con texto
   personal de la dueña. Nada de eso está en git —los tres están ignorados, y
   `git check-ignore` lo confirma—, pero un `Compress-Archive` / «enviar a >
   carpeta comprimida» sobre la carpeta de trabajo **sí** los mete. `git archive`
   lee el objeto `HEAD`, no el disco: lo ignorado no puede colarse porque no
   existe en el commit.
2. **El peso y la mutilación.** Ese mismo ZIP pesaba 171 MB, de los cuales
   **94,3 % eran basuras de compilación** (dos entornos virtuales de Windows,
   `android*/build/**`, `dist`), y al extraerlo en Linux quedó en 7.365 ficheros
   planos con `\\` en el nombre: un proyecto que ya no se puede abrir. Aquí sólo
   viaja lo versionado, y el resultado se comprueba **contra la lista del propio
   archivo**, no contra la buena voluntad de quien lo hizo.

La guarda es doble a propósito: `git archive` ya no debería meter nada prohibido,
y aun así se vuelve a mirar. Un `git add -f` despistado (forzar un ignorado) es
justo el tipo de error que sólo se ve cuando el archivo ya está publicado.

Uso:
    python3 scripts/empaquetar.py                 # CORT-fuente-<versión>.zip
    python3 scripts/empaquetar.py --destino /tmp   # otra carpeta de salida
    python3 scripts/empaquetar.py --comprobar X.zip # auditar un archivo ajeno
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

# Piezas que **nunca** deben salir de esta máquina. Son rutas o patrones sobre
# los nombres internos del ZIP (con `/`, que es lo que escribe `git archive`).
PROHIBIDO: tuple[str, ...] = (
    ".env",                    # secretos; `.env.example` sí viaja
    "/.venv",                  # entornos virtuales
    ".venv/",
    "node_modules/",
    "/build/",                 # outputs de Gradle/Android
    "/intermediates/",
    "__pycache__/",
    ".pyc",
    "/dist/",                  # la cara ya compilada se publica en la Release, no en la fuente
    ".db",
    ".sqlite",
    ".sqlite3",
    "data/rechazos.jsonl",     # bitácora de intentos rechazados: texto de la usuaria
    "data/agenda.json",
    "data/atuendos/",          # modelos .vrm: 157 MB y con licencia ajena
    "apps/apk/llave/",         # keystore y su contraseña
    ".keystore",
    ".apk",
    "/.git/",
)

# `.env.example` es plantilla y sí debe viajar; se excluye de la regla anterior.
PERMITIDO_EXACTO: frozenset[str] = frozenset({".env.example"})

ENTRADAS_MINIMAS = 100  # un archivo con menos de cien entradas es un empaquetado roto


def revisar(nombres: list[str]) -> list[str]:
    """Devuelve las entradas que no deberían estar en un archivo de fuente.

    Es una función pura sobre una lista de nombres para poder probarla sin
    ejecutar `git`: la guarda es lo importante, no el transporte.
    """
    malos: list[str] = []
    for nombre in nombres:
        # `lstrip("./")` sería un error: recorta *conjuntos de caracteres* y
        # convertiría `.env` en `env`, colándose por la guarda. Se quita el prefijo.
        limpio = nombre[2:] if nombre.startswith("./") else nombre.lstrip("/")
        if limpio in PERMITIDO_EXACTO or limpio.endswith(".env.example"):
            continue
        for patrón in PROHIBIDO:
            if patrón in f"/{limpio}":
                malos.append(nombre)
                break
    return malos


def version_de(repo: Path) -> str:
    """Etiqueta del commit, o su hash corto si el commit no está etiquetado."""
    salida = git(repo, "describe", "--tags", "--always", "--dirty")
    return salida or "sin-version"


def git(repo: Path, *args: str) -> str:
    """Ejecuta `git` en `repo` y devuelve su salida, o cadena vacía si falla."""
    try:
        hechas = subprocess.run(
            ("git", *args),
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return ""
    return hechas.stdout.strip()


def empaquetar(repo: Path, destino: Path) -> tuple[Path, list[str], int]:
    """Crea el ZIP desde `HEAD` y devuelve (ruta, entradas, bytes)."""
    etiqueta = version_de(repo)
    salida = destino / f"CORT-fuente-{etiqueta}.zip"
    destino.mkdir(parents=True, exist_ok=True)
    temporal = destino / ".cort-fuente.parcial.zip"

    # `git archive` escribe el commit, no el disco: lo ignorado no puede colarse.
    proceso = subprocess.run(
        ("git", "archive", "--format=zip", "-o", str(temporal), "HEAD"),
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proceso.returncode != 0 or not temporal.exists():
        raise SystemExit(f"git archive falló: {proceso.stderr.strip() or 'sin salida'}")

    with zipfile.ZipFile(temporal) as archivo:
        entradas = archivo.namelist()
    temporal.replace(salida)
    return salida, entradas, salida.stat().st_size


def comprobar(ruta_zip: Path) -> tuple[list[str], int]:
    """Lee un ZIP ajeno y devuelve (entradas, bytes) sin tocarlo."""
    with zipfile.ZipFile(ruta_zip) as archivo:
        return archivo.namelist(), ruta_zip.stat().st_size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Empaqueta CORT desde lo versionado.")
    parser.add_argument("--destino", default="/tmp", help="carpeta donde escribir el ZIP")
    parser.add_argument("--comprobar", help="auditar un ZIP existente en vez de crear uno")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent

    if args.comprobar:
        ruta = Path(args.comprobar)
        entradas, bytes_ = comprobar(ruta)
    else:
        ruta, entradas, bytes_ = empaquetar(repo, Path(args.destino))

    malos = revisar(entradas)
    print(f"archivo   : {ruta}")
    print(f"entradas  : {len(entradas)}")
    print(f"peso      : {bytes_ / 1024 / 1024:.2f} MB")
    if len(entradas) < ENTRADAS_MINIMAS:
        print(f"AVISO     : menos de {ENTRADAS_MINIMAS} entradas: el empaquetado está incompleto")
        return 1
    if malos:
        print(f"PROHIBIDAS: {len(malos)}")
        for nombre in malos[:20]:
            print(f"  - {nombre}")
        return 1
    print("guarda    : limpia (nada de .env, secretos, venvs ni basuras de build)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
