#!/usr/bin/env python3
"""Censo del repertorio de comandos que CORT anuncia en pantalla.

El panel «REPERTORIO DE COMANDOS» promete una lista de frases. Este script toma
esa lista (tal como la muestra la página) y mide, comando por comando:

  1. si alguna regla local del puente lo coge hoy (intentos_locales);
  2. qué familia de trabajo necesita realmente (acciones de PC, música, correo,
     domótica, visión, conversación...), que es lo que dice cuánta falta hace.

No inventa nada: si el puente no tiene regla y no hay backend, se apunta como
silencio. Salida = la tabla del informe INFORME_FUNCIONES.md.

Uso:
    python3 cort_repertorio.py comandos.json     # lista de frases en un JSON
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cort_server as cs  # noqa: E402

# Orden importante: lo primero que cuadra gana. Cada familia dice qué hace falta.
FAMILIAS = [
    ("equipo y clima (datos reales del puente)",
     ("hora", "fecha", "dia es", "clima", "temps", "pleuvoir", "temperature", "viento",
      "alertas meteorolog", "navidad", "edad tengo", "calcule", "calculatrice")),
    ("antivirus y seguridad", ("virus", "antivirus", "auditor", "seguridad", "analyse")),
    ("temporizadores, notas, tareas, compras",
     ("minuteur", "temporizador", "alarma", "recuerdame", "note que", "memoriza", "notes",
      "tarea", "pendientes", "compras", "lista de compras", "vaciar", "vacia")),
    ("conversación e identidad (cerebro LLM)",
     ("quien te creo", "quien eres", "chiste", "cita", "inspira", "silence", "tais-toi",
      "capital", "moneda", "deletrea", "como se dice", "como se escribe", "traduis",
      "password", "contraseña", "dado", "numero entre", "pile ou face", "cuentame")),
    ("acciones sobre el equipo (capa Linux)",
     ("abre", "ouvre", "ferme", "cierra", "modo trabajo", "volumen", "brillo", "captura",
      "screenshot", "apaga el ordenador", "explorador", "terminal", "notepad", "paint",
      "administrador", "ajustes", "bloc de notas", "carpeta", "documents", "bureau",
      "descargas", "images", "videos", "musique", "dossier", "chrome", "steam")),
    ("música y vídeo (Spotify/YouTube/IPTV)",
     ("musique", "spotify", "playlist", "youtube", "video", "videos", "artiste", "chancon",
      "volumen sube", "pause", "lecture", "iptv", "tendances", "suscriptores", "canal")),
    ("crear con IA (imagen, música, web, prompt)",
     ("crea un sitio", "crea un prompt", "crea una imagen", "genera una musica", "genera un video",
      "fais-moi un rap", "canta")),
    ("domótica Home Assistant",
     ("luz", "enchufe", "calefaccion", "sala", "ha ", "domotica")),
    ("globo 3D y mapas",
     ("terre", "globe", "mapa", "pasa sobre", "where", "donde esta", "position", "rute",
      "ruta de", "globo")),
    ("visión y control de pantalla",
     ("que estas viendo", "mira mi pantalla", "clic en", "ecribe", "champ", "cette image")),
    ("correo, documentos y calendario",
     ("email", "gmail", "docs", "sheet", "documentos de google", "eventos", "calendar",
      "pdf", "whatsapp")),
    ("deportes y restaurantes",
     ("partido", "classement", "score", "restaurante", "pizzeria", "sushi")),
]


def familia(texto):
    q = cs.sin_acentos(texto.lower())
    for nombre, llaves in FAMILIAS:
        if any(k in q for k in llaves):
            return nombre
    return "sin clasificar"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    comandos = json.loads(pathlib.Path(sys.argv[1]).read_text())
    estado = cs.leer_estado()

    por_familia, conteo = {}, {}
    cogido, silencio = [], []
    for c in comandos:
        f = familia(c)
        conteo[f] = conteo.get(f, 0) + 1
        por_familia.setdefault(f, []).append(c)
        try:
            r = cs.intentos_locales(c, estado)
        except Exception as e:
            r = None
            print(f"  (excepción probando {c!r}: {type(e).__name__})")
        if r:
            # Aquí no se decide si la respuesta es ACIERTADA: se imprime tal cual
            # para revisarla a ojo. Decir "lo hace" sin leer qué dice sería mentir.
            cogido.append((c, (r[0] or "")[:110]))
        else:
            silencio.append(c)

    print(f"comandos anunciados por la interfaz: {len(comandos)}")
    print(f"  los coge una regla local hoy: {len(cogido)}  (revisar el texto abajo)")
    print(f"  sin nadie que los atienda:    {len(silencio)}")
    print("\n--- por familia (lo que hace falta para cada una) ---")
    for f, n in sorted(conteo.items(), key=lambda kv: -kv[1]):
        print(f"{n:4d}  {f}")
    print("\n--- lo que dice hoy una regla local, tal cual ---")
    for c, r in cogido:
        print(f"  «{c}»\n      -> {r}")
    print(f"\nsalida reproducible: python3 {pathlib.Path(__file__).name} {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
