"""Prueba decisiva de la boca del escritorio, SIN sonido, SIN red y SIN espeak.

`voz.py` es la razón por la que CORT habla en Linux: el navegador de este equipo da
CERO voces (medido el 2026-10-22 con `scripts/sonda-voz.html`: `motor: sí ·
voces: 0`, y `voiceschanged` dispara con la lista vacía), así que la cara habla por
el motor del equipo a través del núcleo. Como un test que dependa de `espeak-ng`
sería un test que se salta en la mitad de los equipos, aquí el motor es un **gemelo
de papel** que imita la salida y los códigos de salida MEDIDOS, y se compran de
verdad estas seis cosas:

  1. Los mandos: el deslizador de tono (0,5 … 1,5) y el de velocidad (0,6 … 1,6)
     tienen que llegar al motor convertidos y topeados. Con el bug que había
     (`min(49, …)`) todo lo de «más agudo» se aplastaba contra el natural.
  2. La lista de voces: se leen las columnas de `--voices=es` REALES, se tiran las
     `mbrola` (aquí no hay datos mbrola: el binario responde «Please install
     necessary MBROLA voice» y sale con 1) y no se inventa ninguna.
  3. La honestidad del timbre: una variante que el motor IGNORA (habla igual que la
     base) NO se ofrece, aunque el binario salga con 0.
  4. La orden que se le manda al binario: sin shell, con `-v` sólo si la voz existe
     en este equipo, y con `-p`/`-s` ya convertidos.
  5. Los fracasos con nombre: `sin-motor`, `vacio`, `no-suena`, `no-responde` — el
     silencio sin motivo fue lo que hizo dudar de toda la sección.
  6. Los temporales: cada síntesis crea UNA carpeta `cort-voz-*` y la borra; si se
     filtrara una por frase, el `/tmp` de su PC crecería con cada saludo.

Y si EN ESTE equipo hay `espeak-ng` de verdad, se hace además la comprobación real
(un WAV con bytes) y se dice; en un runner sin el binario se anuncia sin fallar.

Uso:  python3 scripts/prueba-voz.py     (dos segundos, sin servidor, sin cuota)
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backend" / "app"))

import voz            # noqa: E402

FALLOS = []


def dice_ok(que, como):
    print(f"  ok   {que:44} {como}")


def falla(que, como):
    FALLOS.append(que)
    print(f"  FALLA {que:44} {como}")


def espero(que, obtenido, querido):
    if obtenido == querido:
        dice_ok(que, repr(obtenido))
    else:
        falla(que, f"dio {obtenido!r} y tenía que dar {querido!r}")


# ── 1 · los mandos llegan convertidos y topeados ───────────────────────────────
print("\n· 1 · el deslizador → la orden del motor")
espero("tono natural (1,0)", voz.tonos_a_pitch(1.0), 50)
espero("tono grave (0,82 = JARVIS)", voz.tonos_a_pitch(0.82), 41)
espero("tono al fondo (0,5)", voz.tonos_a_pitch(0.5), 26)
espero("tono arriba (1,5)", voz.tonos_a_pitch(1.5), 74)
espero("tono fuera de rango (3,0)", voz.tonos_a_pitch(3.0), voz.PITCH_TOPE)
espero("tono en el fondo (0,0)", voz.tonos_a_pitch(0.0), 1)
espero("tono imposible (-1)", voz.tonos_a_pitch(-1.0), 0)
espero("velocidad natural (1,0)", voz.velocidades_a_wpm(1.0), 175)
espero("velocidad 0,6", voz.velocidades_a_wpm(0.6), 105)
espero("velocidad 1,6", voz.velocidades_a_wpm(1.6), 280)
espero("velocidad absurda (9)", voz.velocidades_a_wpm(9), voz.WPM_MAX)
if voz.tonos_a_pitch(1.5) > voz.tonos_a_pitch(1.0):
    dice_ok("el tope no aplasta el agudo", "74 > 50")
else:
    falla("el tope no aplasta el agudo", "1,5 da lo mismo que 1,0: el tope era la amplitud")

# ── 2 · el texto que se manda a hablar ─────────────────────────────────────────
print("\n· 2 · limpio(): lo que la cara manda, puesto a raya")
espero("sin marcas de markdown", voz.limpio("**hola** _mundo_ `x` >y"), "hola mundo x y")
espero("un enlace se nombra", voz.limpio("mira https://a.b/c y sigue"), "mira el enlace y sigue")
espero("sin control", voz.limpio("a\x00b\x07c"), "a b c")
espero("vacíos a una línea", voz.limpio("  uno\n\n   dos  "), "uno dos")
corto = voz.limpio("palabra " * 400)
if len(corto) <= voz.MAX_TEXTO and not corto.endswith("palab"):
    dice_ok("cortado por palabra", f"{len(corto)} caracteres, termina «{corto[-8:]}»")
else:
    falla("cortado por palabra", f"{len(corto)} caracteres, termina «{corto[-8:]}»")
espero("None no rompe", voz.limpio(None), "")

# ── el motor de papel ──────────────────────────────────────────────────────────
SALIDA_VOICES = """Pty Language       Age/Gender VoiceName          File                 Other Languages
 3  es-es           --/F      spanish-mbrola-3   mb/mb-es3            (es 3)
 5  es              --/M      Spanish_(Spain)    roa/es
 7  es-es           --/M      spanish-mbrola-1   mb/mb-es1            (es 7)
 5  es-419          --/M      Spanish_(Latin_America) roa/es-419           (es-mx 6)
 8  fr              --/M      French             roa/fr
