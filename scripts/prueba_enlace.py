#!/usr/bin/env python3
"""Las costuras del enlace PC ↔ teléfono (F14), comprobadas sin teléfono delante.

Tres cosas se prueba aquí, y las tres son de las que duelen si fallan:

1. **El contrato que habla el Java.** `apps/android/src/dev/sandra/cort/movil/Puente.java`
   fija la ruta, la versión del cuadro y los tres topes. Este script lee ese archivo y
   compara número por número: si alguien mueve el 300 en Java y no lo mueve aquí, el
   teléfono empieza a rechazar filas que el PC sí sirve, y el fallo se ve como
   «rechazados: 12» sin explicación.
2. **Las cuatro reglas del puente**, con datos puestos: la llave no viaja dentro de un
   recuerdo, fusionar no borra, el dedupe normaliza y los topes se cumplen.
3. **La puerta.** Un `GET` sin `?token=` responde 401 con frase en español, y el puente
   de verdad (aiohttp, puerto 127.0.0.1 que decide el sistema) se levanta en este
   script, no contra el de la dueña: su puente vivo del 8765 no es banco de pruebas.

Todo escribe en una arena (`CORT_DATOS` a un directorio temporal), nunca en la memoria
real de la casa.
"""

import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARENA = Path(tempfile.mkdtemp(prefix="cort-arena-enlace-"))

# Antes de importar: los módulos leen `CORT_DATOS` en tiempo de importación.
os.environ["CORT_DATOS"] = str(ARENA)
os.environ["CORT_TOKEN"] = ""
sys.path.insert(0, str(RAIZ / "cort-bridge"))

import cort_enlace  # noqa: E402  (necesita la arena montada)
import cort_memoria  # noqa: E402

RESULTADOS = []


def prueba(nombre, cumple, detalle=""):
    RESULTADOS.append((nombre, bool(cumple), detalle))
    print(f"  [{'ok  ' if cumple else 'FALLO'}] {nombre}" + ("" if cumple else f" — {detalle}"))


def pone_memoria(hechos):
    """Dejando la arena como si la dueña hubiera hablado un rato."""
    d = {"preferencias": {"nombre": "Sandra"}, "hechos": hechos, "correcciones": []}
    cort_memoria._escribir(d)


