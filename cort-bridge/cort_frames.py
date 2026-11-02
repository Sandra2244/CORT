#!/usr/bin/env python3
"""Sacador de fotogramas — herramienta temporal de la fase F2.

No hay ffmpeg en la Canaima y no se va a instalar nada por dos videos. El que sí
decodifica MP4 gratis es el navegador, así que este servidor hace dos cosas:

  · sirve los videos de ~/Escritorio/Referencias IA CORT con peticiones parciales
    (Range), que es lo que permite al <video> saltar de un segundo a otro;
  · recibe los fotogramas que la página pinta en un <canvas> y los guarda en disco.

Se levanta, se sacan los fotogramas y se apaga. No forma parte de CORT.

  python3 cort_frames.py            # escucha en 8767
  http://127.0.0.1:8767/            # la página que hace el trabajo

Salida: ~/Escritorio/Referencias IA CORT/fotogramas/<nombre-del-video>/<NN>-<ss.ss>s.jpg
"""
import base64
import json
import os
import re
import sys
from pathlib import Path

from aiohttp import web

REFS = Path(os.path.expanduser("~/Escritorio/Referencias IA CORT"))
SALIDA = REFS / "fotogramas"
PUERTO = 8767

PAGINA = """<!doctype html><html><head><meta charset="utf-8"><title>fotogramas</title>
<style>body{background:#05070b;color:#9fe;font:12px/1.4 monospace;padding:14px}
video{max-width:520px;display:block;margin:10px 0;border:1px solid #123}</style></head><body>
<div id="estado">sin video</div>
<video id="v" muted playsinline preload="auto"></video>
<canvas id="c" width="640" height="360" style="display:none"></canvas>
<script>
const v = document.getElementById('v'), c = document.getElementById('c'), ctx = c.getContext('2d');
const estado = document.getElementById('estado');
function listo(t){ return new Promise(res => { if (v.readyState >= t) return res();
  v.addEventListener('loadeddata', res, {once:true}); }); }
async function fotograma(seg) {
  await new Promise(res => { v.onseeked = res; v.currentTime = seg; });
  await listo(2);
  const r = v.videoWidth / v.videoHeight;
  c.width = 640; c.height = Math.round(640 / r);
  ctx.drawImage(v, 0, 0, c.width, c.height);
  const url = c.toDataURL('image/jpeg', 0.82);
  const d = await fetch('/guardar', { method: 'POST', headers: {'content-type':'application/json'},
    body: JSON.stringify({ nombre: window._nombre, seg, url }) }).then(r => r.json());
  estado.textContent = `ok ${seg.toFixed(2)} s → ${d.ruta}`;
  return d;
}
window.cargar = async (src, nombre) => {
  window._nombre = nombre;
  estado.textContent = 'cargando ' + src;
  v.src = src; v.load();
  await listo(1);
  await new Promise(res => { if (v.duration && isFinite(v.duration)) return res();
    v.addEventListener('durationchange', res, {once:true}); });
  estado.textContent = `duración ${v.duration.toFixed(1)} s · ${v.videoWidth}x${v.videoHeight}`;
  return { dur: v.duration, w: v.videoWidth, h: v.videoHeight };
};
window.sacar = async (seg) => fotograma(seg);
</script></body></html>"""


async def pagina(req):
    return web.Response(text=PAGINA, content_type="text/html")


async def guardar(req):
    datos = await req.json()
    url = datos.get("url", "")
    m = re.match(r"^data:image/jpeg;base64,(.+)$", url)
    if not m:
        return web.json_response({"error": "no es jpeg base64"}, status=400)
    nombre = re.sub(r"[^A-Za-z0-9._-]", "_", datos.get("nombre", "video"))[:60]
    carpeta = SALIDA / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    seg = float(datos.get("seg", 0))
    ruta = carpeta / f"{int(seg):02d}-{seg:06.2f}s.jpg"
    ruta.write_bytes(base64.b64decode(m.group(1)))
    return web.json_response({"ruta": str(ruta), "bytes": ruta.stat().st_size})


async def video(req):
    """Sirve un .mp4 admitiendo Range: sin eso el <video> no puede buscar segundos."""
    nombre = req.match_info["nombre"]
    ruta = (REFS / nombre).resolve()
    if not str(ruta).startswith(str(REFS.resolve())) or not ruta.is_file():
        return web.Response(status=404, text="no existe")
    tam = ruta.stat().st_size
    rango = req.headers.get("Range")
    inicio, fin = 0, tam - 1
    if rango:
        m = re.match(r"bytes=(\d*)-(\d*)", rango)
        if m:
            inicio = int(m.group(1) or 0)
            fin = int(m.group(2)) if m.group(2) else tam - 1
    cab = {"Content-Type": "video/mp4", "Accept-Ranges": "bytes",
           "Content-Length": str(fin - inicio + 1),
           "Content-Range": f"bytes {inicio}-{fin}/{tam}"}
    with open(ruta, "rb") as f:
        f.seek(inicio)
        return web.Response(status=206 if rango else 200, headers=cab,
                            body=f.read(fin - inicio + 1))


app = web.Application()
app.router.add_get("/", pagina)
app.router.add_post("/guardar", guardar)
app.router.add_get("/v/{nombre:.+}", video)

if __name__ == "__main__":
    SALIDA.mkdir(exist_ok=True)
    print(f"[frames] http://127.0.0.1:{PUERTO}/  · guarda en {SALIDA}", flush=True)
    web.run_app(app, host="127.0.0.1", port=PUERTO, print=None)
