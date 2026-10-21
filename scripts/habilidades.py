#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera las DOS tablas de frases de CORT desde una sola lista:
  · apps/apk/assets/habilidades.json  (la que viaja dentro del APK)
  · el cuerpo de Cerebro.tablaDelCodigo()  (el suelo, cuando el asset falta)

Se escribe aquí una vez y se vierte en los dos sitios para que nunca se separen:
cuando las tablas difieren, la dueña oye una cosa según cómo cargó el asset, y eso
es imposible de ver desde el teléfono. `scripts/prueba-costura.py` comprueba que
sigan siendo las mismas.

Orden = prioridad: primero las exactas, al final las de prefijo {resto}.
"""
import json, re, unicodedata, textwrap

import os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (id, accion, param, respuesta, [patrones])
REGLAS = [
    # ── volumen ────────────────────────────────────────────────────────
    ("volumen-sube", "volumen", "sube", "Subo el volumen.", [
        "sube el volumen", "subir el volumen", "sube volumen", "subele el volumen",
        "sube un poco el volumen", "mas volumen", "mas fuerte", "mas alto",
        "sube el sonido", "sube la musica", "volumen mas alto", "pon el volumen mas alto",
    ]),
    ("volumen-baja", "volumen", "baja", "Lo bajo.", [
        "baja el volumen", "bajar el volumen", "baja volumen", "bajale el volumen",
        "baja un poco el volumen", "menos volumen", "mas bajo", "mas suave",
        "baja el sonido", "baja la musica", "volumen mas bajo", "dejalo mas bajo",
    ]),
    ("volumen-max", "volumen", "max", "Volumen al máximo.", [
        "volumen al maximo", "sube todo el volumen", "ponlo al maximo", "sube al maximo",
        "volumen al tope", "al maximo el volumen", "sube el volumen al maximo",
        "pon el volumen al maximo", "pon el volumen al tope",
    ]),
    ("volumen-min", "volumen", "min", "Volumen al mínimo.", [
        "volumen al minimo", "baja todo el volumen", "baja al minimo", "al minimo el volumen",
        "pon el volumen al minimo", "pon el volumen bajito",
    ]),
    ("volumen-callar", "volumen", "callar", "Silencio. Sigo escuchando.", [
        "silencio", "pon silencio", "callate", "calla", "sin sonido", "mudo",
        "quita el sonido", "apaga el sonido", "sin ruido", "calla la musica",
        "mute", "ponlo en mudo", "en mudo",
    ]),

    # ── linterna ───────────────────────────────────────────────────────
    ("linterna-on", "linterna", "on", "Alumbro.", [
        "enciende la linterna", "prende la linterna", "pon la linterna", "dame luz",
        "enciende linterna", "necesito luz", "linterna encendida", "alumbrame",
        "prendele la linterna", "ponme luz",
    ]),
    ("linterna-off", "linterna", "off", "Apago la luz.", [
        "apaga la linterna", "apagar la linterna", "quita la linterna", "apaga luz",
        "linterna off", "apaga la luz", "linterna apagada", "ya no alumbres", "apaga el foco",
    ]),
    ("linterna-alterna", "linterna", "alterna", "Cambio la linterna.", [
        "linterna", "la linterna", "linterna por favor",
    ]),

    # ── modo juego ─────────────────────────────────────────────────────
    ("juego-on", "juego", "on", "Modo juego: me hago pequeña para no estorbarte.", [
        "modo juego", "activa el modo juego", "activa modo juego", "pon el modo juego",
        "voy a jugar", "me pongo a jugar", "estoy jugando", "activar modo juego",
        "modo gamer", "no me interrumpas mientras juego",
    ]),
    ("juego-off", "juego", "off", "Vuelvo a por el oído.", [
        "sal del modo juego", "desactiva el modo juego", "desactiva modo juego",
        "quita el modo juego", "modo juego off", "ya termine de jugar", "vuelve cort",
        "desactivar modo juego", "sal de modo juego",
    ]),

    # ── avisos del teléfono ────────────────────────────────────────────
    ("avisos", "avisos", "avisos", "Te los cuento.", [
        "lee mis avisos", "leer mis avisos", "leeme los avisos", "que me llego",
        "ultimos avisos", "mis notificaciones", "lee mis notificaciones", "hay avisos nuevos",
        "avisos", "mirame los avisos", "que me escribieron", "hay mensajes nuevos",
        "leeme whatsapp", "revisa mis mensajes", "que hay de nuevo",
    ]),

    # ── música ─────────────────────────────────────────────────────────
    ("musica-pausa", "musica", "pausa", "La dejo en pausa.", [
        "pausa", "pon en pausa", "para la musica", "pausa la musica", "deten la musica",
        "stop", "para todo", "quieto", "apaga la musica",
    ]),
    ("musica-reanuda", "musica", "reanuda", "Sigo.", [
        "continua", "reanuda", "sigue la musica", "vuelve la musica", "vuelve",
        "dale play", "reanuda la musica", "sigue sonando", "pon la musica otra vez",
    ]),
    ("musica-siguiente", "musica", "siguiente", "Voy con la siguiente.", [
        "siguiente", "pasa", "cambia de cancion", "la siguiente", "siguiente cancion",
        "pista siguiente", "pon la siguiente", "otra cancion", "dale a la siguiente",
    ]),
    ("musica-anterior", "musica", "anterior", "Vuelvo a la anterior.", [
        "anterior", "la anterior", "cancion anterior", "retrocede", "la de antes",
        "pista anterior", "pon la anterior", "vuelve a la anterior",
    ]),
    ("musica-mueve", "musica", "mueve", "Me muevo un poco en la cancion.", [
        "muevete", "adelanta", "retrocede un poco", "adelanta un poco",
        "adelanta la cancion", "atrasa la cancion",
    ]),

    # ── memoria ────────────────────────────────────────────────────────
    ("memoria-listar", "memoria", "listar", "Te leo lo que tengo guardado.", [
        "que sabes de mi", "que recuerdas", "que tengo guardado", "dime lo que sabes",
        "que guardaste", "tus recuerdos", "mi informacion",
    ]),

    # ── saludo y cháchara ──────────────────────────────────────────────
    ("saludo-hola", "saludo", "", "Hola, te escucho.", [
        "hola", "buenos dias", "buenas tardes", "buenas noches", "oye cort", "cort",
        "hola cort", "ey cort", "buenas", "ey",
    ]),
    ("saludo-quien-eres", "saludo", "", "Soy CORT, tu asistente en este teléfono.", [
        "quien eres", "como te llamas", "que eres", "quien eres tu", "tu nombre",
        "eres humana", "quien te hizo",
    ]),
    ("saludo-gracias", "saludo", "", "Para eso estoy.", [
        "gracias", "muchas gracias", "muy amable", "de nada", "gracias cort",
    ]),
    ("saludo-estas-ahi", "saludo", "", "Bien, aquí en el teléfono, sin tu portátil.", [
        "estas ahi", "me oyes", "funcionas", "como estas", "estas alli", "aqui estas",
        "estas despierta", "cort estas", "me escuchas",
    ]),
    ("saludo-adios", "saludo", "", "Qué bueno que estés.", [
        "adios", "hasta luego", "chao", "nos vemos", "hasta luego cort",
    ]),
    ("saludo-tiempo", "saludo", "tiempo",
        "Sin la nube no te sé el tiempo; actívala en el perfil y te lo digo.", [
        "que tiempo hace", "que tiempo", "como esta el tiempo", "va a llover",
        "hace frio", "hace calor", "lleva paraguas",
    ]),
    ("saludo-puedes", "saludo", "",
        "Mando sobre el aparato: volumen, linterna, alarmas, temporizadores, abrir apps, "
        "poner música, llamar, buscar, leer tus avisos y acordarme de lo que me cuentes. "
        "Y sin internet sé hacer cuentas, porcentajes, cambios de unidad, y darte la hora "
        "y el día. Lo que no sepa, se lo pregunto a la nube.", [
        "que puedes hacer", "para que sirves", "ayuda", "comandos", "que sabes hacer",
        "dime que puedes", "para que sirves tu", "ayudame", "que puedes hacer por mi",
    ]),

    # ── las de prefijo {resto}: siempre al final, de la más larga a la más corta ──
    ("memoria-guardar", "memoria", "guardar:{resto}", "Me quedo con eso.", [
        "acuerdate de {resto}", "acuedate {resto}", "recuerda que {resto}",
        "guarda que {resto}", "aprende que {resto}", "anota {resto}", "apunta {resto}",
        "acuerdate que {resto}", "recuerdame {resto}", "ten presente {resto}",
        "no se olvide {resto}", "memoriza {resto}",
    ]),
    ("memoria-buscar", "memoria", "buscar:{resto}", "Miro en mis recuerdos.", [
        "que sabes de {resto}", "que recuerdas de {resto}", "recuerdas {resto}",
        "que te conte de {resto}", "sabes de {resto}", "en que quedo lo de {resto}",
    ]),
    ("alarma", "alarma", "{resto}", "Pongo la alarma.", [
        "pon una alarma a las {resto}", "pon alarma a las {resto}",
        "despiertame a las {resto}", "despierta a las {resto}", "alarma a las {resto}",
        "alerta a las {resto}", "alarma {resto}", "programa una alarma a las {resto}",
        "necesito una alarma a las {resto}", "despiertame en {resto}",
        "ponme una alarma {resto}",
    ]),
    ("temporizador", "temporizador", "{resto}", "Cuento hacia atrás y te aviso.", [
        "pon un temporizador de {resto}", "temporizador de {resto}", "temporizador {resto}",
        "cuenta atras de {resto}", "cuenta atras {resto}", "timer {resto}",
        "cronometro de {resto}", "avisame en {resto}", "avisa en {resto}",
        "me avisas en {resto}",
    ]),
    ("llamar", "llamar", "{resto}", "Abro el marcador.", [
        "llama al numero {resto}", "llama a {resto}", "llamar a {resto}",
        "marca a {resto}", "llama {resto}", "llamada a {resto}", "marcame {resto}",
    ]),
    ("buscar", "buscar", "{resto}", "Busco en el navegador.", [
        "busca en la red {resto}", "busca en internet {resto}", "buscar {resto}",
        "busca {resto}", "googlea {resto}", "investiga {resto}",
        "quiero saber sobre {resto}",
    ]),
    ("poner", "poner", "{resto}", "Pongo eso.", [
        "pon la cancion {resto}", "pon el video {resto}", "ponme musica de {resto}",
        "reproduce {resto}", "poner {resto}", "pon {resto}", "suena {resto}",
        "dale a {resto}", "escucha {resto}",
    ]),
    ("abrir-ajustes", "abrir", "ajustes", "Abro los ajustes.", ["configuracion"]),
    ("abrir-app", "abrir", "{resto}", "Abro.", [
        "abre el navegador de {resto}", "abre la aplicacion {resto}", "entra en {resto}",
        "abreme {resto}", "abre {resto}", "abrir {resto}", "arranca {resto}",
        "lanza {resto}", "ve a {resto}", "navega {resto}", "prende {resto}",
        "quiero abrir {resto}",
    ]),
]


def normaliza(t):
    """Copia de `Cerebro.normaliza`: minúsculas, sin tildes, sin signos, un espacio."""
    bajo = unicodedata.normalize("NFD", t).replace("\u0301", "").replace("\u0300", "")
    bajo = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    bajo = bajo.lower()
    bajo = re.sub(r"[¿?¡!.,;:\"“”'()]", " ", bajo)
    return re.sub(r"\s+", " ", bajo).strip()


def sin_repetidos(patrones, ident):
    vistos, fuera = set(), []
    for p in patrones:
        n = normaliza(p)
        if n in vistos:
            fuera.append((ident, p))
            continue
        vistos.add(n)
        if "{" in p and not p.rstrip().endswith("{resto}"):
            raise SystemExit(f"{ident}: {p!r} tiene {{resto}} fuera del final")
        if "{" in p and p.rstrip().endswith("{resto}") and not p.rstrip().endswith(" {resto}"):
            raise SystemExit(f"{ident}: {p!r} pega {{resto}} a la palabra")
    return fuera


def lista_json(items, sangria, ancho=96):
    """`["a", "b", ...]` partido SOLO entre elementos: nunca se corta un literal."""
    fuera, trozo = [], "["
    for i, it in enumerate(items):
        pedazo = json.dumps(it, ensure_ascii=False) + ("," if i + 1 < len(items) else "")
        if len(trozo) + len(pedazo) + 1 > ancho and trozo != "[":
            fuera.append(trozo.rstrip())
            trozo = " " * sangria
        trozo += (" " if not trozo.endswith("[") else "") + pedazo
    fuera.append(trozo.rstrip() + "]")
    return "\n".join(fuera) if len(fuera) > 1 else fuera[0]


def main():
    # 1 · la lista de frases no puede tener duplicados en toda la tabla
    todas = {}
    for (ident, acc, param, resp, ps) in REGLAS:
        for p in ps:
            n = normaliza(p)
            if n in todas:
                raise SystemExit(f"frase duplicada: {n!r} en {ident} y en {todas[n]}")
            todas[n] = ident

    dudosas = []
    for (ident, acc, param, resp, ps) in REGLAS:
        dudosas += sin_repetidos(ps, ident)
    if dudosas:
        raise SystemExit("patrones repetidos dentro de la misma regla: " + str(dudosas))

    # 2 · el JSON que viaja dentro del APK
    cabecera = json.load(open(f"{REPO}/apps/apk/assets/habilidades.json", encoding="utf-8"))
    patrones_json = []
    for (ident, acc, param, resp, ps) in REGLAS:
        patrones_json.append({"id": ident, "accion": acc, "param": param,
                              "patrones": ps, "respuesta": resp})
    vocab = ["volumen", "linterna", "alarma", "temporizador", "abrir", "poner", "llamar",
             "buscar", "musica", "avisos", "juego", "memoria", "saludo", "desconocido"]
    abre = ["whatsapp", "spotify", "youtube", "maps", "gmail", "calendario", "instagram",
            "facebook", "tiktok", "navegador", "ajustes", "musica", "telefono",
            "mensajes", "reloj", "wifi", "bluetooth", "teclado", "avisos", "camara",
            "galeria", "archivos", "telegram", "discord", "netflix", "calculadora"]
    salida = {
        "version": 3,
        "nota": cabecera["nota"] + " GENERADOR: esta tabla y la de `Cerebro.tablaDelCodigo` "
                "se vierten de la misma lista (`scripts/habilidades.py`); `prueba-costura.py` "
                "comprueba que sigan siendo las mismas frases.",
        "vocabulario": cabecera["vocabulario"],
        "parametros": {
            "volumen": ["sube", "baja", "max", "min", "callar"],
            "linterna": ["on", "off", "alterna"],
            "abrir": abre,
            "musica": ["pausa", "reanuda", "siguiente", "anterior", "mueve"],
            "juego": ["on", "off"],
            "memoria": ["listar", "guardar:{resto}", "buscar:{resto}"],
        },
        "patrones": patrones_json,
    }
    texto = ["{"]
    for k in ("version", "nota", "vocabulario"):
        texto.append("  " + json.dumps(k) + ": " + json.dumps(salida[k], ensure_ascii=False) + ",")
    texto.append('  "parametros": {')
    for k, v in salida["parametros"].items():
        texto.append("    " + json.dumps(k) + ": " + lista_json(v, 4 + len(k) + 4) + ",")
    texto[-1] = texto[-1].rstrip(",")
    texto.append("  },")
    texto.append('  "patrones": [')
    for i, r in enumerate(patrones_json):
        texto.append("    { " + ", ".join(f"{json.dumps(k)}: {json.dumps(r[k], ensure_ascii=False)}"
                                          for k in ("id", "accion", "param")) + ",")
        texto.append('      "patrones": ' + lista_json(r["patrones"], 6) + ",")
        texto.append('      "respuesta": ' + json.dumps(r["respuesta"], ensure_ascii=False) + " }"
                     + ("," if i + 1 < len(patrones_json) else ""))
    texto.append("  ]")
    texto.append("}")
    open(f"{REPO}/apps/apk/assets/habilidades.json", "w", encoding="utf-8").write(
        "\n".join(texto) + "\n")

    # 3 · el cuerpo de `tablaDelCodigo`
    # Se parte SIEMPRE entre argumentos completos: un literal de Java no se corta,
    # y un string partido a mitad de línea es justo el error que da `javac` en la 173.
    cuerpo = []
    for (ident, acc, param, resp, ps) in REGLAS:
        cab = f'        reglas.add(r({json.dumps(acc, ensure_ascii=False)}, ' \
              f'{json.dumps(param, ensure_ascii=False)}, {json.dumps(resp, ensure_ascii=False)},'
        lineas = [cab]
        trozo = " " * 12
        for p_ in ps:
            literal = json.dumps(p_, ensure_ascii=False) + ","
            if len(trozo) + len(literal) > 96 and trozo.strip():
                lineas.append(trozo.rstrip())
                trozo = " " * 12
            trozo += " " + literal
        if trozo.strip() and trozo.strip() != ",":
            lineas.append(trozo.rstrip())
        lineas[-1] = lineas[-1].rstrip(",") + "));"
        cuerpo.append("\n".join(lineas))
    java = "\n".join(cuerpo)

    ruta = f"{REPO}/apps/apk/src/com/cort/ia/Cerebro.java"
    original = open(ruta, encoding="utf-8").read()
    # se reescribe desde el comentario de orden hasta el cierre del método
    marca = original.index("    /**\n     * Orden = prioridad.")
    fin = original.index("\n    }\n", original.index("private void tablaDelCodigo()")) + len("\n    }\n")
    nuevo = original[:marca] + (
        "    /**\n"
        "     * Orden = prioridad. Las exactas van antes de las de prefijo `{resto}`; y las\n"
        "     * de prefijo cortas (`pon la linterna`) antes de las generales (`pon {resto}`),\n"
        "     * para que una no le robe la frase a la otra.\n"
        "     *\n"
        "     * ESTO NO SE ESCRIBE A MANO: sale de `scripts/habilidades.py`, la misma lista\n"
        "     * que genera `assets/habilidades.json`. Cambiar una frase en un sitio y no en\n"
        "     * el otro es el tipo de fallo que sólo se ve en la boca del teléfono.\n"
        "     */\n"
        "    private void tablaDelCodigo() {\n" + java + "\n    }\n"
    ) + original[fin:]
    open(ruta, "w", encoding="utf-8").write(nuevo)

    print(f"reglas={len(REGLAS)} frases={len(todas)}")
    print("escalón de respuestas largas:", sum(1 for r in REGLAS if len(r[3]) > 90))


main()
