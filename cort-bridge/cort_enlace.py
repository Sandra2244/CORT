#!/usr/bin/env python3
"""CORT enlace (F14): la memoria de la dueña viaja entre el portátil y el teléfono.

El otro lado de este contrato ya está escrito y publicado: es
`apps/android/src/dev/sandra/cort/movil/Puente.java` y su `Sincroniza.java`, que
llaman a `GET` y `POST /memoria/puente?token=…` en el puerto del núcleo (**8765**
en esta rama, no el 8780 de la otra línea). Hasta este módulo esas dos rutas
respondían 404 — `cort_server.py` sólo tenía `POST /mic` y la estática — y el
teléfono lo decía con palabras: «ese puente aún no tiene memoria compartida».

Las cuatro reglas del puente vienen de los cuatro modos en que sincronizar sale
**peor** que no sincronizar, y son las mismas que tiene el Java, número por
número:

1. **La llave de red nunca viaja dentro de un recuerdo.** El endpoint ya está
   protegido por esa llave; metérsela puesta en una fila sería un autorrobo
   elegante. Una fila que la contiene se oculta y se cuenta (`ocultados`).
2. **Fusionar no borra.** Ni aquí ni allá: lo que llega se añade, lo que hay se
   queda. Un teléfono perdido no puede vaciar la memoria de la casa.
3. **El dedupe normaliza** (espacios corridos y minúsculas, con tildes) porque
   «me gusta el café » y «Me gusta el café» son el mismo recuerdo.
4. **Los topes están escritos**: 300 caracteres por fila, 500 filas por viaje,
   262 144 bytes de subida, y 271 filas por cuadro — que es el tope real de un
   viaje, no un número decorativo.

La puerta: **sin token no hay memoria**. El token se lee de `CORT_TOKEN` y, si no
viene puesto, se genera una vez y se guarda en `~/.local/share/cort/enlace.json`
con modo 0600. Así el enlace puede abrirse a la red (`--red`) sin exponer lo que
CORT sabe de ti a cualquiera que esté en el mismo Wi-Fi. La memoria se sirve por
http dentro de la casa, cifrada sólo si el puente arrancó con `CORT_TLS`; se dice
en `docs/ANDROID.md` en vez de prometer más de lo que hace.

Uso sin puente delante (se prueba solo, en una arena):

```
python3 cort-bridge/cort_enlace.py --cuadro      # qué bajaría el teléfono
python3 cort-bridge/cort_enlace.py --enlace      # la dirección con la llave
```
"""

from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

try:
    import cort_memoria
except Exception:  # un puente sin módulo de memoria no ofrece sincronía
    cort_memoria = None

try:
    import cort_vida
except Exception:
    cort_vida = None