"""


class Papel:
    """Imita `subprocess.run` para espeak-ng con la salida y los bytes medidos.

    `idénticas=True` hace que las variantes hablen IGUAL que la base, que es el
    caso del motor que ignora una variante inexistente sin dar error.
    """

    def __init__(self, binario="/usr/bin/espeak-ng", identicas=False, rompe=False,
                 tarda=False, sin_voces=False):
        self.binario, self.identicas, self.rompe, self.tarda = binario, identicas, rompe, tarda
        self.sin_voces = sin_voces
        self.ordenes = []

    def which(self, nombre):
        return self.binario if nombre == "espeak-ng" else None

    def run(self, args, capture_output=True, text=True, timeout=None):
        self.ordenes.append(list(args))
        if self.tarda:
            raise subprocess.TimeoutExpired(args, timeout or 1)
        if "-w" in args:
            ruta = pathlib.Path(args[args.index("-w") + 1])
            voz_index = args.index("-v") + 1 if "-v" in args else None
            codigo = args[voz_index] if voz_index is not None else "natural"
            if self.rompe or codigo.endswith("+rota"):
                ruta.write_bytes(b"")
                return Resultado(1, "", "Error: The specified espeak-ng voice does not exist.\n")
            if self.identicas or not voz_index:
                cuerpo = b"RIFF\x00\x00\x00\x00WAVE base"       # la base, o sin -v
            else:
                cuerpo = b"RIFF\0\0\0\0WAVE " + codigo.encode() + b"-distinto"
            ruta.write_bytes(cuerpo + b"." * 2000)
            return Resultado(0, "", "")
        if any(a.startswith("--voices") for a in args):
            return Resultado(0, "" if self.sin_voces else SALIDA_VOICES, "")
        return Resultado(0, "", "")


class Resultado:
    def __init__(self, code, out, err):
        self.returncode, self.stdout, self.stderr = code, out, err


REAL_WHICH, REAL_RUN = shutil.which, subprocess.run


def con_papel(p):
    """Pone el gemelo y devuelve el arreglo.

    Se guarda `which` y `run` VERDADEROS una sola vez, al principio del script, y
    SIEMPRE se restaura a ellos. Con «restaurar lo que había al poner» el punto 4
    (que anida un gemelo dentro de otro) habría dejado el gemelo puesto hasta el
    final, y el punto 8 —el que dice «motor real de este equipo»— habría medido
    papel en vez de espeak. Medido: el audio real pesa 51.780 B y el de papel 2.027 B.
    """
    voz.shutil.which, voz.subprocess.run = p.which, p.run
    voz.remeder()

    def deshaz():
        voz.shutil.which, voz.subprocess.run = REAL_WHICH, REAL_RUN
        voz.remeder()
    return deshaz


# ── 3 · el equipo sin motor: hay que decirlo, no callarse ──────────────────────
print("\n· 3 · sin espeak en el equipo")
p = Papel(binario=None)
deshaz = con_papel(p)
espero("binario()", voz.binario(), None)
e = voz.estado()
espero("estado().motor", e["motor"], None)
espero("voces", e["voces"], [])
if "espeak" in e["motivo"]:
    dice_ok("el motivo se nombra", e["motivo"])
else:
    falla("el motivo se nombra", repr(e["motivo"]))
espero("sintetiza dice por qué", voz.sintetiza("hola")["error"], "sin-motor")
deshaz()

# ── 4 · la lista de voces se lee, no se inventa ───────────────────────────────
print("\n· 4 · las voces de `--voices=es` (salida real medida)")
p = Papel()
deshaz = con_papel(p)
leidas = voz._voces_del_motor()
espero("códigos en español", [v["codigo"] for v in leidas], ["es", "es-419"])
espero("nombres del motor", [v["nombre"] for v in leidas],
       ["Spanish_(Spain)", "Spanish_(Latin_America)"])
if not any("mbrola" in v["nombre"].lower() for v in leidas):
    dice_ok("mbrola fuera", "ninguna voz que necesita el motor mbrola")
else:
    falla("mbrola fuera", "se coló una voz mbrola")
if not any(v["codigo"].startswith("fr") for v in leidas):
    dice_ok("francés fuera", "sólo español")
else:
    falla("francés fuera", "se coló otra lengua")

timbres = voz.timbres()
nombres = [t["voz"] for t in timbres]
espero("bases y variantes", len(nombres), 2 + 2 * len(voz.VARIANTES))
if all(not n.startswith("es-419-mal") for n in nombres):
    dice_ok("sin códigos sueltos", ", ".join(nombres[:3]) + " …")
else:
    falla("sin códigos sueltos", repr(nombres))
genero = {t["voz"]: t["male"] for t in timbres}
etiquetas = {t["voz"]: t["nombre"] for t in timbres}
espero("las +f son de mujer", genero.get("es+f2", "NI ESTÁ EN LA LISTA"), False)
espero("las +m son de hombre", genero.get("es+m3", "NI ESTÁ EN LA LISTA"), True)
espero("la base es de hombre", genero.get("es", "NI ESTÁ EN LA LISTA"), True)
if "España" in etiquetas.get("es+f2", "") and "mujer" in etiquetas.get("es+f2", ""):
    dice_ok("etiqueta legible", etiquetas["es+f2"])
else:
    falla("etiqueta legible", repr(etiquetas.get("es+f2")))

# la variante que el motor ignora NO se ofrece
p2 = Papel(identicas=True)
deshaz2 = con_papel(p2)
solo_base = [t["voz"] for t in voz.timbres()]
espero("variante ignorada fuera", solo_base, ["es", "es-419"])
deshaz2()

# y un motor que no pronuncia nada se dice, no se disimula
p3 = Papel(sin_voces=True)
deshaz3 = con_papel(p3)
espero("motor sin español → 0 timbres", voz.timbres(), [])
espero("con motivo", voz.estado()["motivo"], "el motor está pero no pronuncia el español")
deshaz3()

# ── 5 · la orden que se le manda al binario ────────────────────────────────────
print("\n· 5 · sintetiza: qué se ejecuta y qué sale")
p4 = Papel()
deshaz4 = con_papel(p4)
e = voz.estado()                              # deja la lista cacheada, como en la vida real
permitidas = {v["voz"] for v in e["voces"]}
if {"es", "es+f4", "es-419"} <= permitidas:
    dice_ok("timbres disponibles", ", ".join(sorted(permitidas)[:3]) + " …")
else:
    falla("timbres disponibles", repr(sorted(permitidas)))
r = voz.sintetiza("A sus órdenes", voz="es+f4", tono=0.82, velocidad=1.2)
orden = p4.ordenes[-1]
espero("ok", r["ok"], True)
if r["ok"] and r["wav"][:4] == b"RIFF":
    dice_ok("sale audio", f"{len(r['wav'])} bytes RIFF")
else:
    falla("sale audio", repr(r)[:60])
if orden[0] == p4.binario:
    dice_ok("sin shell", "argv como lista, ejecutable primero")
else:
    falla("sin shell", repr(orden[0]))
espero("-v con la voz pedida", orden[orden.index("-v") + 1], "es+f4")
espero("-p convertido", orden[orden.index("-p") + 1], "41")
espero("-s convertido", orden[orden.index("-s") + 1], "210")
espero("el texto, al final", orden[-1], "A sus órdenes")
if not any(";" in a or "|" in a or "&" in a for a in orden):
    dice_ok("nada que el shell interprete", "ni ; ni | ni & en los argumentos")
else:
    falla("nada que el shell interprete", repr(orden))

# una voz que este equipo no tiene: se habla igual, pero SIN mentir en la respuesta
r2 = voz.sintetiza("hola", voz="no-existe+zz", tono=1.0, velocidad=1.0)
espero("sigua hablando", r2["ok"], True)
espero("y avisa que no usó esa voz", r2["voz"], "")
orden2 = p4.ordenes[-1]
if "-v" not in orden2:
    dice_ok("no manda la voz desconocida", "-v ausente")
else:
    falla("no manda la voz desconocida", repr(orden2))

espero("frase vacía", voz.sintetiza("   ")["error"], "vacio")
deshaz4()

# ── 6 · los fracasos tienen nombre ─────────────────────────────────────────────
print("\n· 6 · cuándo no suena, lo dice")
p5 = Papel(rompe=True)
deshaz5 = con_papel(p5)
voz.remeder()
e = voz.estado()
espero("motor que falla → 0 timbres", e["voces"], [])
r = voz.sintetiza("hola")
espero("error", r["error"], "no-suena")
if "MBROLA" in r.get("motivo", "").upper() or "espeak" in r.get("motivo", "").lower():
    dice_ok("con lo que dijo el motor", r["motivo"].strip()[:44])
else:
    falla("con lo que dijo el motor", repr(r.get("motivo")))
deshaz5()

p6 = Papel(tarda=True)
deshaz6 = con_papel(p6)
espero("timeout → no-responde", voz.sintetiza("hola")["error"], "no-responde")
deshaz6()

# ── 7 · no deja basura en /tmp ─────────────────────────────────────────────────
print("\n· 7 · los temporales se recogen")
tmp = pathlib.Path(tempfile.gettempdir())
antes = len(list(tmp.glob("cort-voz-*")))
p7 = Papel()
deshaz7 = con_papel(p7)
voz.remeder()
voz.estado()
for _ in range(3):
    voz.sintetiza("una frase distinta cada vez")
despues = len(list(tmp.glob("cort-voz-*")))
espero("carpetas nuevas que quedan", despues - antes, 0)
deshaz7()

# ── 8 · y si el motor existe AQUÍ, se comprueba de verdad ──────────────────────
print("\n· 8 · el motor real de este equipo (si lo hay)")
if shutil.which("espeak-ng") or shutil.which("espeak"):
    voz.remeder()
    real = voz.estado()
    if real["voces"]:
        dice_ok("timbres reales", f"{real['motor']} · {len(real['voces'])} comprobados: "
                + ", ".join(v["voz"] for v in real["voces"][:3]) + " …")
        wav = voz.sintetiza("A sus órdenes, señora.", voz=real["voces"][0]["voz"],
                            tono=0.82, velocidad=1.1)
        # El listón de 3.000 bytes no es un adorno: el papel de esta suite escribe
        # ~2.000 y el espeak real de aquí saca 51.780 para la misma frase. Si un
        # gemelo se quedara puesto, esta línea lo cazaría en vez de mentir.
        if wav.get("ok") and len(wav["wav"]) > 3000:
            dice_ok("audio real", f"{len(wav['wav'])} bytes · pitch {wav['pitch']} · {wav['wpm']} ppc")
        else:
            falla("audio real", f"{len(wav.get('wav', b''))} bytes — parece papel, no espeak: {str(wav)[:60]}")
    else:
        falla("timbres reales", f"{real['motor']} no pasó ni una voz: {real['motivo']}")
else:
    dice_ok("sin motor en este runner", "los puntos 3 a 7 con el gemelo de papel son los que valen")

if FALLOS:
    print(f"\nFALLO: {len(FALLOS)} comprobaciones: " + ", ".join(FALLOS))
    sys.exit(1)
print("\ntodo en orden: la boca del escritorio manda de verdad y dice por qué no.")
