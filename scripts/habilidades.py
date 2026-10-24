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
import saber as _saber
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# El otro medio diccionario: lo que CORT sabe CONTESTAR (la hora, las cuentas, la
# casa, la nube). Vive en `saber.py` porque su forma es distinta —título, capa y
# un caso de prueba— y se une aquí para que la cara, Java y las pruebas beban de
# la misma lista. Si se duplicara en dos ficheros, la ayuda prometería una cosa y
# `Razon` contestaría otra.
SABER = _saber.SABER

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
    # `destapar` ya existe en `Acciones.volumen` desde la 2.1, pero ninguna frase
    # lo pedía: el modo estaba escrito y mudo. Ahora tiene su intención.
    ("volumen-destapar", "volumen", "destapar", "Te destapo el sonido.", [
        "quita el silencio", "destapa el sonido", "quita el mudo", "vuelve el sonido",
    ]),

    # ── las tres manos que ya existían y no tenían frase ─────────────────
    # `Acciones` sabe del cronómetro, del estado y de la rejilla de apps desde
    # rondas anteriores, pero `Cerebro` no las nombraba: se podían tocar con el
    # dedo y no con la voz. La F14 las mete en el diccionario y en el vocabulario.
    ("cronometro", "cronometro", "mostrar",
     "Te enseño el cronómetro; Android no me deja ponerlo en marcha.", [
        "pon el cronometro", "abre el cronometro", "muestrame el cronometro",
        "quiero el cronometro",
    ]),
    ("estado", "estado", "", "Miro cómo va el teléfono.", [
        "estado del telefono", "como esta el telefono", "dime como va el telefono",
        "como va el aparato",
    ]),
    ("lanzadores", "lanzadores", "", "Te cuento las apps que veo.", [
        "que apps tengo", "lista mis apps", "dime que apps hay",
        "ensename mis aplicaciones",
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
    # F15 · la música por NOMBRE y las listas. Estas tres van antes de la regla
    # general «pon {resto}» (más abajo) o se comerían sus frases.
    ("musica-playlist", "musica", "lista:{resto}", "Pongo esa lista.", [
        "pon la playlist {resto}", "ponme la playlist {resto}",
        "reproduce la playlist {resto}", "pon la lista {resto}",
        "ponme la lista {resto}", "reproduce mi playlist {resto}",
        "quiero oir la playlist {resto}", "escucha la playlist {resto}",
    ]),
    ("musica-listas", "musica", "listas", "Miro tus listas.", [
        "que playlists tengo", "que playlists hay", "mis playlists", "mis listas",
        "que listas tengo", "que listas hay", "dime mis playlists",
        "listame las playlists",
    ]),
    ("musica-ecualiza", "musica", "ecualiza:{resto}", "Cambio el ecualizador.", [
        "pon el ecualizador en {resto}", "cambia el ecualizador a {resto}",
        "pon el ecualizador {resto}", "ecualizador {resto}", "ecualiza a {resto}",
        "ecualiza {resto}", "cambia el sonido a {resto}", "pon el sonido en {resto}",
    ]),
    ("musica-ecualiza-estado", "musica", "ecualizaestado", "Miro el ecualizador.", [
        "que ecualizador tengo", "como esta el ecualizador", "en que ecualizador esta",
        "dime el ecualizador", "que preset tengo", "que sonido tengo puesto",
        "como suena el ecualizador", "que ecualizacion hay",
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
    # F15 · «pon {resto}» ya no abre YouTube a ciegas: la cara busca PRIMERO en la
    # música del teléfono (`musicaPonerNombre`) y sólo si no hay nada cae al
    # buscador. La acción sigue siendo `musica`; el parámetro dice qué hacer.
    ("musica-pon-nombre", "musica", "poner:{resto}", "Busco esa cancion.", [
        "pon la cancion {resto}", "pon el video {resto}", "ponme musica de {resto}",
        "reproduce {resto}", "poner {resto}", "pon {resto}", "suena {resto}",
        "dale a {resto}", "escucha {resto}", "ponme {resto}",
        "cambialo a {resto}", "cambia a {resto}", "cambia la cancion a {resto}",
        "ponme la cancion {resto}",
    ]),
    ("abrir-ajustes", "abrir", "ajustes", "Abro los ajustes.", ["configuracion"]),
    ("abrir-app", "abrir", "{resto}", "Abro.", [
        "abre el navegador de {resto}", "abre la aplicacion {resto}", "entra en {resto}",
        "abreme {resto}", "abre {resto}", "abrir {resto}", "arranca {resto}",
        "lanza {resto}", "ve a {resto}", "navega {resto}", "prende {resto}",
        "quiero abrir {resto}",
    ]),
]


# El vocabulario cerrado que `Cerebro.ACCIONES` valida y que la cara sabe ejecutar.
# Está aquí, y no en tres sitios, para que una acción nueva no se cuele en el JSON
# y el teléfono la ignore en silencio: el generador escribe la misma lista en el
# asset y `prueba-costura.py` la compara con el `Set` de Java.
VOCABULARIO = ["volumen", "linterna", "alarma", "temporizador", "cronometro", "estado",
               "lanzadores", "abrir", "poner", "llamar", "buscar", "musica", "avisos",
               "juego", "memoria", "saludo", "desconocido"]

# Las dos cifras de la fase F14. No son adorno: si alguien borra media tabla para
# que el número «cuadre», el generador se para antes de escribir nada.
MIN_INTENTS = 91
MIN_FRASES = 736


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
    # 0 · la otra mitad del diccionario, con su forma comprobada ANTES de escribir
    # nada: una capa mal escrita mandaría una frase al fichero equivocado y la
    # prueba de no-locales la daría por buena para siempre.
    vistos_saber = set()
    for entrada in SABER:
        if len(entrada) != 5:
            raise SystemExit(f"entrada de saber.py con {len(entrada)} campos: {entrada!r}")
        ident, capa, titulo, ps, prueba = entrada
        if ident in vistos_saber:
            raise SystemExit(f"intención repetida en saber.py: {ident}")
        vistos_saber.add(ident)
        if capa not in ("razon", "casa", "nube"):
            raise SystemExit(f"{ident}: capa desconocida {capa!r}")
        if len(ps) != 8:
            raise SystemExit(f"{ident}: {len(ps)} frases; el diccionario pide 8 reales")
        if capa == "razon":
            if not (isinstance(prueba, tuple) and len(prueba) == 2):
                raise SystemExit(f"{ident}: una intención de razón necesita (frase, prefijo)")
            if prueba[0] not in ps:
                raise SystemExit(f"{ident}: la frase de prueba no está entre sus frases")
        elif prueba is not None:
            raise SystemExit(f"{ident}: casa/nube no llevan prueba local (su prueba es la contraria)")

    # 1 · la lista de frases no puede tener duplicados en toda la tabla
    todas = {}
    for (ident, acc, param, resp, ps) in REGLAS:
        if acc not in VOCABULARIO:
            raise SystemExit(f"{ident}: acción {acc!r} fuera del vocabulario")
        for p in ps:
            n = normaliza(p)
            if n in todas:
                raise SystemExit(f"frase duplicada: {n!r} en {ident} y en {todas[n]}")
            todas[n] = ident
    for ident, capa, titulo, ps, prueba in SABER:
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

    intents = len(REGLAS) + len(SABER)
    frases = len(todas)
    if intents < MIN_INTENTS or frases < MIN_FRASES:
        raise SystemExit(f"el diccionario se encogió: {intents} intenciones y {frases} frases "
                         f"(mínimo {MIN_INTENTS}/{MIN_FRASES})")

    # 2 · el JSON que viaja dentro del APK
    cabecera = json.load(open(f"{REPO}/apps/apk/assets/habilidades.json", encoding="utf-8"))
    # La nota que ya está en el fichero puede traer la coletilla del generador de
    # una pasada anterior: se corta para que correrlo dos veces no la repita.
    nota_base = cabecera["nota"].split(" GENERADOR:")[0]
    patrones_json = []
    for (ident, acc, param, resp, ps) in REGLAS:
        patrones_json.append({"id": ident, "accion": acc, "param": param,
                              "patrones": ps, "respuesta": resp})
    abre = ["whatsapp", "spotify", "youtube", "maps", "gmail", "calendario", "instagram",
            "facebook", "tiktok", "navegador", "ajustes", "musica", "telefono",
            "mensajes", "reloj", "wifi", "bluetooth", "teclado", "avisos", "camara",
            "galeria", "archivos", "telegram", "discord", "netflix", "calculadora"]
    salida = {
        "version": 4,
        "nota": nota_base + " GENERADOR: esta tabla, la de `Cerebro.tablaDelCodigo`, "
                "`ui/js/diccionario.js` y los casos de `apps/apk/prueba/` se vierten de la "
                "misma lista (`scripts/habilidades.py` + `scripts/saber.py`); "
                "`prueba-costura.py` comprueba que sigan siendo la misma cosa.",
        "vocabulario": "Las 'accion' sólo pueden ser: " + ", ".join(VOCABULARIO)
                + ". Cualquier otra se ignora al cargar (Cerebro.ACCIONES).",
        "parametros": {
            "volumen": ["sube", "baja", "max", "min", "callar", "destapar"],
            "linterna": ["on", "off", "alterna"],
            "abrir": abre,
            "musica": ["pausa", "reanuda", "siguiente", "anterior", "mueve",
                       "poner:{resto}", "lista:{resto}", "listas",
                       "ecualiza:{resto}", "ecualizaestado"],
            "juego": ["on", "off"],
            "memoria": ["listar", "guardar:{resto}", "buscar:{resto}"],
            "cronometro": ["mostrar"],
            "estado": [""],
            "lanzadores": [""],
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

    # 4 · lo que la CARA lee: el diccionario entero, con su capa y su ejemplo.
    # `mando` son las órdenes que mueven el aparato; `razon` lo que se contesta sin
    # red; `casa` y `nube` lo que necesita un modelo. La ayuda de la cara sale de
    # aquí, así que no puede prometer una frase que la tabla no tenga.
    entradas = []
    for (ident, acc, param, resp, ps) in REGLAS:
        entradas.append({
            "id": ident, "capa": "mando", "titulo": ident.replace("-", " · "),
            "accion": acc, "param": param, "dice": resp,
            "ejemplo": ps[0], "frases": ps,
        })
    for ident, capa, titulo, ps, prueba in SABER:
        entradas.append({"id": ident, "capa": capa, "titulo": titulo,
                         "ejemplo": ps[0], "frases": ps})
    por_capa = {capa: sum(1 for e in entradas if e["capa"] == capa)
                for capa in ("mando", "razon", "casa", "nube")}
    totales = {"intents": intents, "frases": frases, "porCapa": por_capa}
    ejemplos = ["¿qué hora es?", "¿cuánto es 7 x 8?", "¿cuánto es el 15 por ciento de 240?",
                "la mitad de 80", "3 km a millas", "cuánta propina dejo por 80",
                "pon el cronómetro", "qué apps tengo", "comprueba si 1996 es bisiesto"]
    faltan_ejemplos = [e for e in ejemplos if normaliza(e) not in todas]
    if faltan_ejemplos:
        raise SystemExit("un ejemplo de la ayuda no está en el diccionario: " + str(faltan_ejemplos))
    ayuda = [
        f"  {intents} intenciones y {frases} frases: {por_capa['mando']} órdenes, "
        f"{por_capa['razon']} de razón, {por_capa['casa']} de casa y {por_capa['nube']} de nube",
        "  " + " · ".join(ejemplos[:5]),
        "  " + " · ".join(ejemplos[5:]),
    ]
    js = ["/* GENERADO por `scripts/habilidades.py` desde `saber.py` y la tabla de",
          "   `REGLAS`. No se escribe a mano: la ayuda de la cara, el JSON del APK y",
          "   la tabla de `Cerebro.tablaDelCodigo` son la misma lista. */",
          "export const DICCIONARIO = " + json.dumps(entradas, ensure_ascii=False, indent=2) + ";",
          "export const TOTALES = " + json.dumps(totales, ensure_ascii=False) + ";",
          "export const EJEMPLOS = " + json.dumps(ejemplos, ensure_ascii=False) + ";",
          "export const AYUDA = " + json.dumps(ayuda, ensure_ascii=False) + ";",
          "",
          "/* La capa es la que manda: `mando` mueve el aparato, `razon` contesta sin",
          "   red, y `casa`/`nube` necesitan un modelo. */",
          "export function frasesDe(capa) {",
          "  return DICCIONARIO.filter(x => x.capa === capa).flatMap(x => x.frases);",
          "}",
          ""]
    open(f"{REPO}/ui/js/diccionario.js", "w", encoding="utf-8").write("\n".join(js))

    # 5 · los dos ficheros de casos que corre `Prueba5.java` en el portátil.
    # · casos-razon: TODAS las frases de razón (208), con el prefijo esperado sólo
    #   en la frase de prueba de cada intención. Así una frase nueva que `Razon`
    #   deje de contestar se ve, no se queda en promesa.
    # · casos-no-locales: TODAS las de casa y nube. Ni `Cerebro` las reclama ni
    #   `Razon` las resuelve; si un día una se contesta localmente con una respuesta
    #   floja, la suite se pone roja en vez de sonreír.
    razon, ajenas = [], []
    for ident, capa, titulo, ps, prueba in SABER:
        if capa == "razon":
            for p in ps:
                razon.append(p + "|" + (prueba[1] if p == prueba[0] else ""))
        else:
            ajenas += ps
    open(f"{REPO}/apps/apk/prueba/casos-razon.txt", "w", encoding="utf-8").write(
        "# GENERADO por scripts/habilidades.py — frase|prefijo (prefijo vacío: sólo no ser null)\n"
        + "\n".join(razon) + "\n")
    open(f"{REPO}/apps/apk/prueba/casos-no-locales.txt", "w", encoding="utf-8").write(
        "# GENERADO por scripts/habilidades.py — no puede contestarlas ni Cerebro ni Razon\n"
        + "\n".join(ajenas) + "\n")

    print(f"reglas={len(REGLAS)} saberes={len(SABER)} intents={intents} frases={frases} "
          f"(mando {por_capa['mando']}, razon {por_capa['razon']}, "
          f"casa {por_capa['casa']}, nube {por_capa['nube']})")
    print("escalón de respuestas largas:", sum(1 for r in REGLAS if len(r[3]) > 90))


main()
