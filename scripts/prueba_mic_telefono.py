"""F7 — el micrófono del teléfono entra por POST /mic, no por el navegador.

El WebView de Android no puede usar getUserMedia mientras el puente va por http
(origen no seguro), así que la aplicación graba un WAV y lo sube. Esta prueba
hace exactamente ese viaje, pero con audio sintético: no hace falta micro.

Va contra el puente de arena (8776 por defecto). Si alguien lo apunta a 8766 está
golpeando el puente vivo de la casa: el script lo dice en la primera línea.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

PUERTO = os.environ.get("CORT_WEB_PORT", "8776")
BASE = f"http://127.0.0.1:{PUERTO}"
FRASE = os.environ.get("CORT_MIC_FRASE", "hola cort buenas tardes")

RESULTADOS = []


def apunta():
    print(f"destino: {BASE}/mic  ({'ARENA' if PUERTO != '8766' else 'PUENTE VIVO, ten cuidado'})",
          flush=True)


def post(datos: bytes, tipo="audio/wav"):
    req = urllib.request.Request(BASE + "/mic", data=datos, method="POST")
    req.add_header("Content-Type", tipo)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def wav_de_espeak(texto: str, destino: Path) -> bool:
    """espeak-ng escribe 22050 Hz; el teléfono manda 16000. Sox los iguala."""
    if not (shutil.which("espeak-ng") and shutil.which("sox")):
        return False
    crudo = destino.with_suffix(".crudo.wav")
    subprocess.run(["espeak-ng", "-v", "es", "-w", str(crudo), texto], check=True)
    subprocess.run(["sox", str(crudo), "-r", "16000", "-c", "1", "-b", "16", str(destino)],
                   check=True)
    crudo.unlink(missing_ok=True)
    return True


def caso(nombre, condicionado, detalle=""):
    RESULTADOS.append((nombre, condicionado, detalle))
    print(f"  {'PASA' if condicionado else 'FALLA'}  {nombre}" + (f"  · {detalle}" if detalle else ""),
          flush=True)


def main():
    apunta()
    tmp = Path("/tmp/cort-prueba-mic")
    tmp.mkdir(parents=True, exist_ok=True)
    ruta = tmp / "frase.wav"

    if not wav_de_espeak(FRASE, ruta):
        print("no hay espeak-ng ni sox: se omite el caso de audio real")
        datos = None
    else:
        datos = ruta.read_bytes()
        print(f"  wav de {len(datos)} bytes · 16 kHz mono 16 bits · frase «{FRASE}»")

    print("\n1) lo que pasa cuando no es audio")
    estado, r = post(b"esto no es un wav")
    caso("rechaza lo que no es RIFF/WAVE", estado == 200 and r.get("ok") is False
         and "no es un WAV" in (r.get("motivo") or ""), f"motivo: {r.get('motivo')}")
    caso("y lo dice con origen no disponible", r.get("origen") == "no disponible")

    print("\n2) audio real subido como lo subiría el teléfono")
    if datos is None:
        caso("audio sintético -> transcripción", False, "sin espeak-ng/sox en este equipo")
    else:
        t0 = os.times()[4]
        estado, r = post(datos)
        ms = int((os.times()[4] - t0) * 1000)
        caso("el puente responde 200", estado == 200, f"estado {estado}")
        caso("dice origen real", r.get("origen") == "real", f"origen {r.get('origen')}")
        texto = (r.get("texto") or "").lower()
        palabras = set(FRASE.lower().split())
        encontradas = [p for p in palabras if p in texto]
        caso("saca palabras del audio del teléfono", bool(texto),
             f"texto: «{texto}»")
        caso("y las palabras son las que se dijeron", len(encontradas) >= 2,
             f"coinciden {len(encontradas)}/{len(palabras)}: {encontradas}")
        print(f"     round trip completo: {ms} ms · proceso Vosk {r.get('ms_proceso')} ms")

    print("\n3) el audio no se queda en el disco")
    sobran = sorted(p.name for p in Path("/tmp/cort-voz").glob("micro-*.wav")) \
        if Path("/tmp/cort-voz").exists() else []
    caso("no queda ningún micro-*.wav después de transcribir", not sobran, f"quedan {sobran}")

    ruta.unlink(missing_ok=True)
    buenos = sum(1 for _, ok, _ in RESULTADOS if ok)
    print(f"\n{buenos}/{len(RESULTADOS)} casos")
    return 0 if buenos == len(RESULTADOS) else 1


if __name__ == "__main__":
    sys.exit(main())
