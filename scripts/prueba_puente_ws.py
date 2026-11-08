#!/usr/bin/env python3
"""F20a — la puerta del /ws, el emparejamiento del teléfono y el TLS de la casa.

Lo que se juega aquí, en orden de gravedad:

* que la cara local (cort-web) siga entrando al /ws SIN llave desde 127.0.0.1,
  y que cualquiera que venga de fuera necesite el ?token= — con 401 dicho en
  español y sin hacer el upgrade;
* que `mobile_auth` conteste de verdad: ok:false con la llave mala, ok:true con
  la buena, con el perfil del equipo y las capacidades medidas — y que el token
  no vuelva jamás en la respuesta;
* que el certificado de la casa se genere con el openssl que ya hay (sin
  instalar nada), con los SAN y los días pedidos, en 0600, que `generar` no pise
  un par existente y que la huella sea la misma cuenta que la de openssl.

Todo corre en una arena (`CORT_HOME`, `CORT_DATOS`, `CORT_STATE` temporales) y en
un puerto efímero que decide el sistema: el puente vivo de la dueña (8765/8766)
no se toca ni se mira. El clima se apaga en esta arena porque saldría a internet
(ipapi/open-meteo) y aquí no se prueba el clima.

    python3 scripts/prueba_puente_ws.py

Sale con 0 si todo cuadra y con 1 si algo falta; cada línea está dicha en español.
"""

import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARENA = Path(tempfile.mkdtemp(prefix="cort-arena-ws-"))
LLAVE = "llave-de-arena-para-el-ws"
MALA = "la-llave-que-no-es"

# Antes de importar: los módulos leen estas variables en tiempo de importación.
os.environ.update({
    "CORT_HOME": str(ARENA),
    "CORT_DATOS": str(ARENA / "datos"),
    "CORT_STATE": str(ARENA / "cort_state.json"),
    "CORT_TMP": str(ARENA / "tmp-voz"),
    "CORT_TOKEN": LLAVE,
    "CORT_VOZ": "0", "CORT_MIC": "0", "CORT_NUCLEO": "0",
    "CORT_ACTUALIZA": "0", "CORT_AUTOSONDA": "0",
    "CORT_OLLAMA": "http://127.0.0.1:1",      # no hay cerebro en esta prueba
    "OLLAMA_MODELOS": str(ARENA / "modelos"),
    "CORT_TLS": "", "CORT_TLS_AUTO": "0",
})
sys.path.insert(0, str(RAIZ / "cort-bridge"))

import aiohttp                      # noqa: E402  (el mismo que usa el puente de la casa)
from aiohttp import web             # noqa: E402
import cort_enlace                  # noqa: E402  (necesita la arena montada)
import cort_server                  # noqa: E402
import cort_tls                     # noqa: E402

# El empuje de la conexión saldría a ipapi/open-meteo a preguntar el clima: en la
# arena no hay red fuera de casa, así que se contesta lo mismo que el puente
# cuando el servicio no responde. El resto del empuje (perfil, voz, memoria) es real.
cort_server.clima = lambda ciudad="": {"ok": False, "motivo": "arena sin clima"}

RESULTADOS = []


def prueba(nombre, cumple, detalle=""):
    RESULTADOS.append((nombre, bool(cumple), detalle))
    print(f"  [{'ok  ' if cumple else 'FALLO'}] {nombre}" + ("" if cumple else f" — {detalle}"))


def openssl(*args):
    return subprocess.run([shutil.which("openssl"), *args],
                          capture_output=True, text=True, timeout=30)