# --- el contrato, con los mismos números que `Puente.java` ---------------------
VERSION = 1
TIPO = "memoria"
ORIGEN = "pc"
RUTA = "/memoria/puente"
MAX_CONTENIDO = 300
MAX_FILAS = 500
MAX_BYTES = 262144
FILAS_QUE_CABEN = min(MAX_FILAS, MAX_BYTES // (MAX_CONTENIDO * 3 + 64))  # 271

DATOS = Path(os.environ.get("CORT_DATOS",
                           str(Path.home() / ".local" / "share" / "cort")))
ENLACE = DATOS / "enlace.json"


def espacios(texto):
    """Corriendo los espacios sin tocar las mayúsculas: así llega `Puente.limpia`."""
    return re.sub(r"\s+", " ", (texto or "")).strip()


def normaliza(texto):
    """La misma norma de dedupe que `Puente.normaliza`: espacios corridos y minúsculas.

    Sólo para comparar. **Nunca para guardar**: el texto que viaja conserva las mayúsculas
    de la dueña, y porque pasar todo a minúsculas además de feo rompe la regla 1 — la
    llave de red sale con mayúsculas (`token_urlsafe`) y, una vez minúsculo el recuerdo,
    `llave in texto` ya no la encuentra. Medido en esta suite: con `normaliza` como
    filtro viajó «mi token es e3x-D…» y se escribió en la memoria del portátil.
    """
    return espacios(texto).lower()


def lleva_llave(texto, llave):
    """Si dentro de este recuerdo va la llave del enlace (regla 1, en los dos sentidos)."""
    if not llave:
        return False
    return llave in texto or llave.lower() in texto.lower()


def cuando(hora_epoch):
    """`cuando` en ISO-8601 UTC: es lo que espera leer el teléfono en la fila."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(hora_epoch or 0)))


# --- la llave ------------------------------------------------------------------
def token(nuevo=False):
    """La llave del enlace: `CORT_TOKEN` si está puesta; si no, la guardada.

    Con `nuevo=True` se fuerza una llave nueva y se persiste (es lo que hace
    `--token` al abrir el puente a la red). Se guarda con modo 0600 porque es la
    única puerta que tiene la memoria cuando el puente escucha en la casa.
    """
    entorno = os.environ.get("CORT_TOKEN", "").strip()
    if entorno and not nuevo:
        return entorno
    if not nuevo:
        guardado = _leer_enlace().get("token", "")
        if guardado:
            return guardado
    llave = secrets.token_urlsafe(18)
    _escribir_enlace({"token": llave,
                      "hora": datetime.now().isoformat(timespec="seconds")})
    return llave


def _leer_enlace():
    try:
        with open(ENLACE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _escribir_enlace(d):
    DATOS.mkdir(parents=True, exist_ok=True)
    # Se crea ya con 0600: un archivo de llaves que primero existe con 0644 y se
    # aprieta después es legible por cualquier proceso de la sesión ese instante.
    bandera = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    with open(os.open(ENLACE, bandera, 0o600), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def autorizada(valor, llave):
    """Comparación de tiempo constante: `?token=` es lo único que mira el enlace."""
    if not llave:
        return False
    return hmac.compare_digest(str(valor or ""), str(llave))


# --- el cuadro que se baja -----------------------------------------------------
def cuadro(llave, maximo=FILAS_QUE_CABEN):
    """Lo que el teléfono viene a buscar: los recuerdos del portátil, del más nuevo al más viejo.

    `origen` es `pc` (el Java manda `telefono`) y el `total` es lo que **sale**, no lo
    que hay: si la dueña tiene 400 hechos, el viaje lleva 271 y el resto se queda en
    casa esperando otra vuelta. `ocultados` cuenta las filas que no viajaron por
    vacías, larguísimas o porque llevaban la llave dentro.
    """
    hechos = []
    if cort_memoria is not None:
        hechos = list(reversed(cort_memoria._leer().get("hechos", [])))
    recuerdos = []
    ocultados = 0
    for h in hechos:
        texto = espacios(h.get("texto", ""))
        if not texto or len(texto) > MAX_CONTENIDO or lleva_llave(texto, llave):
            ocultados += 1
            continue
        if len(recuerdos) >= maximo:
            ocultados += 1
            continue
        recuerdos.append({"contenido": texto, "cuando": cuando(h.get("hora"))})
    cuadro_base = {"tipo": TIPO, "version": VERSION, "origen": ORIGEN,
                   "total": len(recuerdos), "ocultados": ocultados,
                   "recuerdos": recuerdos}
    cuadro_base.update(vida())
    return cuadro_base


def vida():
    """El equipaje extra que ya está en el portátil: preferencias, lista y notas.

    El APK publicado (`cort-v0.12.0`) todavía **ignora** estos tres bloques: los mete
    `Sincroniza` en cuanto la cara del teléfono sepa enseñarlos (fase F14c). Viajar
    antes que mostrarse no rompe nada —el Java valida `version` y `recuerdos` y deja
    pasar lo que no conoce—, y así el enlace no vuelve a pedirse un viaje por bloque.
    """
    extra = {}
    if cort_memoria is not None:
        try:
            d = cort_memoria._leer()
            extra["preferencias"] = d.get("preferencias", {})
        except Exception:
            extra["preferencias"] = {}
    if cort_vida is not None:
        try:
            extra["lista"] = cort_vida.compras()
            extra["notas"] = cort_vida.notas()
        except Exception:
            extra["lista"] = []
            extra["notas"] = []
    return extra


def limpia_fila(fila, llave):
    """La misma criba que `Puente.limpia`: controles fuera, vacío y largo fuera, llave fuera."""
    if not isinstance(fila, dict):
        return None
    contenido = espacios(re.sub(r"[\u0000-\u001f\u007f]", " ", str(fila.get("contenido", ""))))
    if not contenido or len(contenido) > MAX_CONTENIDO:
        return None
    if lleva_llave(contenido, llave):
        return None
    return contenido


def recibe(cuerpo, llave):
    """Metiendo los recuerdos del teléfono en la memoria del portátil, **sin borrar nada**.

    Devuelve el recuento que la cara del teléfono enseña (`nuevos`, `repetidos`,
    `rechazados`) más el total que queda en casa. Un cuadro con otra `version`, sin
    lista o con más filas que el tope es error con mensaje en español, no una fusión a
    medias: se valida todo antes de tocar disco.
    """
    if cort_memoria is None:
        return {"ok": False, "origen": "no disponible",
                "motivo": "el puente no cargó el módulo de memoria; no hay dónde guardar nada"}
    if not isinstance(cuerpo, dict):
        return {"ok": False, "motivo": "el cuadro no es un objeto JSON"}
    if cuerpo.get("version") != VERSION:
        return {"ok": False,
                "motivo": "versión de cuadro %r: este puente habla la %d"
                          % (cuerpo.get("version"), VERSION)}
    filas = cuerpo.get("recuerdos")
    if not isinstance(filas, list):
        return {"ok": False, "motivo": "el cuadro no trae lista de recuerdos"}
    if len(filas) > MAX_FILAS:
        return {"ok": False, "motivo": "demasiados recuerdos en un viaje: %d (tope %d)"
                                      % (len(filas), MAX_FILAS)}

    d = cort_memoria._leer()
    existentes = {normaliza(h.get("texto", "")) for h in d.get("hechos", [])}
    nuevos = repetidos = rechazados = 0
    ahora = int(time.time())
    for fila in filas:
        contenido = limpia_fila(fila, llave)
        if contenido is None:
            rechazados += 1
            continue
        if normaliza(contenido) in existentes:
            repetidos += 1
            continue
        existentes.add(normaliza(contenido))
        # La `clave` se forma como la forma `_apuntar` (las primeras seis palabras): si
        # el enlace la inventara a su manera, «qué sabes de mí» dejaría de encontrar los
        # recuerdos que llegaron del teléfono.
        try:
            clave = " ".join(cort_memoria._palabras(contenido)[:6]) or contenido[:40]
        except Exception:
            clave = contenido[:40]
        d.setdefault("hechos", []).append({"clave": clave,
                                           "texto": contenido, "hora": ahora})
        nuevos += 1
    if len(d["hechos"]) > cort_memoria.LIMITE_HECHOS:
        d["hechos"] = d["hechos"][-cort_memoria.LIMITE_HECHOS:]
    if nuevos:
        r = cort_memoria._escribir(d)
        if not r.get("ok"):
            return {"ok": False, "motivo": "la memoria del portátil no se pudo escribir: %s"
                                           % r.get("motivo", "sin motivo")}
    return {"ok": True, "tipo": TIPO, "version": VERSION, "origen": ORIGEN,
            "nuevos": nuevos, "repetidos": repetidos, "rechazados": rechazados,
            "total": len(d.get("hechos", []))}


# --- el puente (aiohttp) -------------------------------------------------------
def registro(app, llave=None):
    """Montando `GET` y `POST` de `/memoria/puente` en la aplicación del core.

    El teléfono no pregunta por la interfaz (8766), pregunta por el puerto del core
    (8765 en esta rama): `Puente.urlDelPuente` cambia un número por el otro
    conservando el host, así que las rutas van en la aplicación del WebSocket.
    """
    llave = llave or token()

    async def bajar(request):
        if not autorizada(request.query.get("token"), llave):
            return web.json_response(
                {"ok": False, "origen": "no disponible",
                 "motivo": "sin llave no hay memoria: el enlace pide ?token=…"}, status=401)
        return web.json_response(cuadro(llave))

    async def subir(request):
        if not autorizada(request.query.get("token"), llave):
            return web.json_response(
                {"ok": False, "origen": "no disponible",
                 "motivo": "sin llave no hay memoria: el enlace pide ?token=…"}, status=401)
        cuerpo_crudo = await request.text()
        if len(cuerpo_crudo.encode("utf-8")) > MAX_BYTES:
            return web.json_response(
                {"ok": False, "motivo": "el cuadro pesa %d bytes, y el tope es %d"
                                        % (len(cuerpo_crudo.encode("utf-8")), MAX_BYTES)},
                status=413)
        try:
            cuerpo = json.loads(cuerpo_crudo)
        except Exception:
            return web.json_response({"ok": False, "motivo": "el cuerpo no es JSON"}, status=400)
        respuesta = recibe(cuerpo, llave)
        return web.json_response(respuesta, status=200 if respuesta.get("ok") else 400)

    app.router.add_get(RUTA, bajar)
    app.router.add_post(RUTA, subir)
    return llave


try:  # `aiohttp` sólo hace falta para montar las rutas; el resto se prueba sin él
    from aiohttp import web
except Exception:
    web = None


def enlace_del_puente(bind=None, puerto=None, llave=None):
    """La dirección que ve el teléfono: host, puerto del core y llave en el query."""
    host = bind or "127.0.0.1"
    if host in ("0.0.0.0", "::"):
        host = ip_de_casa() or "127.0.0.1"
    protocolo = "https" if os.environ.get("CORT_TLS") else "http"
    puerto = puerto or 8765
    return "%s://%s:%d%s?token=%s" % (protocolo, host, puerto, RUTA, llave or token())


def ip_de_casa():
    """La IP local real, sin salir a internet: un socket UDP conectado no manda paquetes."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))  # ruta de encaminamiento, nunca tráfico
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return None


# --- el QR del enlace ----------------------------------------------------------
# `qrcodegen` es la biblioteca de Project Nayuki (MIT), vendida en
# `cort-bridge/terceros/` con su suma fijada en `terceros.txt` y leída antes de
# usarla: sólo importa `collections`, `itertools` y `re` — no abre red, no escribe
# disco, no ejecuta nada. Que el QR lo dibuje CORT y no una página de terceros es
# lo que permite que el enlace **nunca salga de la casa**.
try:
    sys.path.insert(0, str(BASE / "terceros"))
    import qrcodegen
except Exception:
    qrcodegen = None


def qr_matriz(texto):
    """La rejilla del QR como lista de listas de `bool`, o None si la biblioteca falta."""
    if qrcodegen is None:
        return None
    codigo = qrcodegen.QrCode.encode_text(texto, qrcodegen.QrCode.Ecc.MEDIUM)
    tam = codigo.get_size()
    return [[codigo.get_module(x, y) for y in range(tam)] for x in range(tam)]


def qr_svg(texto, modulo=6, margen_modulos=4):
    """El QR como SVG de texto: se abre en cualquier navegador sin instalar nada."""
    rejilla = qr_matriz(texto)
    if rejilla is None:
        return None
    lado = len(rejilla)
    total = (lado + 2 * margen_modulos) * modulo
    cuadros = []
    for x, columna in enumerate(rejilla):
        for y, oscuro in enumerate(columna):
            if oscuro:
                cuadros.append('<rect x="%d" y="%d" width="%d" height="%d"/>' % (
                    (x + margen_modulos) * modulo, (y + margen_modulos) * modulo, modulo, modulo))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
            '<rect width="100%%" height="100%%" fill="#ffffff"/><g fill="#000000">%s</g></svg>'
            % (total, total, total, total, "".join(cuadros)))


