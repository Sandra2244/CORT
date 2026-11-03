#!/usr/bin/env python3
"""S1 — prueba del escáner de capacidades con equipos fingidos.

Lo que se comprueba no es el número de esta laptop (ése se ve en la pantalla), sino
la **decisión**: que un chip sin AVX no reciba un nivel 2 aunque tenga 32 GB, que un
equipo con CUDA suba al escalón 3, que lo que se apaga en el texto sea exactamente lo
que el plan ordena apagar, y que sin Ollama vivo el nivel sea 0 con el motivo dicho.

    .venv/bin/python scripts/prueba_perfil.py
"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cort-bridge"))
import cort_perfil  # noqa: E402

BASE = {
    "cpu": {"modelo": "Intel Celeron N2805", "nucleos": 2, "mhz": 1467,
            "avx2": False, "avx": False, "sse42": True, "carga_1min": 5.9},
    "memoria": {"libre_mb": 348, "total_mb": 1851, "swap_libre_mb": 1789, "swap_total_mb": 2949},
    "disco": {"libre_mb": 217249, "total_mb": 299111},
    "gpu": {"nodos_dri": ["card0"], "descripcion": "Intel Atom Z36xxx", "cuda": False},
    "camara": [{"nodo": "/dev/video0", "nombre": "USB 2.0 Camera"}],
    "temperatura": {"celsius": 49.0, "sensor": "TCPU"},
}
LIGERO = {"smollm2:135m": {"mb": 258, "ram_est": 511}}


ULTIMO = {}


def caso(nombre, caps, ollama, modelos, esperaNivel, esperado_en_plan, no_espera=None):
    caps = copy.deepcopy(caps)
    info = cort_perfil.nivel(caps, ollama_vivo=ollama, modelos=modelos)
    plan = cort_perfil.plan(caps, info)
    fallos = []
    if info["nivel"] != esperaNivel:
        fallos.append(f"nivel {info['nivel']} ≠ {esperaNivel}")
    for clave, valor in esperado_en_plan.items():
        if plan.get(clave) != valor:
            fallos.append(f"plan.{clave}={plan.get(clave)!r} ≠ {valor!r}")
    # el texto y la clave tienen que decir lo mismo, o la pantalla miente
    if len(info["se_apaga"]) != len(info["se_apaga_texto"]):
        fallos.append("se_apaga y se_apaga_texto no coinciden")
    for prohibida in (no_espera or []):
        if prohibida in info["se_apaga"]:
            fallos.append(f"apagó «{prohibida}» sin venir a caso")
    ULTIMO.clear()
    ULTIMO.update(info=info, plan=plan)
    return (nombre, not fallos,
            f"nivel {info['nivel']} ({info['nombre']}) · "
            + (" · ".join(fallos) if fallos else
               f"plan {plan['orbe_fps']} fps, scanlines {plan['scanlines']}, "
               f"voz natural {plan['voz_natural']}, escucha {plan['escucha_continua']}, "
               f"visión {plan['vision']}"))


def con(**cambios):
    c = copy.deepcopy(BASE)
    for ruta, valor in cambios.items():
        nodo, clave = ruta.split("__")
        c[nodo][clave] = valor
    return c


def main():
    resultados = []

    # 1 · la Canaima real: sin AVX, con lo que haya en disco, Ollama vivo o no.
    resultados.append(caso("sin AVX (Canaima)", BASE, True, LIGERO, 0,
                           {"orbe_fps": 30, "scanlines": False, "voz_natural": False},
                           no_espera=["escucha", "vision"]))
    r = ULTIMO["info"]
    resultados.append(("el motivo nombra la instrucción que falta",
                       "AVX" in r["motivo"] and "Illegal instruction" in r["motivo"],
                       r["motivo"][:68]))

    # 2 · Ollama apagado: nivel 0 con el motivo honesto, y no se apaga la voz.
    resultados.append(caso("Ollama apagado", BASE, False, {}, 0,
                           {"voz_natural": True, "orbe_fps": 30},
                           no_espera=["voz_natural"]))

    # 3 · mismo chip sin AVX pero con 16 GB: sigue en 0. La RAM no compra instrucciones.
    resultados.append(caso("sin AVX con mucha RAM",
                           con(memoria__libre_mb=15000), True, LIGERO, 0,
                           {"orbe_fps": 30}, no_espera=[]))

    # 4 · CPU con AVX y RAM justa: modelo ligero, y aquí sí se apaga la escucha.
    con_avx = con(cpu__avx=True, cpu__avx2=True, cpu__modelo="Intel i5-8250U",
                  memoria__libre_mb=700)
    resultados.append(caso("AVX + 700 MB (ligero)", con_avx, True, LIGERO, 1,
                           {"orbe_fps": 24, "scanlines": False, "escucha_continua": False}))

    # 5 · AVX y RAM grande: escalón 2, nada se apaga.
    resultados.append(caso("AVX + 4 GB (completo)",
                           con(memoria__libre_mb=4096, cpu__avx=True, cpu__avx2=True,
                               cpu__modelo="Intel i7"), True, LIGERO, 2,
                           {"orbe_fps": 60, "scanlines": True, "escucha_continua": True}))

    # 6 · GPU CUDA: el escalón 3, con 60 fps y todo encendido.
    resultados.append(caso("CUDA (portátil grande)",
                           con(gpu__cuda=True, memoria__libre_mb=8000, cpu__avx2=True,
                               cpu__modelo="Ryzen 7"), True, LIGERO, 3,
                           {"orbe_fps": 60, "vision": True}))

    # 7 · AVX, RAM suficiente, pero NINGÚN modelo por debajo del piso: no promete nivel 1.
    resultados.append(caso("AVX y sin modelo ligero",
                           con(memoria__libre_mb=700, cpu__avx=True), True,
                           {"qwen2.5:7b": {"mb": 4700, "ram_est": 5200}}, 0,
                           {"voz_natural": False}))

    # 8 · sin cámara: los gestos se apagan solos, con su motivo.
    sin_cam = copy.deepcopy(BASE)
    sin_cam["camara"] = []
    resultados.append(caso("sin cámara", sin_cam, False, {}, 0,
                           {"vision": False}))
    resultados.append(("el apagado dice «gestos»",
                       "vision" in ULTIMO["info"]["se_apaga"] and
                       "los gestos con cámara" in ULTIMO["info"]["se_apaga_texto"],
                       str(ULTIMO["info"]["se_apaga_texto"])))

    # 9 · el resumen hablado trae el número que decide, no un adjetivo.
    info = cort_perfil.nivel(BASE, ollama_vivo=True, modelos=LIGERO)
    caps = copy.deepcopy(BASE)
    caps["nivel"] = info
    texto = cort_perfil.resumen(caps)
    resultados.append(("resumen hablado con cifras",
                       "348" in texto and "1851" in texto and "Nivel 0" in texto,
                       texto[:70] + "…"))

    # 10 · el equipo de verdad, medido ahora (no se afirma nada que no esté en /proc).
    real = cort_perfil.informe()
    resultados.append(("medida real: origen y marcas",
                       real["origen"] == "real" and real["cpu"]["nucleos"] >= 1 and
                       real["memoria"]["libre_mb"] > 0 and "plan" in real and
                       real["medido_en"],
                       f"{real['cpu']['modelo'][:26]} · {real['memoria']['libre_mb']} MB · "
                       f"AVX {real['cpu']['avx']} · nivel {real['nivel']['nivel']}"))
    resultados.append(("medida real: el nivel nunca supera lo que el chip permite",
                       (real["nivel"]["nivel"] == 0) or real["cpu"]["avx"] or real["cpu"]["avx2"],
                       f"nivel {real['nivel']['nivel']} con AVX={real['cpu']['avx']}"))

    # 11 · claves de apagado válidas: una clave sin rótulo sería un cartel vacío.
    resultados.append(("todas las claves tienen rótulo",
                       all(k in cort_perfil.APAGAR for k in info["se_apaga"]),
                       str(info["se_apaga"])))

    for nombre, ok, detalle in resultados:
        print(f"{'ok  ' if ok else 'FALLO'} {nombre:<52} {detalle}")
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados)} casos · fallos: {len(fallos)}")
    return 0 if not fallos else 1


if __name__ == "__main__":
    sys.exit(main())