# --------------------------------------------------------------- el TLS de la casa
def pruebas_tls():
    print("\n== cort_tls: el certificado de la casa ==")
    if not shutil.which("openssl"):
        prueba("hay openssl para generar (sin instalar nada)", False, "no está en el PATH")
        return
    directorio = ARENA / "tls"
    cert, clave = cort_tls.generar(directorio)
    prueba("generar devuelve el par y los dos existen",
           Path(cert).is_file() and Path(clave).is_file(), f"{cert}, {clave}")
    prueba("certificado y clave nacen en 0600",
           (Path(cert).stat().st_mode & 0o777) == 0o600
           and (Path(clave).stat().st_mode & 0o777) == 0o600,
           f"{oct(Path(cert).stat().st_mode & 0o777)}, {oct(Path(clave).stat().st_mode & 0o777)}")
    h1, h2 = cort_tls.huella(cert), cort_tls.huella(cert)
    prueba("la huella es estable y son 64 hex", h1 == h2 and re.fullmatch(r"[0-9a-f]{64}", h1) is not None, h1)
    r = openssl("x509", "-in", cert, "-noout", "-fingerprint", "-sha256")
    de_openssl = r.stdout.strip().split("=")[-1].replace(":", "").lower()
    prueba("la huella es la misma cuenta que `openssl x509 -fingerprint -sha256`",
           h1 == de_openssl, f"mía {h1} · openssl {de_openssl}")
    antes = (Path(cert).read_bytes(), Path(cert).stat().st_mtime_ns,
             Path(clave).read_bytes(), Path(clave).stat().st_mtime_ns)
    cert2, clave2 = cort_tls.generar(directorio)
    despues = (Path(cert).read_bytes(), Path(cert).stat().st_mtime_ns,
               Path(clave).read_bytes(), Path(clave).stat().st_mtime_ns)
    prueba("generar dos veces NO pisa el par existente (la huella fijada sigue valiendo)",
           (cert2, clave2) == (cert, clave) and antes == despues)
    r = openssl("x509", "-in", cert, "-noout", "-text")
    prueba("la clave es RSA de 2048 bits", "Public-Key: (2048 bit)" in r.stdout)
    r = openssl("x509", "-in", cert, "-noout", "-ext", "subjectAltName")
    san = r.stdout
    prueba("los SAN llevan localhost y 127.0.0.1", "DNS:localhost" in san and "127.0.0.1" in san, san.strip())
    ips = cort_tls.ips_de_la_maquina()
    prueba("los SAN llevan cada IPv4 no loopback leída del equipo",
           all(("IPAddress:" + ip) in san.replace(" ", "") for ip in ips)
           and all(not ip.startswith("127.") for ip in ips), str(ips))
    prueba("vigencia de 825 días: no vence en 824, sí vence en 826",
           openssl("x509", "-in", cert, "-noout", "-checkend", str(824 * 86400)).returncode == 0
           and openssl("x509", "-in", cert, "-noout", "-checkend", str(826 * 86400)).returncode == 1)
    e = cort_tls.estado(directorio)
    prueba("estado describe el par con su huella",
           e["existe"] is True and e["huella"] == h1 and e["cert"] == cert, str(e))

    print("\n== el arranque automático (CORT_TLS_AUTO) y el enlace ==")
    prueba("sin CORT_TLS_AUTO no se usa nada aunque exista el par", cort_tls.rutas_auto() == "")
    # El par de la carpeta por defecto: la misma donde vive la llave del enlace.
    cert_auto, clave_auto = cort_tls.generar()
    prueba("la carpeta por defecto es la de la llave del enlace",
           Path(cert_auto).parent == cort_enlace.DATOS, str(cert_auto))
    os.environ["CORT_TLS_AUTO"] = "1"
    prueba("con CORT_TLS_AUTO=1 y par existente, rutas_auto da el formato de CORT_TLS",
           cort_tls.rutas_auto() == f"{cert_auto},{clave_auto}")
    prueba("enlace_del_puente dice https con el automático puesto",
           cort_enlace.enlace_del_puente("192.168.1.19", 8765, LLAVE).startswith("https://"))
    https, huella = cort_enlace.tls_del_puente()
    prueba("tls_del_puente da (True, huella del par)", https is True and huella == cort_tls.huella(cert_auto))
    os.environ["CORT_TLS"] = "/no/existe.pem,/no/existe.key"
    prueba("el CORT_TLS explícito manda sobre el automático",
           cort_enlace.tls_del_puente() == (True, ""))
    os.environ["CORT_TLS"] = ""
    # La decisión del QR: el cuadro lleva sólo la dirección. Meter la huella dentro
    # lo haría más denso; aquí se mide que es verdad, no se supone.
    url = cort_enlace.enlace_del_puente("192.168.1.19", 8765, LLAVE)
    lado_solo = len(cort_enlace.qr_matriz(url) or [])
    lado_con_huella = len(cort_enlace.qr_matriz(url + "&huella=" + huella) or [])
    prueba("la huella en el QR lo haría más denso (por eso viaja en el GET con llave)",
           lado_con_huella > lado_solo > 0, f"lado {lado_solo} -> {lado_con_huella}")


