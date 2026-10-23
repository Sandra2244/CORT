#!/usr/bin/env python3
"""Mide el catálogo de Ollama desde su propio registro — sin estimar nada.

¿Por qué existe este script? Porque la dueña pidió «catálogo de modelos con su
peso», y el peso que se ve en las capturas de Lark/Ollama es el que **se baja**,
no el que anuncia una web. El único número honesto es la suma de las capas del
manifiesto OCI que sirve `registry.ollama.ai`: ésos son los bytes que
`ollama pull` va a traer.

Uso (no necesita red del portátil, sólo salir a Internet; stdlib puro):

    python3 scripts/mede-catalogo.py llama3.1:8b qwen3:4b
    python3 scripts/mede-catalogo.py --lista      # los 107 ya medidos

Lo que sale es una tabla `modelo|bytes` lista para pegar en
`ui/js/telefono.js` (`CATALOGO_OLLAMA`) y en `backend/app/models.py`
(`CATALOGO`, campos `b` y `gb`). La costura ([23]) comprueba que las dos capas
coinciden, así que si alguien redondea a mano, se pone rojo.

Medido por última vez el 2026-10-23.
"""
from __future__ import annotations

import json
import sys
import urllib.request

REGISTRO = "https://registry.ollama.ai/v2/library/{mod}/manifests/{tag}"
ACEPTA = "application/vnd.docker.distribution.manifest.v2+json"

# Los 107 modelos cuya descarga se midió; la cara del teléfono lleva esta misma
# tabla dentro (`CATALOGO_OLLAMA` en `ui/js/telefono.js`) para poder mirarla sin
# portátil. Cambiarla aquí sin cambiarla allí se pone rojo en la costura.
LISTA = """llama3.2:1b llama3.2:3b llama3.1:8b llama3:8b qwen2.5:0.5b qwen2.5:1.5b
qwen2.5:3b qwen2.5:7b qwen2.5:32b qwen3:0.6b qwen3:1.7b qwen3:4b qwen3:8b qwen3:14b
qwen3.5:0.8b qwen3.5:2b qwen3.5:4b qwen3.5:9b qwen3.5:27b qwen3.5:35b
gemma2:2b gemma3:270m gemma3:1b gemma3:4b gemma3:12b gemma3:27b gemma3n:e2b
gemma3n:e4b functiongemma:270m shieldgemma:2b llama-guard3:1b phi3:3.8b phi3:mini
phi4-mini:3.8b phi4:14b phi4-reasoning:14b tinyllama:1.1b smollm:135m smollm2:135m
smollm2:360m smollm2:1.7b lfm2.5-thinking:1.2b deepseek-r1:1.5b deepseek-r1:7b
deepseek-r1:8b deepseek-r1:14b deepseek-r1:32b deepseek-llm:7b qwq:32b deepscaler:1.5b
deepcoder:1.5b cogito:8b cogito:14b mistral:7b mistral-nemo:12b mistral-small:24b
ministral-3:3b ministral-3:8b ministral-3:14b devstral:24b minicpm-v:8b moondream:1.8b
llama3.2-vision:11b qwen3-vl:2b qwen3-vl:8b codellama:7b codegemma:7b qwen2.5-coder:1.5b
qwen2.5-coder:7b qwen2.5-coder:32b qwen3-coder:30b starcoder2:3b starcoder2:7b
sqlcoder:7b dolphincoder:7b wizardcoder:33b all-minilm:22m all-minilm:33m
nomic-embed-text:latest bge-m3:latest bge-large:335m paraphrase-multilingual:latest
snowflake-arctic-embed2:568m aya:8b aya-expanse:8b tulu3:8b hermes3:3b hermes3:8b
dolphin3:8b neural-chat:7b openchat:7b starling-lm:7b solar:10.7b orca-mini:3b
llama2:7b glm4:9b exaone-deep:7.8b falcon3:1b falcon3:3b falcon3:7b granite3.1-dense:2b
granite3.1-dense:8b granite3.3:8b granite4:1b granite4:3b nemotron-mini:4b
nemotron-3-nano:4b llama3.3:70b""".split()


def bytes_de_la_descarga(modelo: str, tag: str) -> int:
    """Suma las capas del manifiesto: lo que `ollama pull` baja de verdad."""
    peticion = urllib.request.Request(REGISTRO.format(mod=modelo, tag=tag),
                                      headers={"Accept": ACEPTA})
    with urllib.request.urlopen(peticion, timeout=25) as respuesta:
        manifiesto = json.load(respuesta)
    capas = manifiesto.get("layers") or []
    if not capas:
        raise ValueError("el manifiesto no trae capas")
    return sum(int(capas[i].get("size", 0)) for i in range(len(capas)))


def main(etiquetas: list[str]) -> int:
    fallos = 0
    for etiqueta in etiquetas:
        if ":" not in etiqueta:
            print(f"{etiqueta}|MAL|falta la etiqueta después de los dos puntos")
            fallos += 1
            continue
        modelo, tag = etiqueta.split(":", 1)
        try:
            total = bytes_de_la_descarga(modelo, tag)
            print(f"{modelo}:{tag}|{total}|{round(total / 1e9, 1)} GB")
        except Exception as error:
            print(f"{modelo}:{tag}|ERROR|{type(error).__name__}: {error}")
            fallos += 1
    return 1 if fallos and fallos == len(etiquetas) else 0


if __name__ == "__main__":
    argumentos = sys.argv[1:]
    if argumentos[:1] == ["--lista"]:
        sys.exit(main(sorted(LISTA, key=lambda t: t.split(":")[0])))
    sys.exit(main(argumentos or ["qwen3:0.6b", "llama3.1:8b"]))
