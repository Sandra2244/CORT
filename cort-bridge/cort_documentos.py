"""F19 — los documentos: el teléfono sube un archivo y la PC le saca las letras.

Sandra estudia y quiere que CORT **lea**. Un teléfono no saca texto de un PDF: para
eso está `poppler` en la PC. Este módulo es el puente honesto —el archivo sube por el
mismo puerto y la misma llave que el parlamento, la PC lo abre, devuelve el texto y lo
borra— y no guarda documentos en ninguna parte.

El contrato (puerto del core, **8765**, con la llave del enlace):

* `POST /documentos?token=…` — cuerpo: los bytes del archivo (`%PDF` al principio o
  texto plano). Devuelve JSON con `texto`, `tipo`, `paginas`, `caracteres`,
  `recortado`, `ms`, `origen`.

Las reglas de la casa, comprobadas en `scripts/prueba_documentos.py`:

1. **Sin llave no hay documento.** 401 con el motivo dicho con palabras.
2. **El archivo no se queda.** Se escribe en un tmp propio sólo mientras `pdftotext` lo
   lee y se borra en el `finally`; el texto que devuelve tampoco se guarda en la
   memoria —es un reading, no un recuerdo.
3. **Un PDF sin letras no se disfraza.** Si `pdftotext` devuelve vacío son imágenes: lo
   dice, en vez de leer el índice como si fuera el libro. El lector de letras
   (`tesseract`) no está en esta PC, y se dice con esa palabra.
4. **Topes por escrito:** 8 MB de cuerpo, 60 000 caracteres devueltos y 90 s de margen
   para el extractor. Un libro de 400 páginas no inunda la pantalla del teléfono.
"""

import asyncio
import os
import subprocess
import time
from pathlib import Path

from aiohttp import web

MAX_CUERPO = 8 * 1024 * 1024
TEXTO_MAX = 60_000
CADUCIDAD_S = 90

TMP = Path(os.environ.get("CORT_TMP_DOC", "/tmp/cort-documentos"))


def _ruta_tmp(ident: str) -> Path:
    seguro = "".join(c if c.isalnum() or c in "-_" else "" for c in str(ident))[:24]
    return TMP / f"documento-{os.getpid()}-{seguro or 'x'}"


def _paginas(texto: str, ruta: Path) -> int:
    """`pdfinfo` si está; si no, los saltos de página que deja pdftotext (\x0c)."""
    try:
        salida = subprocess.run(["pdfinfo", str(ruta)], capture_output=True,
                                timeout=20, text=True).stdout
        for linea in salida.splitlines():
            if linea.startswith("Pages:"):
                return int(linea.split()[1])
    except Exception:
        pass
    return max(1, texto.count("\f") + 1)


def extrae_texto(bytes_archivo: bytes, ident: str) -> dict:
    """Letras de un PDF o de un texto plano. Nunca deja nada en el disco."""
    empezado = time.monotonic()
    if bytes_archivo[:5] == b"%PDF-":
        TMP.mkdir(parents=True, exist_ok=True)
        ruta = _ruta_tmp(ident)
        try:
            ruta.write_bytes(bytes_archivo)
            try:
                proceso = subprocess.run(
                    ["pdftotext", "-enc", "UTF-8", "-q", str(ruta), "-"],
                    capture_output=True, timeout=CADUCIDAD_S, text=True)
            except FileNotFoundError:
                return {"ok": False, "origen": "no disponible", "tipo": "pdf",
                        "motivo": "esta PC no tiene pdftotext (paquete poppler-utils)",
                        "hace_falta": "poppler-utils"}
            except subprocess.TimeoutExpired:
                return {"ok": False, "origen": "no disponible", "tipo": "pdf",
                        "motivo": f"pdftotext tardó más de {CADUCIDAD_S} s y se cortó"}
            texto = (proceso.stdout or "").strip()
            if proceso.returncode != 0 and not texto:
                return {"ok": False, "origen": "no disponible", "tipo": "pdf",
                        "motivo": (proceso.stderr.strip() or "pdftotext salió con error")[:200]}
            if not texto:
                return {"ok": False, "origen": "no disponible", "tipo": "pdf",
                        "motivo": "el PDF no trae letras: son imágenes. Esta PC no tiene "
                                  "lector de letras (tesseract) instalado",
                        "paginas": _paginas("", ruta)}
            paginas = _paginas(texto, ruta)
            recortado = len(texto) > TEXTO_MAX
            return {"ok": True, "origen": "real", "tipo": "pdf", "paginas": paginas,
                    "texto": texto[:TEXTO_MAX], "caracteres": len(texto),
                    "recortado": recortado,
                    "ms": int((time.monotonic() - empezado) * 1000)}
        finally:
            try:
                ruta.unlink()
            except OSError:
                pass
    try:
        texto = bytes_archivo.decode("utf-8")
    except UnicodeDecodeError:
        texto = bytes_archivo.decode("latin-1", errors="replace")
    texto = texto.replace("\r\n", "\n").strip()
    if not texto:
        return {"ok": False, "origen": "no disponible", "tipo": "texto",
                "motivo": "el archivo no tenía texto"}
    recortado = len(texto) > TEXTO_MAX
    return {"ok": True, "origen": "real", "tipo": "texto", "paginas": 1,
            "texto": texto[:TEXTO_MAX], "caracteres": len(texto), "recortado": recortado,
            "ms": int((time.monotonic() - empezado) * 1000)}


def limpiar_tmp(retencion: int = 15 * 60) -> int:
    """Tira residuos de archivos que murieron a media extracción. Devuelve cuántos."""
    quitados = 0
    try:
        ahora = time.time()
        for archivo in TMP.glob("documento-*"):
            try:
                if ahora - archivo.stat().st_mtime > retencion:
                    archivo.unlink()
                    quitados += 1
            except OSError:
                pass
    except OSError:
        pass
    return quitados


def montar(app, llave, autorizada):
    """Monta `POST /documentos` en el puerto del core, junto al parlamento."""

    async def documentos(request):
        if not autorizada(request.query.get("token"), llave):
            return web.json_response({"ok": False, "origen": "no disponible",
                                      "motivo": "el ?token= no es la llave del enlace"},
                                     status=401)
        cuerpo = await request.read()
        if not cuerpo:
            return web.json_response({"ok": False, "origen": "no disponible",
                                      "motivo": "el archivo llegó vacío"})
        cuadro = await asyncio.get_event_loop().run_in_executor(
            None, extrae_texto, cuerpo, request.query.get("hilo", ""))
        cuadro["bytes"] = len(cuerpo)
        return web.json_response(cuadro)

    app.router.add_post("/documentos", documentos)
    return {"max_mb": round(MAX_CUERPO / 1024 / 1024), "caracteres": TEXTO_MAX}
