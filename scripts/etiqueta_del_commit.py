#!/usr/bin/env python3
"""La etiqueta que apunta a un commit, leída de la lista de tags de GitHub.

Existe porque `.github/workflows/compilar-apk.yml` necesita saber **en qué versión
se está escribiendo el APK** antes de invocar `compilar.sh`, y el nombre del ref
que disparó el run no siempre es la respuesta: cuando `publicar-release.yml` crea
la etiqueta él solo (`gh release create v0.14.1` sobre el commit de `main`), el
evento que corre es un `push` de rama, y `GITHUB_REF_NAME` vale `main`. Medido el
2026-10-15: el `CORT-v0.14.1.apk` salió con `versionName "main"` por leer el ref.

Lee el JSON por `stdin` —el paso del workflow hace `gh api …/tags | python3
scripts/etiqueta_del_commit.py`— y escribe en `stdout` la etiqueta con su `v`, o
cadena vacía si ninguna apunta a ese commit. Imprime nada en vez de fallar a
propósito: un resolutor que revienta no puede contar su propio fallo, y las logs
de Actions son privadas.

Sin dependencias fuera de la estándar (`json`, `os`, `sys`): regla 4 del repo.
"""
from __future__ import annotations

import json
import os
import sys


def desde_json(texto: str, sha: str) -> str:
    """La primera etiqueta cuyo commit sea `sha`; vacío si no la hay.

    Se aceptan los dos sentidos del prefijo (`sha` corto contra los 40 hex de la
    API y al revés) porque los pasos escriben `${GITHUB_SHA:0:7}` por comodidad.
    Con `sha` más corto de 7 caracteres se devuelve vacío: un prefijo de tres
    letras casaría con media docena de commits y la «etiqueta» sería un invento.
    """
    blanco = (sha or "").strip().lower()
    if len(blanco) < 7:
        return ""
    try:
        datos = json.loads(texto)
    except (json.JSONDecodeError, TypeError, ValueError):
        return ""
    if not isinstance(datos, list):
        return ""
    for etiqueta in datos:
        if not isinstance(etiqueta, dict):
            continue
        commito = etiqueta.get("commit")
        objetivo = commito.get("sha") if isinstance(commito, dict) else None
        if not isinstance(objetivo, str):
            continue
        objetivo = objetivo.strip().lower()
        if objetivo == blanco or objetivo.startswith(blanco) or blanco.startswith(objetivo):
            return str(etiqueta.get("name") or "")
    return ""


def main(argv: list[str]) -> int:
    sha = argv[1] if len(argv) > 1 else os.environ.get("GITHUB_SHA", "")
    nombre = desde_json(sys.stdin.read(), sha)
    if nombre:
        print(nombre)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