def main():
    print("== el contrato compartido con el Java ==")
    java = (RAIZ / "apps/android/src/dev/sandra/cort/movil/Puente.java").read_text(
        encoding="utf-8")

    def const_java(nombre, por_defecto=None):
        m = re.search(r"static final int %s = ([0-9]+);" % nombre, java)
        return int(m.group(1)) if m else por_defecto

    ruta_java = re.search(r'String RUTA = "([^"]+)"', java)
    prueba("la ruta es la misma en los dos lados",
           ruta_java is not None and ruta_java.group(1) == cort_enlace.RUTA,
           f"Java: {ruta_java.group(1) if ruta_java else '?'} · Python: {cort_enlace.RUTA}")
    prueba("la versión del cuadro no se separó",
           const_java("VERSION") == cort_enlace.VERSION,
           f"Java {const_java('VERSION')} · Python {cort_enlace.VERSION}")
    for nombre, valor in (("MAX_CONTENIDO", cort_enlace.MAX_CONTENIDO),
                          ("MAX_FILAS", cort_enlace.MAX_FILAS),
                          ("MAX_BYTES", cort_enlace.MAX_BYTES)):
        prueba(f"el tope {nombre} vale {valor} en los dos lados",
               const_java(nombre) == valor,
               f"Java {const_java(nombre)} · Python {valor}")
    filas_java = re.search(r"filasQueCaben\(\) \{\s*return Math.min\(MAX_FILAS, "
                           r"MAX_BYTES / \(MAX_CONTENIDO \* 3 \+ 64\)\);", java)
    prueba("el tope de filas por cuadro se calcula igual (271)",
           filas_java is not None and cort_enlace.FILAS_QUE_CABEN == 271,
           f"Python {cort_enlace.FILAS_QUE_CABEN}")
    origen_java = re.search(r'String ORIGEN = "([^"]+)"', java)
    prueba("el teléfono se llama `telefono` y el PC `pc`, sin pisarse",
           origen_java is not None and origen_java.group(1) == "telefono"
           and cort_enlace.ORIGEN == "pc",
           f"Java {origen_java.group(1) if origen_java else '?'} · Python {cort_enlace.ORIGEN}")

    print("\n== la llave ==")
    llave = cort_enlace.token()
    prueba("el enlace tiene llave aunque nadie ponga CORT_TOKEN",
           len(llave) >= 16, f"{len(llave)} caracteres")
    modo = oct(cort_enlace.ENLACE.stat().st_mode & 0o777)
    prueba("el archivo de la llave es 0600 (no lo lee otro usuario)", modo == "0o600", modo)
    prueba("la misma llamada dos veces devuelve la misma llave",
           cort_enlace.token() == llave)
    prueba("otra IP distinta no vale (`autorizada` compara en tiempo constante)",
           not cort_enlace.autorizada(llave[:-1] + "x", llave)
           and not cort_enlace.autorizada(None, llave)
           and not cort_enlace.autorizada(llave, ""))

    print("\n== el cuadro que baja el teléfono ==")
    pone_memoria([
        {"clave": "cafe", "texto": "Me gusta  el café   ", "hora": 1_730_000_000},
        {"clave": "examen", "texto": "El examen es en abril", "hora": 1_730_000_500},
        {"clave": "llave", "texto": f"mi token es {llave}", "hora": 1_730_000_600},
        {"clave": "vacio", "texto": "   ", "hora": 1_730_000_700},
        {"clave": "largo", "texto": "x" * 400, "hora": 1_730_000_800},
    ])
    cuadro = cort_enlace.cuadro(llave)
    prueba("los campos que exige el Java están todos",
           all(k in cuadro for k in ("tipo", "version", "origen", "total", "ocultados", "recuerdos")))
    prueba("los cuatro topes se cumplen en el cuadro",
           cuadro["total"] <= cort_enlace.FILAS_QUE_CABEN
           and all(len(r["contenido"]) <= cort_enlace.MAX_CONTENIDO for r in cuadro["recuerdos"]))
    guardados = [r["contenido"] for r in cuadro["recuerdos"]]
    prueba("el recuerdo que llevaba la llave NO viajó (regla 1)",
           not any(llave in c for c in guardados),
           str(guardados))
    prueba("el orden es del más nuevo al más viejo (lo que espera `filas`)",
           [r["cuando"] for r in cuadro["recuerdos"]] ==
           sorted([r["cuando"] for r in cuadro["recuerdos"]], reverse=True))
    prueba("el `cuando` sale en ISO-8601 UTC, que es como lo lee el teléfono",
           re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", cuadro["recuerdos"][0]["cuando"]) is not None,
           cuadro["recuerdos"][0]["cuando"])
    prueba("vacío y larguísimo se cuentan como ocultados, no se callan",
           cuadro["ocultados"] == 3, f"ocultados={cuadro['ocultados']}")
    prueba("espacios corridos: «Me gusta  el café  » llega normalizado",
           "me gusta el café" not in guardados and "Me gusta el café" in guardados,
           str(guardados))
    prueba("el equipaje extra viaja (preferencias, lista, notas)",
           {"preferencias", "lista", "notas"} <= set(cuadro))

    print("\n== lo que sube el teléfono ==")
    pone_memoria([{"clave": "cafe", "texto": "me gusta el café", "hora": 1_730_000_000}])
    sube = {"tipo": "memoria", "version": 1, "origen": "telefono", "total": 4,
            "recuerdos": [
                {"contenido": "Me gusta el café  "},          # ya está, con otro espacio
                {"contenido": "Vivo en Zamora"},               # nuevo
                {"contenido": ""},                            # vacío → rechazado
                {"contenido": f"token {llave}"},               # lleva la llave → rechazado
            ]}
    r = cort_enlace.recibe(sube, llave)
    prueba("el recuento dice 1 nuevo, 1 repetido, 2 rechazados",
           (r["nuevos"], r["repetidos"], r["rechazados"]) == (1, 1, 2), str(r))
    despues = [h["texto"] for h in cort_memoria._leer()["hechos"]]
    prueba("fusionar NO borra: el recuerdo que había sigue en su sitio (regla 2)",
           "me gusta el café" in despues and "Vivo en Zamora" in despues, str(despues))
    prueba("lo rechazado no se escribe nunca", not any("token" in t for t in despues), str(despues))
    prueba("el PC responde con el `origen` y la `versión` que el Java lee",
           r["origen"] == "pc" and r["version"] == 1)

    mal = cort_enlace.recibe({"version": 2, "recuerdos": []}, llave)
    prueba("otra versión del cuadro es error dicho, no fusión a medias",
           not mal["ok"] and "versión" in mal["motivo"], mal.get("motivo", ""))
    sin_lista = cort_enlace.recibe({"version": 1}, llave)
    prueba("un cuadro sin lista de recuerdos es error dicho", not sin_lista["ok"])
    demasido = cort_enlace.recibe({"version": 1, "recuerdos": [{"contenido": f"fila {i}"}
                                                               for i in range(501)]}, llave)
    prueba("501 filas en un viaje se rechazan con el tope en la frase",
           not demasido["ok"] and "tope 500" in demasido["motivo"], demasido.get("motivo", ""))

    print("\n== la puerta, con un puente de verdad delante (puerto efímero) ==")
    from aiohttp import web  # noqa: E402  (el mismo que usa el puente de la casa)

    async def ensayo_http():
        app = web.Application()
        cort_enlace.registro(app, llave)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        puerto = site._server.sockets[0].getsockname()[1]
        base = f"http://127.0.0.1:{puerto}{cort_enlace.RUTA}"
        cosas = {}

        def pide(url, datos=None, metodo=None):
            cuerpo = json.dumps(datos).encode() if datos is not None else None
            peticion = urllib.request.Request(url, data=cuerpo, method=metodo or ("POST" if cuerpo else "GET"))
            # Un 404 de aiohttp no es JSON («404: Not Found» en texto), y la prueba de
            # que-la-estática-sigue-viva lo necesita tal cual.
            def cuerpo_a_diccionario(texto):
                try:
                    return json.loads(texto or "{}")
                except Exception:
                    return {"crudo": texto[:80]}
            try:
                with urllib.request.urlopen(peticion, timeout=5) as respuesta:
                    return respuesta.status, cuerpo_a_diccionario(respuesta.read().decode())
            except urllib.error.HTTPError as e:
                return e.code, cuerpo_a_diccionario(e.read().decode())

        # El cliente es bloqueante (`urllib`), así que se corre en su propio hilo: si
        # llamara desde el mismo lazo del servidor, el lazo no podría contestar y la
        # prueba moriría por reloj, no por contrato. Medido aquí la primera vez.
        async def llama(url, datos=None, metodo=None):
            return await asyncio.to_thread(pide, url, datos, metodo)

        codigo, cuerpo_sin = await llama(base)
        cosas["sin_llave"], cosas["motivo_sin"] = codigo, cuerpo_sin.get("motivo", "")
        codigo, cuadro_bajado = await llama(base + f"?token={llave}")
        cosas["con_llave"], cosas["recuerdos_bajados"] = codigo, cuadro_bajado.get("total")
        codigo, respuesta_sube = await llama(
            base + f"?token={llave}", {"tipo": "memoria", "version": 1, "origen": "telefono",
                                       "recuerdos": [{"contenido": "Tengo cita el martes"}]})
        cosas["sube_ok"], cosas["nuevos"] = codigo, respuesta_sube.get("nuevos")
        codigo, cuadro_final = await llama(base + f"?token={llave}")
        cosas["vuelve_a_bajar"] = codigo
        cosas["en_cuadro_final"] = any("cita el martes" in r["contenido"]
                                       for r in cuadro_final.get("recuerdos", []))
        cosas["peso"], _ = await llama(
            base + f"?token={llave}",
            {"version": 1, "relleno": "x" * (cort_enlace.MAX_BYTES + 10)})
        cosas["ruta_estatica"], _ = await llama(
            base.replace(cort_enlace.RUTA, "/no-existe") + f"?token={llave}")
        await runner.cleanup()
        return cosas

    http = asyncio.run(ensayo_http())
    prueba("GET sin llave: 401", http["sin_llave"] == 401, str(http["sin_llave"]))
    prueba("el 401 trae la frase en español, no un número desnudo",
           "sin llave no hay memoria" in http["motivo_sin"], http["motivo_sin"])
    prueba("GET con llave: 200 y su cuadro", http["con_llave"] == 200 and http["recuerdos_bajados"] >= 1,
           str(http["con_llave"]))
    prueba("POST con llave: escribe y cuenta", http["sube_ok"] == 200 and http["nuevos"] == 1,
           str(http))
    prueba("lo subido por el teléfono se vuelve a bajar del PC (los dos sentidos)",
           http["vuelve_a_bajar"] == 200 and http["en_cuadro_final"])
    prueba("una subida que pasa del tope es 413, no un 500", http["peso"] == 413, str(http["peso"]))
    prueba("el puente sigue sirviendo lo suyo (404 en lo que no existe, no cascos)",
           http["ruta_estatica"] == 404)

    print("\n== el puente de la casa tiene que montar el enlace ==")
    servidor = (RAIZ / "cort-bridge" / "cort_server.py").read_text(encoding="utf-8")
    prueba("`cort_server.py` importa el módulo del enlace", "cort_enlace" in servidor)
    prueba("y registra las dos rutas en la aplicación del core",
           "cort_enlace.registro(" in servidor)
    prueba("el arranque dice dónde está el enlace, para poder escribirlo a mano",
           "memoria compartida" in servidor)

    shutil.rmtree(ARENA, ignore_errors=True)
    totales = len(RESULTADOS)
    buenos = sum(1 for _, ok, _ in RESULTADOS if ok)
    print(f"\nresultado: {buenos}/{totales} comprobaciones")
    if buenos != totales:
        print("sin pasar:")
        for nombre, ok, detalle in RESULTADOS:
            if not ok:
                print(f"  - {nombre}" + (f" ({detalle})" if detalle else ""))
    return 0 if buenos == totales else 1


if __name__ == "__main__":
    sys.exit(main())
