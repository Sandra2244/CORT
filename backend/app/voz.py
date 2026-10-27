"""La boca de CORT en el escritorio: voz con el motor que YA tiene el equipo.

Por qué existe este módulo (medido en el portátil de Sandra el 2026-10-22):
la cara de PC habla con `window.speechSynthesis` del navegador. Abriendo la hoja
`scripts/sonda-voz.html` en el Chromium de este equipo (Electron 43, Chrome 150)
el resultado es:

    motor: sí        voces: 0        voiceschanged: dispara y sigue en 0

Es decir: el navegador responde pero **no da ninguna voz**, así que `speak()` se
queda en un silencio que parece funcionar (salta `onend`, CORT no se atasca, y no
se oye nada). Por eso los deslizadores de tono y velocidad de la ventana 07 ·
Perfil eran decorativos en Linux: no había boca que modular. En Windows y macOS la
misma ruta sí funciona, y en el teléfono manda el puente nativo (`CortNative.java`
con `TextToSpeech`), así que esto **no** es un apaño para Android: es el agujero
de Linux.

El equipo, en cambio, sí tiene motor de voz instalado y comprobado aquí:

    /usr/bin/espeak-ng  con voces en español y datos de diccionario
    /usr/bin/speech-dispatcher

`espeak-ng` escribe un WAV en 0,1 s y casi sin memoria, así que la boca del
escritorio es un proceso hija del núcleo: `POST /api/voice/say` → WAV → `<audio>`.
Y da tres mandos reales, medidos byte a byte sobre el mismo texto:

    -v es / es-419 / es+f4   cambia la forma de onda (timbre distinto)   md5 distinto
    -p 20 | 50 | 80          cambia la onda (grave ↔ agudo)              md5 distinto
    -s 120 | 220             79.972 B ↔ 40.114 B                          la mitad de duración

Las voces se **prueban** al enumerarlas: de `--voices=es` salen también las
`*-mbrola-*`, y aquí no hay datos mbrola instalados (`espeak-ng` responde
«Please install necessary MBROLA voice» y sale con 1). Una lista con voces que
fallan sería peor que no tener lista, así que cada voz se sintetiza de verdad y
sólo se ofrecen las que producen audio.

Nada de esto habla con Internet ni toca sus claves: es un binario local.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

# Los mandos de la cara (07 · Perfil) van en 0,5 … 1,5 y 1 = natural. `espeak-ng`
# usa otras escalas: `-p` de 0 a 99 (50 = natural) y `-s` palabras por minuto
# (175 = su defecto). Se mapea linealmente y se topea: un -p fuera de rango hace
# que el binario salga con error y CORT se quede muda sin decir por qué.
TONO_MIN, TONO_MAX = 0.5, 1.5
PITCH_NATURAL, PITCH_AMPLITUD, PITCH_TOPE = 50, 49, 99
VELOCIDAD_MIN, VELOCIDAD_MAX = 0.6, 1.6
WPM_NATURAL, WPM_MIN, WPM_MAX = 175, 80, 450

# Un párrafo largo no debe convertir el portátil en una centralita: 900 caracteres
# es la frase más larga que CORT dice por voz en la cara, y se corta por palabra.
MAX_TEXTO = 900

CANDIDATOS = ("espeak-ng", "espeak")

# Bases en español que ofrece CORT. Se filtran por las que este equipo de verdad
# pueda pronunciar; los nombres se leen del propio motor (línea por voz de
# `--voices=es`) y se completan con estas etiquetas, que son las que se ven.
BASES = {
    "es": ("Español (España)", "M"),
    "es-419": ("Español (Latinoamérica)", "M"),
    "es-mx": ("Español (México)", "M"),
}
# Variantes del motor: en espeak `+m*` suena a voz de hombre y `+f*` a voz de
# mujer. No están todas en todas las versiones, así que cada una se comprueba
# sintetizándola y viendo que la onda SALE DISTINTA de la base (si el motor ignora
# la variante, los bytes coinciden y la voz no se ofrece).
VARIANTES = {"+f2": "voz de mujer", "+f4": "voz de mujer grave",
             "+m3": "voz de hombre grave", "+m5": "voz de hombre muy grave"}

FRASE_SONDA = "ya"

_BINARIO: str | None = None
_PROBADO = False
_ESTADO: dict | None = None
cerrojo = threading.Lock()             # la cara pide /api/voice varias veces a la vez


def binario() -> str | None:
    """Ruta del motor de voz, o None. Se busca una vez y se guarda."""
    global _BINARIO, _PROBADO
    if not _PROBADO:
        for nombre in CANDIDATOS:
            _BINARIO = shutil.which(nombre)
            if _BINARIO:
                break
        _PROBADO = True
    return _BINARIO


def remeder() -> None:
    """Olvida lo aprendido (para las pruebas y por si instala el motor sin reiniciar)."""
    global _BINARIO, _PROBADO, _ESTADO
    with cerrojo:
        _BINARIO, _PROBADO, _ESTADO = None, False, None


def _archivo_de_trabajo(tmp: Path) -> Path:
    """Dentro de `tmp` se escribe y se pisa el WAV de cada prueba de voz.

    Un solo directorio temporal para toda la enumeración: `mkdtemp` por cada voz
    dejaría quince carpetas huérfanas en `/tmp` en cada arranque del núcleo.
    """
    return tmp / "voz.wav"


def _ejecuta(args: list[str], timeout: int = 8):
    """Corre el motor sin shell (no hay comandos que ensamblar con texto de la cara).

    Devuelve el resultado, o la cadena `''` si el proceso no arranca o se pasa del
    tiempo: así la llamada puede distinguirlo en el mensaje que lee la cara.
    """
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


def _suena(voz: str, ruta: Path, timeout: int = 8) -> bool:
    """Sintetiza una palabra con esa voz y dice si de verdad sale audio."""
    b = binario()
    if not b:
        return False
    r = _ejecuta([b, "-v", voz, "-w", str(ruta), FRASE_SONDA], timeout)
    return bool(r and r.returncode == 0 and ruta.exists() and ruta.stat().st_size > 1024)


def _huella(voz: str, ruta: Path) -> bytes:
    """Los bytes del audio de esa voz, o b'' si no se puede sintetizar."""
    b = binario()
    if not b:
        return b""
    r = _ejecuta([b, "-v", voz, "-w", str(ruta), FRASE_SONDA])
    if r is None or r.returncode != 0 or not ruta.exists():
        return b""
    return ruta.read_bytes()


def tonos_a_pitch(tono: float) -> int:
    """El deslizador (0,5 … 1,5, 1 = natural) al `-p` del motor (0 … 99).

    El tope es 99, no la amplitud: con `min(49, …)` todo lo que fuera «más agudo
    de lo natural» se aplastaba contra el natural y el deslizador de tono sólo
    servía para la mitad de su recorrido. Medido: 0,5 → 26 · 1 → 50 · 1,5 → 74.
    """
    return max(0, min(PITCH_TOPE, round(PITCH_NATURAL + (tono - 1.0) * PITCH_AMPLITUD)))


def velocidades_a_wpm(velocidad: float) -> int:
    """El deslizador (0,6 … 1,6) a palabras por minuto del motor."""
    return max(WPM_MIN, min(WPM_MAX, round(WPM_NATURAL * velocidad)))


def _huella(voz: str, ruta: Path) -> bytes:
    """Los bytes del audio de esa voz, o b'' si no se puede sintetizar."""
    b = binario()
    if not b:
        return b""
    try:
        r = subprocess.run([b, "-v", voz, "-w", str(ruta), FRASE_SONDA],
                           capture_output=True, text=True, timeout=8)
        if r.returncode != 0 or not ruta.exists():
            return b""
        return ruta.read_bytes()
    except (OSError, subprocess.SubprocessError):
        return b""
    finally:
        ruta.unlink(missing_ok=True)


def _voces_del_motor() -> list[dict]:
    """Lo que lista `--voices=es`, leído por columnas y sin inventar nada.

    La salida real en este equipo (medida) es así:

        Pty Language       Age/Gender VoiceName          File   Other Languages
         5  es              --/M      Spanish_(Spain)    roa/es
         5  es-419          --/M      Spanish_(Latin_America) roa/es-419
         7  es-es           --/M      spanish-mbrola-1   mb/mb-es1

    El nombre va sin espacios (usan guiones bajos), así que la columna 4 es el
    nombre y la 3 el sexo. Las `mbrola` se descartan sin ni siquiera probarlas:
    piden un motor extra que aquí no está.
    """
    b = binario()
    if not b:
        return []
    try:
        r = subprocess.run([b, "--voices=es"], capture_output=True, text=True, timeout=8)
        crudo = r.stdout
    except (OSError, subprocess.SubprocessError):
        return []
    voces = []
    for linea in crudo.splitlines()[1:]:
        campos = linea.split()
        if len(campos) < 4:
            continue
        nombre, codigo = campos[3], campos[1]
        if "mbrola" in nombre.lower():
            continue
        if codigo.split("-")[0] != "es":
            continue
        voces.append({"codigo": codigo, "nombre": nombre})
    return voces


def timbres() -> list[dict]:
    """Las voces que este equipo puede pronunciar de verdad, con nombre bonito.

    Se comprueba sintetizando: primero la base, y de cada variante sólo se ofrece
    si su audio sale DISTINTO de la base (un `-v es+zz` inválido no da error: el
    motor lo ignora y habla igual, y eso sería una opción mentirosa en el desplegable).
    """
    if not binario():
        return []
    tmp = Path(tempfile.mkdtemp(prefix="cort-voz-"))
    ruta = _archivo_de_trabajo(tmp)
    salida: list[dict] = []
    try:
        vistas: set[str] = set()
        for v in _voces_del_motor():
            if v["codigo"] in vistas:
                continue
            vistas.add(v["codigo"])
            if not _suena(v["codigo"], ruta):
                continue
            etiqueta, _sexo = BASES.get(v["codigo"], (v["nombre"], "M"))
            salida.append({"voz": v["codigo"], "nombre": etiqueta,
                           "male": True, "fuente": "motor"})
            base = _huella(v["codigo"], ruta)
            for sufijo, como_suena in VARIANTES.items():
                audio = _huella(v["codigo"] + sufijo, ruta)
                if not audio or audio == base:
                    continue                    # variante inexistente o ignorada
                salida.append({"voz": v["codigo"] + sufijo,
                               "nombre": f"{etiqueta} · {como_suena}",
                               "male": sufijo.startswith("+m"), "fuente": "variante"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return salida


def estado() -> dict:
    """Qué boca tiene este equipo. La cara llama aquí una vez al arrancar.

    Se cachea porque enumerar timbres cuesta ~1 s de síntesis de prueba y la cara
    lo pide con cada `loadProfile()`.
    """
    global _ESTADO
    with cerrojo:
        if _ESTADO is not None:
            return dict(_ESTADO)
        b = binario()
        if not b:
            _ESTADO = {"motor": None, "binario": "", "voces": [],
                       "motivo": "no hay espeak-ng ni espeak instalados"}
            return dict(_ESTADO)
        voces = timbres()
        _ESTADO = {"motor": Path(b).name, "binario": b, "voces": voces,
                   "motivo": "" if voces else "el motor está pero no pronuncia el español"}
        return dict(_ESTADO)


def limpio(texto: str) -> str:
    """Lo que la cara manda a hablar, puesto a raya: sin marcas raras, sin
    control, y cortado por palabra (no por sílaba a la mitad de «ordenador»)."""
    t = re.sub(r"[`*_#>]+", " ", str(texto or ""))
    t = re.sub(r"https?://\S+", "el enlace", t)
    t = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > MAX_TEXTO:
        t = t[:MAX_TEXTO].rsplit(" ", 1)[0]
    return t


def sintetiza(texto: str, voz: str = "", tono: float = 1.0, velocidad: float = 1.0) -> dict:
    """Devuelve `{"ok": True, "wav": <bytes>}` o `{"ok": False, "error": …}`.

    El `error` viaja hasta la consola de la cara, que es donde Sandra puede leerlo;
    un silencio sin motivo es lo que hizo dudar de toda la sección de voz.
    """
    b = binario()
    if not b:
        return {"ok": False, "error": "sin-motor"}
    t = limpio(texto)
    if not t:
        return {"ok": False, "error": "vacio"}
    # La voz sólo se fija si el equipo la tiene. Si eligió una de las nuestras y
    # luego cambió de PC, se habla con la del motor en vez de quedarse muda.
    permitidas = {v["voz"] for v in estado().get("voces", [])}
    tmp = Path(tempfile.mkdtemp(prefix="cort-voz-"))
    ruta = _archivo_de_trabajo(tmp)
    args = [b, "-w", str(ruta)]
    if voz and voz in permitidas:
        args += ["-v", voz]
    args += ["-p", str(tonos_a_pitch(tono)), "-s", str(velocidades_a_wpm(velocidad)), t]
    try:
        r = _ejecuta(args, timeout=30)
        if r is None:
            return {"ok": False, "error": "no-responde",
                    "motivo": "el motor de voz no arranca o tarda más de 30 s"}
        if r.returncode != 0 or not ruta.exists():
            return {"ok": False, "error": "no-suena",
                    "motivo": (r.stderr or r.stdout or "").strip()[:160]}
        return {"ok": True, "wav": ruta.read_bytes(),
                "voz": voz if (voz and voz in permitidas) else "",
                "pitch": tonos_a_pitch(tono), "wpm": velocidades_a_wpm(velocidad)}
    except OSError as e:
        return {"ok": False, "error": "binario-fallando", "motivo": str(e)[:160]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