def qr_terminal(texto, con_ansi=None):
    """El mismo QR dibujado en la consola con bloques Unicode (dos módulos por carácter).

    Es el camino por defecto: la dirección con la llave **no se sirve por red**, así
    que nadie en el Wi-Fi puede abrir una página y llevársela. Se lee aquí, en la
    pantalla de la PC, con el teléfono delante.

    Los cuatro módulos de zona de silencio no son adorno: el estándar los pide y sin
    ellos zxing en el teléfono no ve dónde empieza el cuadro. El fondo blanco forzado
    (sólo en terminal interactiva) es por lo mismo: en una consola oscura los espacios
    serían negros y el QR saldría invertido.
    """
    rejilla = qr_matriz(texto)
    if rejilla is None:
        return "el enlace tiene dirección pero este equipo no tiene `qrcodegen` para dibujar el QR"
    if con_ansi is None:
        con_ansi = sys.stdout.isatty()
    tam = len(rejilla)
    MARGEN = 4
    ancho = tam + 2 * MARGEN
    # fg negro sobre bg blanco: los espacios salen blancos y los bloques ▀▄█ negros, así
    # que el cuadro se ve igual en consola clara que en oscura.
    fondo = "\033[30m\033[47m" if con_ansi else ""
    apagar = "\033[0m" if con_ansi else ""
    franca = fondo + " " * ancho + apagar
    lineas = [franca] * (MARGEN // 2)     # cada línea de texto vale dos módulos de alto
    for i in range(0, tam, 2):
        pedazos = []
        for x in range(tam):
            arriba = rejilla[x][i]
            abajo = rejilla[x][i + 1] if i + 1 < tam else False
            pedazos.append("█" if arriba and abajo else ("▀" if arriba else ("▄" if abajo else " ")))
        lineas.append(fondo + " " * MARGEN + "".join(pedazos) + " " * MARGEN + apagar)
    lineas += [franca] * (MARGEN // 2)
    return "\n".join(lineas)


def principal(argv):
    import argparse
    p = argparse.ArgumentParser(description="el enlace de memoria PC ↔ teléfono (F14)")
    p.add_argument("--cuadro", action="store_true", help="imprimir el cuadro que bajaría el teléfono")
    p.add_argument("--enlace", action="store_true", help="imprimir la dirección con la llave")
    p.add_argument("--token", action="store_true", help="forjar una llave nueva y decir cuál es")
    p.add_argument("--qr", action="store_true", help="dibujar el enlace en la consola, para escanearlo con el teléfono")
    p.add_argument("--qr-svg", metavar="ARCHIVO", help="guardar el enlace como SVG (se abre en el navegador)")
    p.add_argument("--en-casa", action="store_true",
                   help="forzar 127.0.0.1 en vez de la IP de la red (el teléfono no podría leerlo)")
    args = p.parse_args(argv)
    if args.qr or args.qr_svg:
        # Sin esto el QR apuntaría a `127.0.0.1`, que en el teléfono es el propio teléfono:
        # un cuadro que se escanea y no encuentra nada. Se dibuja la IP de la casa.
        anfitrion = "127.0.0.1" if args.en_casa else (ip_de_casa() or "127.0.0.1")
        url = enlace_del_puente(anfitrion)
    if args.qr:
        if anfitrion == "127.0.0.1":
            print("esta PC no ve su propia IP de la red: el cuadro apuntaría a sí misma y "
                  "el teléfono no encontraría nada. Conecta el Wi-Fi, o escribe la dirección "
                  "a mano en el teléfono.")
        print(qr_terminal(url))
        print(url)
        return 0
    if args.qr_svg:
        svg = qr_svg(url)
        if svg is None:
            print("no hay `qrcodegen` en cort-bridge/terceros/", file=sys.stderr)
            return 1
        Path(args.qr_svg).write_text(svg, encoding="utf-8")
        print(args.qr_svg)
        print(url)
        return 0
    if args.token:
        print(token(nuevo=True))
        return 0
    if args.cuadro:
        print(json.dumps(cuadro(token()), ensure_ascii=False, indent=1))
        return 0
    if args.enlace:
        print(enlace_del_puente())
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
