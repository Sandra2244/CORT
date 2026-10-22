"""Prueba decisiva del clima por ciudad y del registro de código, SIN red.

Cuatro cosas compradas de una vez, y ninguna sale de este portátil:

  1. `sitio_nombrado`: «¿qué tiempo hace en Gijón ahora mismo?» tiene que dar
     `Gijón`, y «el clima de la semana» NO tiene que dar `Semana`.
  2. `local_command`: la frase de clima se contesta con el tiempo, y la que NO es
     clima («tengo poco tiempo») se va al cerebro con `None`.
  3. La honestidad: si el geocoder dice que el nombre no existe, CORT tiene que
     repetir el nombre entre comillas en vez de dar el tiempo de otra ciudad ni
     decir «no hay internet».
  4. `es_programacion`: «hazme una app del clima en Python» es código, no clima.

No hay ni una petición a Open-Meteo: se sustituye `sensors.weather` por un gemelo
que devuelve los campos EXACTOS que se midieron el 2026-10-22 contra el servicio
vivo (`current` + `daily`, con `lugar`, `cielo`, `max`, `min`, `lluvia`). Y
`memory.DB` se va a un directorio temporal: el `cort_memory.db` de la dueña no se
abre. La tabla WMO sí se prueba de verdad, porque es código local.

Uso:  python3 scripts/prueba-clima.py     (un segundo, sin servidor, sin cuota)
"""
import pathlib
import sys
import tempfile