# ------------------------------------------------------------------ la puerta /ws
def pruebas_puerta():
    print("\n== la puerta del /ws: casa sin llave, fuera con llave ==")
    f = cort_server.es_de_casa
    prueba("son de casa 127.0.0.1, ::1 y la IPv4 vista desde IPv6",
           f("127.0.0.1") and f("127.0.0.53") and f("::1") and f("::ffff:127.0.0.1"))
    prueba("NO son de casa la IP del Wi-Fi, None ni una cadena que no es IP",
           not f("192.168.1.40") and not f("10.0.0.5") and not f(None) and not f("") and not f("no-es-ip"))
    g = cort_server.entrada_ws_autorizada
    prueba("desde casa se entra sin token (la cara local sigue viva)", g("127.0.0.1", None, LLAVE))
    prueba("desde fuera sin token NO se entra", not g("192.168.1.40", None, LLAVE))
    prueba("desde fuera con el token malo NO se entra", not g("192.168.1.40", MALA, LLAVE))
    prueba("desde fuera con la llave buena se entra", g("192.168.1.40", LLAVE, LLAVE))
    prueba("sin llave configurada nadie entra de fuera", not g("192.168.1.40", LLAVE, ""))
    prueba("mobile_auth salió del panel de órdenes sin backend",
           "mobile_auth" not in cort_server.FALTA_EN_EL_PUENTE
           and "mobile_auth" not in cort_server.PANEL_DE_ORDEN)

    async def pedido_de_fuera():
        # Un pedido falso con IP de fuera: ws_handler debe contestar 401 SIN llegar
        # a preparar el WebSocket (por eso el falso no tiene nada de ws).
        falso = type("Pedido", (), {"remote": "192.168.1.40", "query": {}})()
        return await cort_server.ws_handler(falso)

    resp = asyncio.run(pedido_de_fuera())
    cuerpo = json.loads(resp.body)
    prueba("de fuera sin token: HTTP 401 sin upgrade, con JSON {ok:false, motivo}",
           resp.status == 401 and cuerpo.get("ok") is False and cuerpo.get("motivo"), str(cuerpo))
    prueba("el motivo está en español y pide el token", "token" in cuerpo.get("motivo", ""), cuerpo.get("motivo", ""))
    prueba("el 401 no dice cuál es la llave buena", LLAVE not in resp.body.decode())


# ---------------------------------------------------- el WebSocket de verdad, en arena
async def espera_tipo(ws, tipo, plazo=30):
    """Lee hasta que llegue el mensaje pedido; los empujes de la conexión se saltan."""
    fin = time.monotonic() + plazo
    while True:
        restante = fin - time.monotonic()
        if restante <= 0:
            return {"type": "(silencio)", "ok": None}
        m = await asyncio.wait_for(ws.receive_json(), timeout=restante)
        if m.get("type") == tipo:
            return m


