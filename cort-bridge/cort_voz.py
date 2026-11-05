#!/usr/bin/env python3
"""CORT — voz de salida y micrófono, con el equipo mirado de frente.

Por qué este archivo existe aparte del puente: la voz es lo único que puede mentir
por omisión. Si el motor no está, el altavoz no existe o el micrófono está muerto,
CORT tiene que decir el dispositivo exacto y no quedarse callado como si nada.

Medido en la Classmate el 2026-11-02 con `pactl list short` (no es teoría):
  · salida  -> 34 auto_null. El códec analógico y el jack de 3,5 mm están muertos;
    suena sólo por HDMI o por dongle USB de audio conectados.
  · entrada -> 34 auto_null.monitor. No hay micrófono de captura en este equipo:
    el interno no aparece como fuente. El del teléfono sí servirá cuando CORT corra
    en el A16 y mande el audio por el WebSocket (F7).

Medida también la velocidad de cada motor con la misma frase (4-5 s de audio), con
la máquina cargada (el entorno del agente se estaba comiendo los 2 núcleos):

| motor | carga del modelo | sintetizar | factor (ms de CPU por s de audio) |
|---|---|---|---|
| espeak-ng `-v es` | — | 549 ms | **0,14** |
| Piper es_ES-davefx-medium | 15,2 s | 8.534 ms para 3,34 s | 2,55 |
| Piper es_ES-mls_10246-low | 14,2 s | 9.417 ms para 4,96 s | 1,90 |

De ahí sale la elección por defecto: **`rapida` = espeak-ng** para que CORT conteste
al instante (robótico, pero suena), y **`natural` = Piper** para frases cortas, con el
modelo cargado UNA sola vez dentro del proceso del puente (los 14 s de carga pesan una
vez, no en cada frase). Cambiar de motor es un ajuste, no un secreto.

Los modelos viven en ~/.local/share/cort, fuera del repo: aquí no se comita binario.

Uso en terminal (auto-prueba incluida):
  cort_voz.py estado                 qué hay y qué falta, con números
  cort_voz.py decir "frase"          sintetiza y reproduce
  cort_voz.py probar [frase]         sintetiza y mide, sin reproducir
  cort_voz.py escuchar 5             graba 5 s del micrófono y transcribe
  cort_voz.py transcribir a.wav      Vosk sobre un WAV (prueba sin micrófono)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

# -------------------------------------------------------------------- rutas ----
REPO = Path(__file__).resolve().parent.parent
CASA = Path(os.environ.get("CORT_HOME", str(Path.home())))
DATOS = Path(os.environ.get("CORT_DATOS", str(CASA / ".local" / "share" / "cort")))
DIR_VOZ = DATOS / "voz"
DIR_MODELOS = DATOS / "modelos"
DIR_VOSK = DIR_MODELOS / "vosk-es"
TMP = Path(os.environ.get("CORT_TMP", "/tmp/cort-voz"))
# Cuánto vive un WAV dicho por la PC. `hablar()` no puede borrar el suyo al terminar:
# la página lo baja por `/audio/…` para que el orbe suene con su subtítulo. Sin techo,
# /tmp se vuelve un archivo de todo lo que CORT dijo — medido: 18 WAV y 8,9 MB.
RETENCION_TMP = 600

# onnx, nombre para el usuario, factor medido (ms de CPU por segundo de audio)
VOZES = {
    "natural": (DIR_VOZ / "es_ES-mls_10246-low.onnx", "Piper mls_10246 (natural)", 1.90),
    "natural2": (DIR_VOZ / "es_ES-davefx-medium.onnx", "Piper davefx (natural)", 2.55),
}
ESPEAK = shutil.which("espeak-ng") or shutil.which("espeak")
PW_PLAY = shutil.which("pw-play") or shutil.which("paplay")
ARECORD = shutil.which("arecord")
RATE_STT = 16000

MOTOR = os.environ.get("CORT_VOZ_MOTOR", "rapida")   # "rapida" | "natural"
_PIPER: dict[Path, tuple] = {}          # ruta -> (PiperVoice, segundos de carga)
_PIPER_LOCK = threading.Lock()
_VOSK = None
_VOSK_LOCK = threading.Lock()

_LOCK = threading.Lock()
_TAREAS: list[dict] = []
_HIST: dict[int, dict] = {}     # id -> resultado, para que el puente consulte si terminó
_COLA: list[int] = []
_MAX_COLA = 3        # si hay tres frases esperando, se tira la más vieja


def cambiar_motor(nuevo: str) -> dict:
    """Cambia `rapida` (espeak-ng) por `natural` (Piper) y dice qué hay detrás."""
    global MOTOR
    if nuevo not in ("rapida", "natural", "natural2"):
        return {"ok": False, "motivo": "motor desconocido",
                "hay": list(VOZES) + ["rapida"]}
    MOTOR = nuevo
    ruta = voz_del_motor(nuevo)
    if nuevo != "rapida" and not (ruta and ruta.exists()):
        return {"ok": False, "motor": MOTOR, "motivo": "no está el modelo en " + str(DIR_VOZ),
                "vuelve_a": "rapida"}
    return {"ok": True, "motor": MOTOR, **{k: v for k, v in disponibilidad().items()
                                           if k != "dispositivos"}}


# ---------------------------------------------------------------- dispositivos ----
def dispositivos() -> dict:
    """Qué ve PipeWire de verdad, ahora mismo. Sin suposiciones."""
    def listar(que: str):
        if not shutil.which("pactl"):
            return []
        try:
            salida = subprocess.run(["pactl", "list", "short", que],
                                    capture_output=True, text=True, timeout=4).stdout
        except Exception:
            return []
        filas = []
        for linea in salida.splitlines():
            partes = linea.split("\t")
            if len(partes) >= 2:
                filas.append({"nombre": partes[1], "detalle": "\t".join(partes[2:4])})
        return filas

    sinks = listar("sinks")
    sources = listar("sources")
    altavoces = [s for s in sinks if s["nombre"] != "auto_null"]
    micros = [s for s in sources if not s["nombre"].endswith(".monitor")]
    return {
        "salidas": sinks, "entradas": sources,
        "altavoces_reales": altavoces, "microfonos_reales": micros,
        "suena": bool(altavoces), "escucha": bool(micros),
    }


def voz_del_motor(motor: str):
    """El onnx del motor pedido; `rapida` no usa onnx (es espeak-ng)."""
    if motor == "rapida":
        return None
    for clave in (motor, "natural"):
        ruta = VOZES.get(clave, (None,))[0]
        if ruta and ruta.exists():
            return ruta
    return None


def disponibilidad() -> dict:
    """Inventario honesto: motor, modelo, reproductor y dispositivos, con números."""
    ruta = voz_del_motor(MOTOR)
    return {
        "motor": MOTOR,
        "habla": ("espeak-ng" if MOTOR == "rapida" and ESPEAK else
                  ("piper" if ruta else None)),
        "espeak": ESPEAK,
        "piper_onnx": str(ruta) if ruta else None,
        "piper_cargado": sorted(k.name for k in _PIPER if _PIPER.get(k)),
        "piper_mb": round(ruta.stat().st_size / 1e6) if ruta else 0,
        "factor_medido": (0.14 if MOTOR == "rapida" else VOZES["natural"][2]),
        "stt": "vosk-small-es" if DIR_VOSK.exists() else None,
        "stt_mb": round(sum(f.stat().st_size for f in DIR_VOSK.rglob("*")
                            if f.is_file()) / 1e6, 1) if DIR_VOSK.exists() else 0,
        "reproductor": PW_PLAY, "grabador": ARECORD,
        "dispositivos": dispositivos(),
    }


# ----------------------------------------------------------------------- hablar ----
def _piper_de(ruta: Path):
    """El modelo se carga UNA vez por proceso: 14 s de carga no se pagan por frase."""
    with _PIPER_LOCK:
        if ruta not in _PIPER:
            from piper import PiperVoice
            t0 = time.time()
            _PIPER[ruta] = (PiperVoice.load(str(ruta)), round(time.time() - t0, 1))
        return _PIPER[ruta][0]


def _sintetizar(texto: str, destino: Path):
    destino.parent.mkdir(parents=True, exist_ok=True)
    ruta = voz_del_motor(MOTOR)
    if ruta:
        t0 = time.time()
        try:
            voz = _piper_de(ruta)
            with wave.open(str(destino), "wb") as w:
                voz.synthesize_wav(texto, w)
            if destino.stat().st_size > 2000:
                return "piper", int((time.time() - t0) * 1000)
        except Exception:
            pass   # si Piper falla, se cae a espeak sin dramatismo
    if ESPEAK:
        t0 = time.time()
        try:
            subprocess.run([ESPEAK, "-v", "es", "-s", "155", "-w", str(destino), texto],
                           capture_output=True, timeout=60)
            if destino.exists() and destino.stat().st_size > 2000:
                return "espeak-ng", int((time.time() - t0) * 1000)
        except Exception:
            pass
    return None, 0


def duracion_wav(ruta: Path) -> float:
    try:
        with wave.open(str(ruta)) as w:
            return round(w.getnframes() / float(w.getframerate()), 2)
    except Exception:
        return 0.0


def salida_por_defecto() -> str:
    """El sink que PipeWire usa ahora; `auto_null` significa silencio físico."""
    if not shutil.which("pactl"):
        return "desconocida"
    try:
        return subprocess.run(["pactl", "get-default-sink"], capture_output=True,
                              text=True, timeout=4).stdout.strip() or "desconocida"
    except Exception:
        return "desconocida"


def limpiar_tmp(retencion=RETENCION_TMP) -> int:
    """Tira los WAV de hablar/escucha más viejos que `retencion` segundos.

    Devuelve cuántos quitó. Nunca toca un directorio que no existe y nunca falla hacia
    fuera: la limpieza no puede tumbar una respuesta.
    """
    quitados = 0
    try:
        ahora = time.time()
        for ruta in list(TMP.glob("decir-*.wav")) + list(TMP.glob("escucha-*.wav")):
            try:
                if ahora - ruta.stat().st_mtime > retencion:
                    ruta.unlink()
                    quitados += 1
            except OSError:
                pass
    except OSError:
        pass
    return quitados


def hablar(texto: str, reproducir: bool = True) -> dict:
    """Sintetiza (y de paso reproduce). Devuelve números, nunca promesas."""
    texto = (texto or "").strip()
    if not texto:
        return {"ok": False, "motivo": "no hay texto que decir"}
    TMP.mkdir(parents=True, exist_ok=True)
    limpiar_tmp()
    ruta = TMP / f"decir-{int(time.time()*1000)}.wav"
    motor, ms = _sintetizar(texto, ruta)
    if not motor:
        return {"ok": False, "motivo": "ningún motor de voz produjo audio",
                "hay": disponibilidad()}
    segundos = duracion_wav(ruta)
    disp = dispositivos()
    r = {"ok": True, "motor": motor, "ms_sintesis": ms, "audio_segundos": segundos,
         "archivo": str(ruta), "caracteres": len(texto), "reproducido": False,
         "altavoz_real": disp["suena"], "sink": salida_por_defecto(),
         "factor": round((ms / 1000) / max(segundos, 0.01), 2), "nota": ""}
    if reproducir:
        if PW_PLAY:
            try:
                proc = subprocess.run([PW_PLAY, str(ruta)], capture_output=True, timeout=300)
                # rc 0 con auto_null NO es sonido: es el nulo de PipeWire tragándose
                # el audio. `reproducido` sólo es verdad si hay un altavoz real detrás.
                r["reproducido"] = proc.returncode == 0 and disp["suena"]
                if proc.returncode != 0:
                    r["nota"] = "pw-play respondió " + (proc.stderr.decode()[:120] or str(proc.returncode))
            except Exception as e:
                r["nota"] = f"pw-play falló: {type(e).__name__}"
        else:
            r["nota"] = "no hay pw-play ni paplay en el equipo"
    r["dispositivos"] = disp
    if not disp["suena"]:
        r["nota"] = (r["nota"] + " " if r["nota"] else "") + \
            "la única salida es auto_null: no hay altavoz físico (HDMI o dongle USB)."
    return r


def hablar_en_hilo(texto: str) -> int:
    """El puente llama esto y sigue atendiendo: la voz nunca bloquea una orden."""
    with _LOCK:
        while len(_COLA) >= _MAX_COLA:
            _COLA.pop(0)
        ident = len(_TAREAS) + 1
        _COLA.append(ident)

    def correr():
        r = hablar(texto)
        r["id"] = ident
        r["texto"] = texto[:120]
        with _LOCK:
            _TAREAS.append(r)
            _HIST[ident] = r
            while len(_TAREAS) > 20:
                viejo = _TAREAS.pop(0)
                _HIST.pop(viejo.get("id"), None)
            if ident in _COLA:
                _COLA.remove(ident)

    threading.Thread(target=correr, daemon=True, name=f"cort-voz-{ident}").start()
    return ident


def tarea(ident):
    """Resultado de una frase ya sintetizada, o None si todavía no terminó."""
    with _LOCK:
        return _HIST.get(ident)


def pendientes() -> int:
    with _LOCK:
        return len(_COLA)


# --------------------------------------------------------------------- escuchar ----
def _modelo_vosk():
    global _VOSK
    with _VOSK_LOCK:
        if _VOSK is None:
            from vosk import Model
            os.environ.setdefault("VK_FFTLIB_DISABLE", "1")
            _VOSK = Model(str(DIR_VOSK))
        return _VOSK


def transcribir_wav(ruta) -> dict:
    """Transcribe un WAV mono 16 bits. Sirve para probar sin micrófono."""
    if not DIR_VOSK.exists():
        return {"ok": False, "motivo": "no está el modelo de Vosk en " + str(DIR_MODELOS)}
    try:
        from vosk import KaldiRecognizer
        with wave.open(str(ruta)) as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2:
                return {"ok": False, "motivo": "el WAV debe ser mono y 16 bits"}
            sr = w.getframerate()
            rec = KaldiRecognizer(_modelo_vosk(), sr)
            trozos, t0 = [], time.time()
            while True:
                datos = w.readframes(4000)
                if not datos:
                    break
                if rec.AcceptWaveform(datos):
                    trozos.append(json.loads(rec.Result()).get("text", ""))
            trozos.append(json.loads(rec.FinalResult()).get("text", ""))
            audio = round(w.getnframes() / float(sr), 2)
        return {"ok": True, "texto": " ".join(t for t in trozos if t).strip(),
                "segundos_audio": audio, "ms_proceso": int((time.time() - t0) * 1000),
                "motor": "vosk-small-es"}
    except Exception as e:
        return {"ok": False, "motivo": f"{type(e).__name__}: {e}"}


def escuchar(segundos: int = 5) -> dict:
    """Graba del micrófono real y transcribe. Si no hay micro, lo dice con nombre."""
    disp = dispositivos()
    if not disp["microfonos_reales"]:
        return {"ok": False, "motivo": "no hay micrófono de captura en este equipo",
                "vio": disp["entradas"],
                "hace_falta": "un dongle USB con micro, o el micrófono del teléfono (F7)"}
    if not ARECORD:
        return {"ok": False, "motivo": "no está arecord (paquete alsa-utils)"}
    TMP.mkdir(parents=True, exist_ok=True)
    ruta = TMP / f"escucha-{int(time.time())}.wav"
    try:
        subprocess.run([ARECORD, "-q", "-c", "1", "-r", str(RATE_STT), "-f", "S16_LE",
                        "-d", str(int(segundos)), str(ruta)],
                       capture_output=True, timeout=segundos + 10)
    except Exception as e:
        return {"ok": False, "motivo": f"arecord falló: {type(e).__name__}"}
    r = transcribir_wav(ruta)
    r["archivo"] = Path(ruta).name
    # Lo que ella dictó no se queda escrito: se transcribe y se tira. `archivo`
    # sigue dicho por su nombre, para que la consola cuente qué se oyó.
    try:
        Path(ruta).unlink()
    except OSError:
        pass
    return r


class EscuchaContinua:
    """Escucha por turnos: arecord -> Vosk -> callback con el texto final.

    El puente levanta esto con `mic_on` y lo baja con `mic_off`. No intenta oír si
    no hay micrófono: devuelve el motivo, porque prometer escucha sin micro es la
    mentira que la fase F1 vino a matar.
    """

    def __init__(self, al_texto, al_estado=None):
        self.al_texto = al_texto
        self.al_estado = al_estado or (lambda e: None)
        self.parar = threading.Event()
        self.hilo = None
        self.estado = "apagada"
        self.errores = []
        self.textos = 0

    def arrancar(self) -> dict:
        if self.hilo and self.hilo.is_alive():
            return {"ok": True, "estado": self.estado, "nota": "ya estaba andando"}
        disp = dispositivos()
        if not disp["microfonos_reales"]:
            self.estado = "sin micro"
            self.al_estado(self.estado)
            return {"ok": False, "estado": self.estado,
                    "motivo": "no hay micrófono de captura", "vio": disp["entradas"]}
        if not ARECORD:
            self.estado = "sin arecord"
            return {"ok": False, "estado": self.estado, "motivo": "falta alsa-utils"}
        self.parar.clear()
        self.hilo = threading.Thread(target=self._correr, daemon=True, name="cort-mic")
        self.hilo.start()
        self.estado = "escuchando"
        self.al_estado(self.estado)
        return {"ok": True, "estado": self.estado}

    def detener(self) -> dict:
        self.parar.set()
        self.estado = "apagada"
        self.al_estado(self.estado)
        return {"ok": True, "estado": self.estado}

    def _correr(self):
        from vosk import KaldiRecognizer
        proc = subprocess.Popen(
            [ARECORD, "-q", "-c", "1", "-r", str(RATE_STT), "-f", "S16_LE", "-t", "raw"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        rec = KaldiRecognizer(_modelo_vosk(), RATE_STT)
        try:
            while not self.parar.is_set():
                datos = proc.stdout.read(4000)
                if not datos:
                    break
                if rec.AcceptWaveform(datos):
                    texto = json.loads(rec.Result()).get("text", "").strip()
                    if texto:
                        self.textos += 1
                        self.al_texto(texto)
            texto = json.loads(rec.FinalResult()).get("text", "").strip()
            if texto:
                self.textos += 1
                self.al_texto(texto)
        except Exception as e:
            self.errores.append(f"{type(e).__name__}: {e}")
            self.estado = "error"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()


# ------------------------------------------------------------------------- CLI ----
def main(argv):
    orden = argv[1] if len(argv) > 1 else "estado"
    if orden == "estado":
        print(json.dumps(disponibilidad(), indent=2, ensure_ascii=False))
    elif orden == "decir":
        texto = " ".join(argv[2:]) or "CORT en línea. La voz de salida funciona."
        print(json.dumps(hablar(texto), indent=2, ensure_ascii=False))
    elif orden == "probar":
        texto = " ".join(argv[2:]) or "Hola Sandra, soy CORT y esta es mi voz real en la Canaima."
        print(json.dumps(hablar(texto, reproducir=False), indent=2, ensure_ascii=False))
    elif orden == "escuchar":
        n = int(argv[2]) if len(argv) > 2 else 5
        print(json.dumps(escuchar(n), indent=2, ensure_ascii=False))
    elif orden == "transcribir":
        print(json.dumps(transcribir_wav(argv[2]), indent=2, ensure_ascii=False))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
