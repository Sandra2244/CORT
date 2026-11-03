"""S1 — el escáner de capacidades de CORT (la adaptabilidad que pidió Sandra).

CORT no puede pedirle a una máquina lo que la máquina no tiene, y tampoco conformarse
con lo que tenía la última vez. Este módulo mira el equipo **ahora** y saca dos cosas:

  1. un **nivel de cerebro**: hasta dónde puede llegar sin congelar nada, y
  2. un **plan de degradación**: qué se apaga para que lo importante quepa.

Nada de esto es inventado: cada número viene de `/proc`, de `sysfs` o de una llamada
medida. Si algo no se puede saber, el campo dice `no disponible` y el nivel baja.

    python3 cort-bridge/cort_perfil.py        # informe por consola
"""
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# MB libres que hace falta para cada escalón. Son medidas, no deseos: el modelo más
# ligero que está en disco (258 MB de peso) pide ~511 MB según la cuenta del puente.
PISO_LIGERO = 512
PISO_GRANDE = 2048

# Lo que se puede apagar, con clave de máquina y con rótulo para leer. El nivel decide
# las claves; `plan()` las traduce a valores que la interfaz y el puente obedecen.
APAGAR = {
    "orbe30": "orbe a 30 fps",
    "orbe24": "orbe a 24 fps",
    "scanlines": "scanlines del HUD",
    "voz_natural": "voz natural (usar espeak-ng)",
    "escucha": "escucha continua del micrófono",
    "vision": "los gestos con cámara",
}


def _primera_linea(ruta):
    try:
        return Path(ruta).read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except OSError:
        return ""


def cpu():
    """Modelo, núcleos, MHz y los juegos de instrucciones que de verdad trae el chip."""
    texto = ""
    try:
        texto = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    modelos = re.findall(r"^model name\s*:\s*(.+)$", texto, re.M)
    flags = set()
    for linea in texto.splitlines():
        if linea.startswith("flags"):
            flags = set(linea.split(":", 1)[1].split())
            break
    mhz = [float(x) for x in re.findall(r"^cpu MHz\s*:\s*([\d.]+)", texto, re.M)]
    nucleos = os.cpu_count() or 0
    carga = round(os.getloadavg()[0], 2)
    return {
        "modelo": modelos[0].strip() if modelos else "no disponible",
        "nucleos": nucleos,
        "mhz": round(sum(mhz) / len(mhz)) if mhz else 0,
        "avx2": "avx2" in flags,
        "avx": "avx" in flags,
        "sse42": "sse4_2" in flags,
        "carga_1min": carga,
    }


def memoria():
    libre = total = swap_libre = swap_total = 0
    try:
        for linea in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            clave, valor = linea.split(":", 1)
            mb = int(valor.strip().split()[0]) // 1024
            if clave == "MemAvailable":
                libre = mb
            elif clave == "MemTotal":
                total = mb
            elif clave == "SwapFree":
                swap_libre = mb
            elif clave == "SwapTotal":
                swap_total = mb
    except (OSError, ValueError):
        pass
    return {"libre_mb": libre, "total_mb": total,
            "swap_libre_mb": swap_libre, "swap_total_mb": swap_total}


