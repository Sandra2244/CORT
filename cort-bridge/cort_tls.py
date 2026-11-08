#!/usr/bin/env python3
"""CORT TLS local (F20a): el certificado de la casa, sin instalar nada.

El teléfono necesita HTTPS para fiarse del puente (origen seguro: micrófono,
instalación), y un certificado comprado no tiene sentido para una máquina que
sólo habla dentro del Wi-Fi de casa. Este módulo genera un par autofirmado con
el `openssl` que YA esté instalado — si no está, lo dice con palabras y no
instala nada: ni pip, ni binarios de terceros.

Lo que sale:

  * RSA de 2048 bits, 825 días de vigencia, con SAN para `localhost`,
    `127.0.0.1` y cada IPv4 no loopback del equipo (la IP del Wi-Fi cambia de
    casa en casa; por eso se leen todas las interfaces, no una supuesta).
  * Certificado y clave con modo 0600 desde el instante en que existen.
  * La huella: SHA-256 del DER, en hex. Es lo que el teléfono fija (pin) para
    no aceptar cualquier certificado autofirmado que se le ponga delante.

El par vive en la misma carpeta que la llave del enlace (`CORT_DATOS`, por
defecto `~/.local/share/cort`). Si ya existe, `generar` NO lo pisa: la huella
que el teléfono fijó tiene que seguir valiendo.

Este módulo no toca el entorno de ningún proceso: sólo escribe archivos cuando
se le pide. El puente vivo decide al arrancar: `CORT_TLS=cert,clave` explícito
manda, y `CORT_TLS_AUTO=1` usa este par si ya está generado.

Uso en la PC (imprime las rutas, la huella y la línea que exportar):

    python3 cort-bridge/cort_tls.py
    python3 cort-bridge/cort_tls.py --estado     # sólo mirar, sin generar
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

NOMBRE_CERT = "tls-cert.pem"
NOMBRE_CLAVE = "tls-clave.pem"
BITS = 2048     # tamaño de la clave RSA
DIAS = 825      # vigencia del certificado; no hay renovación automática en este módulo


def directorio_por_defecto():
    """La misma carpeta donde `cort_enlace` guarda la llave del enlace.

    Se importa tarde y con salida: si `cort_enlace` no cargara, la regla del
    directorio es la misma que la suya (`CORT_DATOS` o ~/.local/share/cort).
    """
    try:
        import cort_enlace
        return Path(cort_enlace.DATOS)
    except Exception:
        return Path(os.environ.get("CORT_DATOS",
                                   str(Path.home() / ".local" / "share" / "cort")))


def ips_de_la_maquina():
    """Todas las IPv4 no loopback de este equipo, para los SAN del certificado.

    Con `ip -4 -o addr show` (iproute2) se ven todas las interfaces. Si ese
    binario no está o no dice nada, se cae a la resolución del propio nombre,
    que puede ver menos direcciones: se devuelve lo que se pudo leer, no se
    inventa ninguna.
    """
    ips = set()
    binario = shutil.which("ip")
    if binario:
        try:
            salida = subprocess.run([binario, "-4", "-o", "addr", "show"],
                                    capture_output=True, text=True, timeout=5).stdout
            for linea in salida.splitlines():
                campos = linea.split()
                if "inet" in campos:
                    ip = campos[campos.index("inet") + 1].split("/")[0]
                    if not ip.startswith("127."):
                        ips.add(ip)
        except Exception:
            pass
    if not ips:
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                ip = info[4][0]
                if not ip.startswith("127."):
                    ips.add(ip)
        except Exception:
            pass
    return sorted(ips)


def generar(directorio=None):
    """Certificado + clave autofirmados para la casa: (ruta_cert, ruta_clave).

    Si el par ya existe se devuelve tal cual: pisarlo rompería la huella que el
    teléfono ya fijó. Solo se regenera cuando falta alguno de los dos (un
    certificado sin su clave no sirve, y viceversa).
    """
    carpeta = Path(directorio) if directorio is not None else directorio_por_defecto()
    cert, clave = carpeta / NOMBRE_CERT, carpeta / NOMBRE_CLAVE
    if cert.is_file() and clave.is_file():
        return str(cert), str(clave)
    binario = shutil.which("openssl")
    if not binario:
        raise RuntimeError("no hay `openssl` en este equipo: no se puede generar el "
                           "certificado de la casa, y no se instala nada sin tu orden")
    carpeta.mkdir(parents=True, exist_ok=True)
    sans = ["DNS:localhost", "IP:127.0.0.1"] + ["IP:" + ip for ip in ips_de_la_maquina()]
    # Los dos archivos se crean vacíos con 0600 ANTES de que openssl escriba:
    # openssl trunca el que ya existe y le conserva el modo, así que la clave
    # nunca existe ni un instante legible por otros procesos de la sesión.
    for ruta in (cert, clave):
        fd = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.close(fd)
    comando = [binario, "req", "-x509", "-newkey", "rsa:%d" % BITS, "-nodes",
               "-keyout", str(clave), "-out", str(cert), "-days", str(DIAS),
               "-subj", "/CN=" + (socket.gethostname() or "cort"),
               "-addext", "subjectAltName=" + ",".join(sans)]
    try:
        r = subprocess.run(comando, capture_output=True, text=True, timeout=60)
    except Exception as e:
        r = None
        detalle = "%s: %s" % (type(e).__name__, e)
    if r is not None and r.returncode == 0 and cert.stat().st_size and clave.stat().st_size:
        os.chmod(cert, 0o600)
        os.chmod(clave, 0o600)
        return str(cert), str(clave)
    # Si openssl falló no se deja un par vacío que la próxima llamada tomaría por
    # bueno: se retira lo que se alcanzó a crear y se dice el motivo.
    for ruta in (cert, clave):
        try:
            ruta.unlink()
        except OSError:
            pass
    detalle = (r.stderr or "").strip()[:300] if r is not None else detalle
    raise RuntimeError("openssl no pudo generar el certificado de la casa: %s"
                       % (detalle or "salió sin escribir el par"))


def huella(ruta_cert):
    """SHA-256 del DER del certificado, en hex (64 caracteres).

    Es la misma cuenta que `openssl x509 -fingerprint -sha256`: un PEM es el DER
    en base64, así que basta decodificar el cuerpo entre las líneas `-----`.
    Esto es lo que el teléfono fija (pin); no es la llave del enlace y puede
    viajar por la red sin abrir ninguna puerta.
    """
    texto = Path(ruta_cert).read_text(encoding="utf-8")
    cuerpo = "".join(l.strip() for l in texto.splitlines() if "-----" not in l)
    return hashlib.sha256(base64.b64decode(cuerpo)).hexdigest()


def estado(directorio=None):
    """Qué hay en la carpeta: si el par existe, dónde está y cuál es su huella."""
    carpeta = Path(directorio) if directorio is not None else directorio_por_defecto()
    cert, clave = carpeta / NOMBRE_CERT, carpeta / NOMBRE_CLAVE
    d = {"existe": cert.is_file() and clave.is_file(),
         "cert": str(cert), "clave": str(clave), "huella": "",
         "openssl": bool(shutil.which("openssl"))}
    if d["existe"]:
        try:
            d["huella"] = huella(cert)
        except Exception as e:
            d["existe"] = False
            d["motivo"] = "el certificado está pero no se pudo leer (%s)" % type(e).__name__
    return d


def rutas_auto():
    """El par de la casa en formato `CORT_TLS` ("cert,clave"), si se pidió usarlo.

    Sólo mira: con `CORT_TLS_AUTO=1` y el par ya generado devuelve sus rutas; en
    cualquier otro caso devuelve "" y el arranque sigue como estaba. No genera.
    """
    if os.environ.get("CORT_TLS_AUTO", "0") != "1":
        return ""
    d = estado()
    return "%s,%s" % (d["cert"], d["clave"]) if d["existe"] else ""


def principal(argv):
    import argparse
    p = argparse.ArgumentParser(description="el certificado TLS de la casa (F20a)")
    p.add_argument("--directorio", help="carpeta del par (por defecto, la de la llave del enlace)")
    p.add_argument("--estado", action="store_true", help="sólo mirar qué hay, sin generar nada")
    args = p.parse_args(argv)
    directorio = Path(args.directorio) if args.directorio else None
    if args.estado:
        print(json.dumps(estado(directorio), ensure_ascii=False, indent=1))
        return 0
    try:
        cert, clave = generar(directorio)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    print("certificado: %s" % cert)
    print("clave:       %s" % clave)
    print("huella sha256 (la que fija el teléfono): %s" % huella(cert))
    print("para arrancar el puente con él:")
    print("  export CORT_TLS=%s,%s" % (cert, clave))
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))