async def ensayo_ws():
    app = web.Application()
    app.router.add_get("/ws", cort_server.ws_handler)
    cort_enlace.registro(app, LLAVE)
    runner = web.AppRunner(app)
    await runner.setup()
    # Puerto 0: uno libre que decide el sistema. Nunca 8765/8766, que son de la dueña.
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    puerto = site._server.sockets[0].getsockname()[1]
    base = f"http://127.0.0.1:{puerto}"
    cosas = {}
    try:
        async with aiohttp.ClientSession() as ses:
            async with ses.ws_connect(base + "/ws") as ws:
                primero = await asyncio.wait_for(ws.receive_json(), timeout=20)
                cosas["conecta_sin_llave"] = primero.get("type") == "connected"

                await ws.send_json({"type": "mobile_auth", "token": MALA,
                                    "dispositivo": "Pixel de arena", "version": "0.13.0"})
                r = await espera_tipo(ws, "mobile_auth_result")
                crudo = json.dumps(r, ensure_ascii=False)
                cosas["mala"] = (r.get("ok"), r.get("motivo", ""), crudo)

                await ws.send_json({"type": "mobile_auth", "token": LLAVE,
                                    "dispositivo": "Pixel de arena", "version": "0.13.0"})
                r2 = await espera_tipo(ws, "mobile_auth_result")
                cosas["buena"] = r2
                cosas["buena_cruda"] = json.dumps(r2, ensure_ascii=False)

            # El GET del enlace con la llave: aquí viaja la huella, no en el QR.
            async with ses.get(base + cort_enlace.RUTA + f"?token={LLAVE}") as resp:
                cosas["cuadro"] = await resp.json()
        if cort_server.MUESTREO is not None:
            cort_server.MUESTREO.cancel()
    finally:
        await runner.cleanup()
    return cosas


def pruebas_ws():
    print("\n== mobile_auth, con el puente de arena delante (puerto efímero) ==")
    os.environ["CORT_TLS_AUTO"] = "1"     # el GET debe traer la huella del par generado
    cosas = asyncio.run(ensayo_ws())
    os.environ["CORT_TLS_AUTO"] = "0"
    prueba("la cara local conecta al /ws SIN token y recibe `connected`", cosas["conecta_sin_llave"])
    ok, motivo, crudo = cosas["mala"]
    prueba("mobile_auth con la llave mala: ok:false con motivo en español",
           ok is False and bool(motivo), f"ok={ok} motivo={motivo}")
    prueba("la respuesta mala no lleva ningún token (ni el malo ni el bueno)",
           MALA not in crudo and LLAVE not in crudo)
    r2 = cosas["buena"]
    prueba("mobile_auth con la llave buena: ok:true y origen real",
           r2.get("ok") is True and r2.get("origen") == "real", str(r2.get("motivo", "")))
    prueba("la respuesta buena tampoco devuelve el token", LLAVE not in cosas["buena_cruda"])
    prueba("dice qué máquina es (el hostname del equipo)",
           r2.get("maquina") == socket.gethostname(), str(r2.get("maquina")))
    perfil = r2.get("perfil") or {}
    prueba("el perfil es el de `perfil_equipo` (reutilizado, con su origen)",
           isinstance(perfil, dict) and perfil.get("origen") in ("real", "no disponible")
           and ("nivel" in perfil if perfil.get("origen") == "real" else "motivo" in perfil),
           str(perfil.get("origen")))
    caps = r2.get("capacidades")
    prueba("las capacidades son el censo de módulos cargados",
           isinstance(caps, list) and all(isinstance(c, str) for c in caps)
           and "memoria" in caps and "enlace_memoria" in caps, str(caps))
    estado = json.loads(Path(os.environ["CORT_STATE"]).read_text(encoding="utf-8"))
    movil = (estado.get("moviles") or {}).get("Pixel de arena") or {}
    prueba("el nombre del aparato quedó en el estado persistido, con hora y versión",
           bool(movil.get("hora")) and movil.get("version") == "0.13.0", str(movil))
    prueba("en el estado persistido no está el token", LLAVE not in json.dumps(estado, ensure_ascii=False))
    tls = (cosas["cuadro"] or {}).get("tls") or {}
    prueba("el GET /memoria/puente trae {https, huella} para el pin del teléfono",
           tls.get("https") is True and re.fullmatch(r"[0-9a-f]{64}", tls.get("huella", "")) is not None,
           str(tls))
    prueba("el cuadro del enlace sigue sin llevar la llave dentro",
           LLAVE not in json.dumps(cosas["cuadro"], ensure_ascii=False))
    prueba("quitado el automático, el enlace vuelve a decir http",
           cort_enlace.enlace_del_puente("192.168.1.19", 8765, LLAVE).startswith("http://"))


def main():
    print("== F20a: /ws con llave fuera de casa, mobile_auth y TLS de la casa ==")
    pruebas_tls()
    pruebas_puerta()
    pruebas_ws()
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