def disco():
    try:
        u = shutil.disk_usage(str(Path.home()))
        return {"libre_mb": u.free // 1024 // 1024, "total_mb": u.total // 1024 // 1024}
    except OSError:
        return {"libre_mb": 0, "total_mb": 0}


def gpu():
    """Qué acelerador hay. Sin `nvidia-smi` y sin CUDA no hay GPU útil para un modelo."""
    tarjetas = sorted(p.name for p in Path("/dev/dri").glob("*")) if Path("/dev/dri").is_dir() else []
    descripcion = ""
    if shutil.which("lspci"):
        try:
            r = subprocess.run(("lspci",), capture_output=True, text=True, timeout=4)
            for linea in r.stdout.splitlines():
                if "VGA" in linea or "Display" in linea:
                    descripcion = linea.split(":", 1)[-1].strip()
                    break
        except Exception:
            pass
    nvidia = bool(shutil.which("nvidia-smi"))
    etiqueta = descripcion
    for recorta in (r"^[0-9a-fA-F:.]+\s+",
                    r"(VGA compatible controller|Display controller|3D controller):\s*",
                    r"^(Intel|NVIDIA|Advanced Micro Devices|Arm|Vivante|Imagination)[^:]*?Corporation\s*"):
        etiqueta = re.sub(recorta, "", etiqueta, flags=re.I)
    etiqueta = etiqueta.strip() or "no disponible"
    if len(etiqueta) > 40:
        etiqueta = etiqueta[:39].rstrip() + "…"
    return {"nodos_dri": tarjetas, "descripcion": descripcion or "no disponible",
            "etiqueta": etiqueta, "cuda": nvidia}


def camara():
    """Las cámaras que el kernel ve. Que existan no significa que den cuadros: eso lo
    mide `cort_vision`, y aquí sólo se declara lo que hay."""
    rutas = sorted(Path("/sys/class/video4linux").glob("video*")) if Path("/sys/class/video4linux").is_dir() else []
    nombres = []
    for r in rutas:
        nombre = _primera_linea(str(r / "name"))
        nombres.append({"nodo": f"/dev/{r.name}", "nombre": nombre or "sin nombre"})
    return nombres


def temperatura():
    """Grados medidos del silicio, con el nombre del sensor. Sirve para saber si la
    máquina está sufriendo antes de pedirle un modelo más."""
    mejor = None
    for zona in sorted(Path("/sys/class/thermal").glob("thermal_zone*")) if Path("/sys/class/thermal").is_dir() else []:
        try:
            mil = int(_primera_linea(str(zona / "temp")))
            if mil > 0:
                tipo = _primera_linea(str(zona / "type")) or zona.name
                if mejor is None or mil > mejor["milicelsius"]:
                    mejor = {"sensor": tipo, "milicelsius": mil}
        except ValueError:
            continue
    return {"celsius": round(mejor["milicelsius"] / 1000, 1) if mejor else None,
            "sensor": mejor["sensor"] if mejor else "no disponible"}


def nivel(caps, ollama_vivo=False, modelos=None):
    """El escalón al que puede aspirar este equipo ahora mismo, y por qué no más arriba.

    `se_apaga` lleva claves de máquina (las de `APAGAR`); el texto que lee la usuaria
    sale de esas mismas claves, así que la pantalla no puede contar algo distinto de
    lo que el puente va a hacer.
    """
    m = caps["memoria"]
    c = caps["cpu"]
    modelos = modelos or {}

    def etiqueta(n, nombre, motivo, apaga):
        return {"nivel": n, "nombre": nombre, "motivo": motivo,
                "se_apaga": list(apaga),
                "se_apaga_texto": [APAGAR[k] for k in apaga]}

    def sin_camara():
        return [] if caps.get("camara") else ["vision"]

    ligeros = [k for k, info in modelos.items()
               if (info.get("ram_est") or info.get("ram_uso") or 9e9) <= PISO_LIGERO]

    if not ollama_vivo:
        return etiqueta(0, "reglas locales",
                        "Ollama no está vivo: CORT responde con reglas, sensores y "
                        "mandos reales, y no finge un modelo",
                        ["orbe30", "scanlines"] + sin_camara())
    if not (c["avx2"] or c["avx"]):
        return etiqueta(0, "reglas locales",
                        f"{c['modelo']} no trae AVX ni AVX2: los binarios oficiales de "
                        f"llama.cpp piden esas instrucciones y revientan con 'Illegal "
                        f"instruction'. Hace falta un motor sin AVX o un modelo que no "
                        f"necesite transformer.cpp",
                        ["orbe30", "scanlines", "voz_natural"] + sin_camara())
    if caps["gpu"]["cuda"] and m["libre_mb"] >= PISO_LIGERO:
        return etiqueta(3, "modelo con GPU",
                        f"hay CUDA y {m['libre_mb']} MB libres: el modelo trabaja "
                        f"acelerado y deja RAM para la interfaz",
                        sin_camara())
    if m["libre_mb"] >= PISO_GRANDE:
        return etiqueta(2, "modelo completo en CPU",
                        f"{m['libre_mb']} MB libres y {c['modelo']} con AVX: cabe un "
                        f"modelo completo, aunque irá a 1–2 tokens/s",
                        sin_camara())
    if m["libre_mb"] >= PISO_LIGERO and ligeros:
        return etiqueta(1, "modelo ligero",
                        f"{m['libre_mb']} MB libres alcanzan para "
                        f"{', '.join(sorted(ligeros)[:3])}",
                        ["orbe24", "scanlines", "escucha"] + sin_camara())
    return etiqueta(0, "reglas locales",
                    f"Ollama está vivo pero sólo hay {m['libre_mb']} MB libres y el piso "
                    f"del modelo ligero es {PISO_LIGERO}"
                    + ("" if ligeros else "; además en disco no hay ningún modelo por debajo de ese piso"),
                    ["orbe24", "scanlines", "voz_natural", "escucha"] + sin_camara())


def plan(caps, info_nivel):
    """Los valores concretos que el puente y la interfaz obedecen según el nivel.

    Aquí es donde el escaneo deja de ser un cartel y pasa a ser comportamiento: con
    el nivel 0 la interfaz no gasta fotogramas ni el puente carga el modelo de Piper.
    """
    apaga = set(info_nivel.get("se_apaga") or [])
    fps = 24 if "orbe24" in apaga else 30 if "orbe30" in apaga else 60
    return {
        "orbe_fps": fps,
        "scanlines": "scanlines" not in apaga,
        "voz_natural": "voz_natural" not in apaga,
        "escucha_continua": "escucha" not in apaga,
        "vision": "vision" not in apaga,
        "nivel": info_nivel.get("nivel", 0),
    }


def resumen(caps):
    """Una frase para decir en voz alta: nivel, el número que lo decide y qué se apagó."""
    n = caps["nivel"]
    m = caps["memoria"]
    c = caps["cpu"]
    extra = f". Se apagan: {', '.join(n['se_apaga_texto'])}" if n.get("se_apaga_texto") else ""
    return (f"Nivel {n['nivel']} ({n['nombre']}): {c['modelo']} con {c['nucleos']} núcleos, "
            f"{m['libre_mb']} de {m['total_mb']} megabytes libres. {n['motivo']}{extra}.")


def informe(ollama_vivo=False, modelos=None, audio=None, caps=None):
    """Todo junto, con la marca de tiempo de la medición.

    `caps` permite medir un equipo distinto del que corre el código (lo usan las
    pruebas); si no se pasa, se escanea el equipo actual.
    """
    caps = caps or {"cpu": cpu(), "memoria": memoria(), "disco": disco(), "gpu": gpu(),
                    "camara": camara(), "temperatura": temperatura()}
    caps.setdefault("audio", audio or {"nota": "sin sondeo de audio"})
    info = nivel(caps, ollama_vivo=ollama_vivo, modelos=modelos)
    caps["nivel"] = info
    caps["plan"] = plan(caps, info)
    caps["medido_en"] = time.strftime("%Y-%m-%d %H:%M:%S")
    caps["origen"] = "real"
    return caps


if __name__ == "__main__":
    import json
    print(json.dumps(informe(), ensure_ascii=False, indent=2))