TRAJO = pathlib.Path(tempfile.mkdtemp(prefix="cort-clima-"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backend" / "app"))

import memory          # noqa: E402
memory.DB = TRAJO / "cort_memory.db"

import sensors         # noqa: E402
import brain           # noqa: E402

FALLOS = []


def dice_ok(que, como):
    print(f"  ok   {que:46} {como}")


def falla(que, como):
    FALLOS.append(que)
    print(f"  FALLA {que:46} {como}")


def espero(que, obtenido, querido):
    if obtenido == querido:
        dice_ok(que, repr(obtenido))
    else:
        falla(que, f"dio {obtenido!r} y tenía que dar {querido!r}")


# ── 1 · el topónimo de la frase ────────────────────────────────────────────────
print("\n· sitio_nombrado: qué ciudad se nombró (y cuál NO)")
espero("en Gijón ahora mismo", brain.sitio_nombrado("el tiempo en Gijón ahora mismo"), "Gijón")
espero("en nueva york mañana", brain.sitio_nombrado("¿qué tiempo hace en nueva york mañana?"), "Nueva York")
espero("en las palmas", brain.sitio_nombrado("el clima en las palmas"), "Las Palmas")
espero("en la paz", brain.sitio_nombrado("¿qué tiempo hace en la paz?"), "La Paz")
espero("de la semana (no es ciudad)", brain.sitio_nombrado("el clima de la semana"), "")
espero("¿tengo tiempo? (no es ciudad)", brain.sitio_nombrado("¿tengo tiempo?"), "")
espero("sin ciudad nombrada", brain.sitio_nombrado("¿qué tiempo hace?"), "")

# ── 2 · la tabla del cielo, que antes mentía ───────────────────────────────────
print("\n· cielo_de: el código WMO traducido (el bug viejo decía «despejado» a todo)")
espero("código 0", sensors.cielo_de(0), "despejado")
espero("código 61", sensors.cielo_de(61), "lluvia débil")
espero("código 95", sensors.cielo_de(95), "tormenta eléctrica")
espero("código 3", sensors.cielo_de(3), "nublado")
espero("código loco 1234", sensors.cielo_de(1234), "cielo sin clasificar (código 1234)")
espero("sin código", sensors.cielo_de(None), "sin dato de cielo")

# ── 3 · la frase dicha con lo que hay, sin inventar ────────────────────────────
print("\n· frase: lo puesto en español, con los campos que midieron en Open-Meteo")
MADRIGAL = {"ok": True, "lugar": "Sevilla, España", "temp": 20.4, "sensacion": 19.1,
            "humedad": 55.0, "viento": 8.7, "codigo": 1, "cielo": "mayormente despejado",
            "max": 26.0, "min": 11.0, "lluvia": 0.0, "cielo_manana": "nublado",
            "lluvia_manana": 3.0, "max_manana": 24.0, "min_manana": 12.0}
dicha = sensors.frase(MADRIGAL)
if "Sevilla" in dicha and "20 °C" in dicha and "mayormente despejado" in dicha:
    dice_ok("ciudad + temperatura + cielo", dicha)
else:
    falla("ciudad + temperatura + cielo", dicha)
# Sin mañana lluviosa no puede salir la advertencia de lluvia; y sin sensación
# distinta tampoco se menciona: las dos son pruebas de que NO rellena huecos.
if "Mañana" not in dicha:
    dice_ok("sin aviso de mañana (3 % de lluvia)", "no lo saca")
else:
    falla("sin aviso de mañana", "sacó una alerta con un 3 %")
if "sensación" not in dicha:
    dice_ok("sin sensación (1 °C de diferencia)", "no la inventa")
else:
    falla("sin sensación", "la sacó con 1 °C de diferencia")
corto = dict(MADRIGAL, sensacion=31.0, lluvia_manana=80.0, cielo_manana="tormenta eléctrica")
fr = sensors.frase(corto)
espero("con sensación y mañana seria", ("sensación 31 °C" in fr, "80 % de lluvia" in fr), (True, True))
espero("sin datos no hay frase", sensors.frase({"ok": False, "error": "sin-lugar"}), "")

# ── 4 · el mando local, con un gemelo de `sensors.weather` ─────────────────────
print("\n· local_command: a quién le contesta la frase (sin abrir el navegador)")
LLAMADAS = []


def clima_falso(lugar=None, lat=None, lon=None):
    LLAMADAS.append(lugar)
    if lugar and lugar.casefold() in ("yopopox", "xd"):
        return {"ok": False, "error": "sin-lugar", "busca": lugar}
    if lugar:
        return dict(MADRIGAL, lugar=f"{lugar}, España")
    return dict(MADRIGAL, lugar="La Guaira")


sensors.weather = clima_falso                      # el gemelo, no la red

espero("«el tiempo en Gijón ahora mismo» pide GIJÓN",
       brain.local_command("el tiempo en Gijón ahora mismo").startswith("En Gijón"), True)
espero("y la ciudad llegó al sensor", LLAMADAS[-1], "Gijón")
espero("la de Sevilla busca a Sevilla",
       brain.local_command("¿qué tiempo hace en Sevilla?").startswith("En Sevilla"), True)
espero("sin ciudad nombrada va por IP", brain.local_command("¿qué tiempo hace?"),
       "En La Guaira: 20 °C, mayormente despejado, viento 9 km/h, humedad 55 %. "
       "Hoy entre 11 y 26 °C, con un 0 % de probabilidad de lluvia.")
espero("la ciudad que no existe se dice con su nombre",
       "«Yopopox»" in brain.local_command("¿qué tiempo hace en Yopopox?"), True)
espero("y NO da el tiempo de otra ciudad",
       "Sevilla" in brain.local_command("¿qué tiempo hace en Yopopox?"), False)
espero("«el clima de la semana» no se queja de Semana",
       "«Semana»" in brain.local_command("el clima de la semana"), False)
espero("«tengo poco tiempo» no es clima", brain.local_command("tengo poco tiempo"), None)
espero("«qué hora es» sigue siendo hora", "son las" in brain.local_command("¿qué hora es?").lower(), True)

# ── 5 · el registro de código no le roba la frase al clima ─────────────────────
print("\n· es_programacion: cuándo la pregunta va al cerebro y no al sensor")
espero("hazme una app del clima en python", brain.es_programacion("hazme una app del clima en python"), True)
espero("cómo arreglo este error de kotlin", brain.es_programacion("cómo arreglo este error de kotlin"), True)
espero("explícame este bucle", brain.es_programacion("explícame este bucle"), True)
espero("¿qué tiempo hace en Sevilla?", brain.es_programacion("¿qué tiempo hace en Sevilla?"), False)
espero("qué hora es", brain.es_programacion("qué hora es"), False)
espero("hazme una nota de la compra", brain.es_programacion("hazme una nota de la compra"), False)
espero("el programa de la tele", brain.es_programacion("el programa de la tele"), False)

# La consigna: misma función, dos registros, y el nombre elegido sigue llegando.
if "registro de programación" in brain.system_prompt("coder") and \
        "registro de programación" not in brain.system_prompt():
    dice_ok("system_prompt(modo)", "el de código es otro texto, y el de siempre intacto")
else:
    falla("system_prompt(modo)", "los dos registros salen iguales")

# Y el mando: en `offline` la frase de código no puede contestar con el tiempo.
brain.cfg = lambda: {"mode": "auto", "ollama_url": "http://no-hay", "ollama_model": "x",
                     "groq_key": "", "gemini_key": "", "gemini_model": "y"}
LLAMADAS.clear()
respuesta, fuente = brain.think("hazme una app del clima en python", [])
espero("el código no se contesta con el clima", fuente, "offline")
espero("y lo dice en español", "cerebro de código" in respuesta, True)
espero("el sensor no se tocó", LLAMADAS, [])
respuesta, fuente = brain.think("¿qué tiempo hace en Madrid?", [])
espero("el clima sí sigue siendo local", fuente, "local")
espero("y por la ciudad pedida", LLAMADAS, ["Madrid"])

# ── 6 · la preferencia `ciudad` del Perfil, en un disco prestado ───────────────
print("\n· la ciudad guardada en PERFIL (base de datos temporal, no la suya)")
memory.set_profile("ciudad", "Barcelona")
LLAMADAS.clear()
espero("«¿qué tiempo hace?» usa la del Perfil",
       brain.local_command("¿qué tiempo hace?").startswith("En Barcelona"), True)
espero("y una ciudad nombrada gana a la del Perfil",
       brain.local_command("el tiempo en Valencia").startswith("En Valencia"), True)

print()
if FALLOS:
    print(f"clima: {len(FALLOS)} FALLA(S) -> {', '.join(FALLOS)}")
    sys.exit(1)
print("clima cosido: la ciudad se busca, se nombra y, si no existe, se dice.")
