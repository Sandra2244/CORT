#!/usr/bin/env python3
"""CORT — la única prueba que decide el cerebro (F9).

Qué mide, con la máquina despejada: si un modelo de 0,5-0,6 B es capaz de traducir tus
frases largas (con errores de dictado incluidos) a un plan JSON que el ejecutor pueda
validar. No ejecuta nada: pregunta al modelo y apunta. Ningún archivo se mueve, ninguna
ventana se cierra, ninguna canción suena.

Se corre CON QODER CERRADO. Medido: con el agente abierto quedan 150-178 MB libres y el
modelo pide ~680 MB; cargarlo ahí es congelar el equipo, no medir.

  python3 scripts/cerebro_prueba.py                      # qwen2.5:0.5b
  python3 scripts/cerebro_prueba.py --modelo qwen3:0.6b  # el otro candidato
  python3 scripts/cerebro_prueba.py --umbral 900         # RAM mínima que exige

Al final deja ~/.local/share/cort/registro-cerebro.jsonl con una línea por frase: el JSON
que propuso, si parseó, si el validador lo aceptó y los tokens/s. Con eso se elige modelo
con números, no por gusto.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
CASA = Path(os.environ.get("CORT_HOME", str(Path.home())))
DATOS = Path(os.environ.get("CORT_DATOS", str(CASA / ".local" / "share" / "cort")))
REGISTRO = DATOS / "registro-cerebro.jsonl"

# Las doce frases que dijiste (o casi): dictado con erratas incluido.
FRASES = [
    "investígame en google qué es la toxoplasmosis",
    "mueve la carpeta proyectos a documentos",
    "mueve los archivos que descargué hoy a documentos",
    "pon en lark player la playlist dark rose y reproduce stereo love slowed",
    "qué canciones tengo en la carpeta dark rose",
    "oye cort cierra todas las ventanas menos firefox",
    "anota que la toxoplasmosis se contagia por los gatos y la carne cruda",
    "recuérdame comprar agua oxigenada en dos horas",
    "bájale el brillo a la laptop y pon el volumen al 30",
    "léeme la selección",
    "qué temperatura tiene el equipo y cuánta memoria queda",
    "hola buenos días",
]

VERBOS = ("investigar abrir_url buscar_archivo mover_archivo copiar_archivo crear_carpeta listar "
          "reproducir playlist pausar siguiente volumen brillo apagar reiniciar bloquear "
          "captura_notas recordatorio temporizador leer_seleccion estado_equipo clima hora saludar "
          "nada")

SISTEMA = (
    "Eres el compilador de intenciones de CORT, un asistente local. No respondes charla: "
    "traduces la frase de la usuaria a UN objeto JSON con estas claves exactas: "
    '{"intencion": "<una de: ' + VERBOS + '>", '
    '"argumentos": {"clave": "valor"}, '
    '"necesita_confirmacion": true|false, '
    '"no_entendido": true|false}. '
    "Reglas: si la frase no pide hacer nada, intencion es \"nada\". Si no la entiendes, "
    "no_entendido es true y no inventes argumentos. Los caminos van tal como la usuaria los "
    "dice, sin inventar rutas. Si pide algo destructivo o apagar, necesita_confirmacion es true. "
    "Devuelves SOLO el JSON, sin explicación."
)


def ram_libre_mb() -> int:
    libre = 0
    for linea in open("/proc/meminfo", encoding="utf-8"):
        if linea.startswith("MemAvailable:"):
            libre = int(linea.split()[1]) // 1024
            break
    return libre


def ollama_vivo() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def levantar_ollama() -> bool:
    if ollama_vivo():
        return True
    if not shutil.which("ollama"):
        print("  [no] ollama no está instalado en esta máquina")
        return False
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    for _ in range(24):
        time.sleep(1.0)
        if ollama_vivo():
            return True
    return False


def generar(modelo: str, frase: str):
    """Una llamada a /api/generate con format=json (muestreo gramatical: no puede
    devolver prosa). Devuelve (dict|None, métricas)."""
    cuerpo = json.dumps({
        "model": modelo, "system": SISTEMA, "prompt": frase,
        "format": "json", "stream": False,
        "options": {"temperature": 0, "num_ctx": 2048, "num_predict": 160,
                    "keep_alive": "2m"},
    }).encode()
    t0 = time.time()
    try:
        req = urllib.request.Request(OLLAMA + "/api/generate", data=cuerpo,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read().decode())
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return None, {"error": f"{type(e).__name__}: {e}", "ms": int((time.time() - t0) * 1000)}
    ms = int((time.time() - t0) * 1000)
    crudo = d.get("response") or ""
    try:
        plan = json.loads(crudo)
    except Exception:
        plan = None
    tok = d.get("eval_count") or 0
    dur = d.get("eval_duration") or 0
    med = {"ms": ms, "tokens": tok,
           "tok_s": round(tok / (dur / 1e9), 1) if dur else None,
           "carga_ms": d.get("load_duration"), "crudo": crudo[:400]}
    return plan, med


def valido(plan, frase: str) -> tuple[bool, str]:
    """El mismo filtro que tendrá el ejecutor: verbo conocido y argumentos con pinta real."""
    if not isinstance(plan, dict):
        return False, "no es un objeto JSON"
    if plan.get("no_entendido"):
        return True, "declaró no entender (honesto, vale)"
    v = plan.get("intencion")
    if not isinstance(v, str) or not v:
        return False, "sin intención"
    if v.strip().lower() not in VERBOS:
        return False, f"intención inventada: {v}"
    a = plan.get("argumentos")
    if a is not None and not isinstance(a, dict):
        return False, "argumentos no son objeto"
    if v in ("mover_archivo", "copiar_archivo", "crear_carpeta") and not (a or {}).get("origen"):
        return False, "falta el origen del archivo"
    if v == "reproducir" and not (a or {}).get("pista") and not (a or {}).get("playlist"):
        return False, "no dice qué reproducir"
    return True, "aceptado"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="qwen2.5:0.5b")
    ap.add_argument("--umbral", type=int, default=900, help="MB libres mínimos para intentar")
    ap.add_argument("--parar-ollama", action="store_true",
                    help="apagar el servidor al terminar (libera la RAM)")
    args = ap.parse_args()

    print(f"[cerebro] modelo {args.modelo} · RAM libre ahora: {ram_libre_mb()} MB")
    if ram_libre_mb() < args.umbral:
        print(f"[cerebro] NO cargo: hacen falta {args.umbral} MB libres y hay {ram_libre_mb()}."
              f"\n            Cierra Qoder (1,09 GB medidos) y el navegador, y vuelve a correr esto."
              f"\n            Cargarlo igual es congelar la máquina, y una medida con el equipo"
              f"\n            swapoteando no es una medida.")
        return 2
    if not levantar_ollama():
        print("[cerebro] Ollama no arrancó; no hay nada que medir.")
        return 3

    DATOS.mkdir(parents=True, exist_ok=True)
    aciertos = 0
    tiempos = []
    with open(REGISTRO, "a", encoding="utf-8") as log:
        print(f"\n{'frase':<52} {'intención':<18} {'validador':<26} {'ms':>6} {'tok/s':>6}")
        print("-" * 112)
        for f in FRASES:
            plan, med = generar(args.modelo, f)
            ok, motivo = valido(plan, f) if plan is not None or "error" not in med else (False, med["error"][:60])
            if ok:
                aciertos += 1
            if med.get("ms"):
                tiempos.append(med["ms"])
            intencion = (plan or {}).get("intencion", "—")
            print(f"{f[:50]:<52} {str(intencion):<18} {(motivo[:24]):<26} "
                  f"{med.get('ms', 0):>6} {med.get('tok_s') or '—':>6}", flush=True)
            log.write(json.dumps({"hora": time.strftime("%Y-%m-%dT%H:%M:%S"), "modelo": args.modelo,
                                  "frase": f, "plan": plan, "valido": ok, "motivo": motivo,
                                  "ms": med.get("ms"), "tok_s": med.get("tok_s"),
                                  "crudo": med.get("crudo")}, ensure_ascii=False) + "\n")

    print("-" * 112)
    if tiempos:
        print(f"[cerebro] válidas {aciertos}/{len(FRASES)} · mediana {sorted(tiempos)[len(tiempos)//2]} ms "
              f"por frase · RAM libre al final {ram_libre_mb()} MB")
    print(f"[cerebro] registro en {REGISTRO}")
    if args.parar_ollama:
        try:
            urllib.request.urlopen(OLLAMA + "/api/generate",
                                   data=json.dumps({"model": args.modelo, "prompt": "",
                                                   "keep_alive": 0}).encode(), timeout=8).read()
        except Exception:
            pass
        print("[cerebro] modelo liberado (keep_alive=0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
