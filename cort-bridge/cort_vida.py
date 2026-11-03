#!/usr/bin/env python3
"""CORT — vida diaria: lista de compras, notas, recordatorios y temporizadores.

Por qué este archivo existe aparte del puente: lo de cada día es lo único que tiene
que sobrevivir al apagado. Una lista que se pierde al cerrar la ventana es un adorno,
no una utilidad. Todo lo de aquí se escribe en JSON antes de responder, y si el disco
falla se dice con el error exacto en vez de contestar "listo".

No hay Obsidian en este equipo (verificado con `which obsidian`), así que las notas
viven en su propia carpeta: ~/.local/share/cort/vida. El panel de notas de la
plantilla se alimenta de aquí con `origen: real` y la nota de que no es Obsidian.

Uso en terminal:
  cort_vida.py estado                    qué hay guardado ahora mismo
  cort_vida.py compra "leche, 3 huevos"  añade a la lista
  cort_vida.py compras                    imprime la lista
  cort_vida.py nota "título" "texto"      guarda una nota
  cort_vida.py recordatorio "llamar" "10 minutos"
  cort_vida.py temporizador 180           3 minutos
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

CASA = Path(os.environ.get("CORT_HOME", str(Path.home())))
DATOS = Path(os.environ.get("CORT_DATOS", str(CASA / ".local" / "share" / "cort")))
VIDA = DATOS / "vida"

# un recordatorio se mira cada segundo; un temporizador avisado se apaga solo
_VELA: threading.Thread | None = None
_AL_VENCER: list = []            # callbacks que pone el puente (hilo separado)
PROXIMO_VENCIMIENTO: dict | None = None


# ------------------------------------------------------------------- archivos ----
def _ruta(nombre: str) -> Path:
    return VIDA / f"{nombre}.json"


def _leer(nombre: str, inicial):
    try:
        with open(_ruta(nombre), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return inicial
    except Exception:
        return inicial


def _escribir(nombre: str, datos) -> dict:
    """Escribe y reléye. Responder "guardado" sin haber vuelto a leer el archivo
    es la forma fina de mentir."""
    try:
        VIDA.mkdir(parents=True, exist_ok=True)
        with open(_ruta(nombre), "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        with open(_ruta(nombre), encoding="utf-8") as f:
            json.load(f)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "motivo": f"{type(e).__name__}: {e}"}


def sin_acentos(t: str) -> str:
    return "".join(c if not unicodedata.combining(c) else ""
                   for c in unicodedata.normalize("NFD", (t or "").lower()))


# --------------------------------------------------------------- compras ----
def compras() -> list:
    d = _leer("compras", {})
    if isinstance(d, list):          # alguien escribió la lista plana: se acepta
        return [str(i).strip() for i in d if str(i).strip()]
    return d.get("items", [])


def fijar_compras(items: list) -> dict:
    limpio = [str(i).strip()[:80] for i in (items or []) if str(i).strip()][:200]
    r = _escribir("compras", {"items": limpio, "hora": datetime.now().isoformat(timespec="seconds")})
    return {"ok": r["ok"], "items": limpio, "cuantos": len(limpio),
            "archivo": str(_ruta("compras")), **({"motivo": r.get("motivo")} if not r["ok"] else {})}


def _dividir(texto: str) -> list:
    partes = re.split(r",| y |\+|;|\n", texto or "")
    return [p.strip() for p in partes if p.strip() and len(p.strip()) <= 80]


def comprar(texto: str) -> dict:
    nuevos = _dividir(texto)
    if not nuevos:
        return {"ok": False, "motivo": "no viene ningún artículo en la frase"}
    actual = compras()
    anadidos = [n for n in nuevos if sin_acentos(n) not in {sin_acentos(x) for x in actual}]
    r = fijar_compras(actual + anadidos)
    r["anadidos"] = anadidos
    r["repetidos"] = [n for n in nuevos if n not in anadidos]
    r["nota"] = (f"{len(anadidos)} artículo(s) nuevo(s)" +
                 (f", {len(r['repetidos'])} ya estaban" if r["repetidos"] else ""))
    return r


def _dice(item: str, busca: str) -> bool:
    """«huevos» saca de la lista a «3 huevos»: la palabra tiene que estar suelta,
    no en mitad de otra (pan no borra panadería)."""
    return bool(re.search(r"(?:^|\W)%s(?:$|\W)" % re.escape(busca), sin_acentos(item), flags=re.I))


def quitar_compra(texto: str) -> dict:
    malos = _dividir(texto)
    if not malos:
        return {"ok": False, "motivo": "no dice qué quitar"}
    actual, fuera, quedan = compras(), [], []
    for i in actual:
        (fuera if any(_dice(i, m) for m in malos) else quedan).append(i)
    if not fuera:
        return {"ok": False, "motivo": "nada de la lista coincide con eso", "lista": actual}
    r = fijar_compras(quedan)
    r["quitados"] = fuera
    r["nota"] = f"Quitado de la lista: {', '.join(fuera)}"
    return r


def vaciar_compras() -> dict:
    r = fijar_compras([])
    r["nota"] = "lista vaciada"
    return r


# ------------------------------------------------------------------ notas ----
def notas() -> list:
    """La lista que pinta el panel: título, un trozo y la hora de escribir."""
    d = _leer("notas", {})
    salida = []
    for titulo, n in d.items():
        cuerpo = (n.get("content") or "").strip()
        salida.append({"titulo": titulo, "note": cuerpo[:160], "title": titulo,
                       "chars": len(cuerpo), "hora": n.get("hora", "")})
    salida.sort(key=lambda x: x.get("hora") or "", reverse=True)
    return salida


def guardar_nota(titulo: str, texto: str) -> dict:
    titulo = (titulo or "").strip()[:80]
    if not titulo:
        return {"ok": False, "motivo": "la nota necesita un título"}
    d = _leer("notas", {})
    d[titulo] = {"content": (texto or "").strip()[:200000],
                 "hora": datetime.now().isoformat(timespec="seconds")}
    r = _escribir("notas", d)
    r["titulo"] = titulo
    r["caracteres"] = len(d[titulo]["content"])
    r["nota"] = (f"Nota guardada: «{titulo}» ({r['caracteres']} caracteres)."
                 if r["ok"] else r.get("motivo", "no se pudo guardar"))
    return r


def leer_nota(titulo: str) -> dict:
    d = _leer("notas", {})
    t = (titulo or "").strip()
    if t in d:
        return {"ok": True, "titulo": t, "content": d[t]["content"], "hora": d[t].get("hora", "")}
    bajo = {sin_acentos(k): k for k in d}
    if sin_acentos(t) in bajo:
        k = bajo[sin_acentos(t)]
        return {"ok": True, "titulo": k, "content": d[k]["content"], "hora": d[k].get("hora", "")}
    return {"ok": False, "motivo": f"no hay una nota llamada «{t}» (hay {len(d)})",
            "títulos": list(d)}


def borrar_nota(titulo: str) -> dict:
    r = leer_nota(titulo)
    if not r["ok"]:
        return r
    d = _leer("notas", {})
    d.pop(r["titulo"], None)
    w = _escribir("notas", d)
    w["titulo"] = r["titulo"]
    w["nota"] = f"Nota borrada: {r['titulo']}." if w["ok"] else w.get("motivo", "")
    return w


# ----------------------------------------------------- tiempo en español ----
UNIDADES = {"segundo": 1, "segundos": 1, "minuto": 60, "minutos": 60,
            "hora": 3600, "horas": 3600, "día": 86400, "dia": 86400,
            "días": 86400, "dias": 86400, "semana": 604800, "semanas": 604800}


def segundos_en(texto: str) -> int | None:
    """«en 10 minutos», «hora y media», «a las 18:30», «mañana a las 7» -> segundos."""
    t = sin_acentos(texto or "")
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(segundos?|minutos?|horas?|dias?|días?|semanas?)", t)
    if m:
        n = float(m.group(1).replace(",", "."))
        return max(1, int(round(n * UNIDADES[m.group(2)])))
    if re.search(r"media hora|hora y media", t):
        return 1800
    m = re.search(r"a\s+la[s]?\s+(\d{1,2})(?:[:h](\d{2}))?\s*(de la mañana|de la tarde|de la noche|am|pm)?", t)
    if m:
        ahora = datetime.now()
        h = int(m.group(1))
        if re.search(r"de la tarde|de la noche|pm", m.group(3) or "") and h < 12:
            h += 12
        d = datetime.combine(ahora.date(), datetime.min.time()).replace(
            hour=min(h, 23), minute=int(m.group(2) or 0))
        if "manana" in t:
            d += timedelta(days=1)
        if d <= ahora:
            d += timedelta(days=1)
        return max(1, int((d - ahora).total_seconds()))
    return None


def _leir_recordatorios() -> list:
    d = _leer("recordatorios", {})
    if isinstance(d, list):
        return d
    return d.get("items", [])


def recordatorios(pendientes: bool = False) -> list:
    d = _leir_recordatorios()
    if pendientes:
        ahora = time.time()
        return [r for r in d if r.get("vencido") is False and r.get("para", 0) > ahora]
    return d


def poner_recordatorio(texto: str, cuando: str = "", tipo: str = "recordatorio") -> dict:
    texto = (texto or "").strip()[:200]
    if not texto:
        return {"ok": False, "motivo": "no dice qué hay que recordar"}
    seg = segundos_en(cuando) or segundos_en(texto)
    if not seg:
        return {"ok": False, "motivo": f"no sé cuándo es «{cuando or texto}»",
                "hace_falta": "una duración («10 minutos», «1 hora») o una hora («a las 18:30»)",
                "lista": recordatorios()}
    d = _leir_recordatorios()
    item = {"id": (max([int(r["id"]) for r in d], default=0) + 1), "texto": texto,
            "tipo": tipo, "segundos": seg, "para": round(time.time() + seg, 1),
            "en": datetime.fromtimestamp(time.time() + seg).isoformat(timespec="seconds"),
            "vencido": False}
    d.append(item)
    r = _escribir("recordatorios", {"items": d})
    if not r["ok"]:
        return {"ok": False, "motivo": r["motivo"]}
    relido = [x for x in _leir_recordatorios() if x["id"] == item["id"]]
    if not relido:
        return {"ok": False, "motivo": "escrito pero no relido; no lo doy por guardado"}
    avivar()
    return {"ok": True, "item": item, "cuantos": len(d),
            "nota": f"{'temporizador' if tipo == 'temporizador' else 'recordatorio'} "
                    f"para dentro de {seg} s"}


def borrar_recordatorio(id_o_texto) -> dict:
    d = _leir_recordatorios()
    clave = str(id_o_texto or "").strip()
    fuera, quedan = [], d
    if clave.isdigit():
        fuera = [r for r in d if str(r["id"]) == clave]
        quedan = [r for r in d if str(r["id"]) != clave]
    else:
        bajo = sin_acentos(clave)
        fuera = [r for r in d if bajo and bajo in sin_acentos(r["texto"])]
        quedan = [r for r in d if r not in fuera]
    if not fuera:
        return {"ok": False, "motivo": f"no encuentro el pendiente «{clave}»",
                "pendientes": [r["texto"] for r in recordatorios(pendientes=True)]}
    _escribir("recordatorios", {"items": quedan})
    return {"ok": True, "borrados": fuera, "cuantos_quedan": len(quedan)}


def vencer() -> list:
    """Los que llegaron a su hora: los marca y los devuelve (el puente los avisa)."""
    ahora = time.time()
    d = _leir_recordatorios()
    tocados = []
    for r in d:
        if r.get("vencido") is False and r.get("para", 0) <= ahora:
            r["vencido"] = True
            tocados.append(r)
    if tocados:
        _escribir("recordatorios", {"items": d})
    return tocados


def proximo_pendiente():
    for r in sorted(recordatorios(pendientes=True), key=lambda x: x.get("para", 0)):
        return {"id": r["id"], "texto": r["texto"], "faltan_seg": max(0, round(r["para"] - time.time())),
                "para": r.get("en", ""), "tipo": r.get("tipo", "recordatorio")}
    return None


# ----------------------------------------------------------------- la vela ----
def al_vencer(al_ganar):
    _AL_VENCER.append(al_ganar)


def _bucle_vela():
    global PROXIMO_VENCIMIENTO
    while True:
        try:
            tocados = vencer()
            PROXIMO_VENCIMIENTO = proximo_pendiente()
            for r in tocados:
                for fn in list(_AL_VENCER):
                    try:
                        fn(r)
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(1)


def avivar():
    """La vela del fondo: un hilo, un segundo de grano, sin procesito aparte."""
    global _VELA
    if _VELA and _VELA.is_alive():
        return
    _VELA = threading.Thread(target=_bucle_vela, daemon=True, name="cort-vela")
    _VELA.start()


# ------------------------------------------------------------------ estado ----
def disponibilidad() -> dict:
    return {"carpeta": str(VIDA), "existe": VIDA.exists(),
            "compras": len(compras()),
            "notas": len(_leer("notas", {})),
            "pendientes": len(recordatorios(pendientes=True)),
            "vencidos": sum(1 for r in recordatorios() if r.get("vencido")),
            "proximo": proximo_pendiente(), "vela": bool(_VELA and _VELA.is_alive())}


def resumen_hablado() -> str:
    c, n, p = compras(), notas(), recordatorios(pendientes=True)
    trozos = []
    trozos.append(f"La lista de compras tiene {len(c)} artículo(s)" +
                  (": " + ", ".join(c[:6]) + ("…" if len(c) > 6 else "") if c else "") + ".")
    trozos.append(f"{len(n)} nota(s) guardadas" + (f": {', '.join(x['titulo'] for x in n[:4])}." if n else "."))
    if p:
        mas = min(p, key=lambda r: r["para"])
        trozos.append(f"{len(p)} pendiente(s); el más cerca es «{mas['texto']}» en "
                      f"{max(0, round((mas['para'] - time.time()) / 60))} minuto(s).")
    else:
        trozos.append("No hay pendientes.")
    return " ".join(trozos)


# --------------------------------------------------------------------- CLI ----
def main(argv):
    orden = argv[1] if len(argv) > 1 else "estado"
    if orden == "estado":
        print(json.dumps(disponibilidad(), indent=2, ensure_ascii=False))
    elif orden == "compras":
        print(json.dumps(compras(), indent=2, ensure_ascii=False))
    elif orden == "compra":
        print(json.dumps(comprar(" ".join(argv[2:])), indent=2, ensure_ascii=False))
    elif orden == "quita":
        print(json.dumps(quitar_compra(" ".join(argv[2:])), indent=2, ensure_ascii=False))
    elif orden == "nota":
        print(json.dumps(guardar_nota(argv[2] if len(argv) > 2 else "sin título",
                                      " ".join(argv[3:]) if len(argv) > 3 else ""),
                         indent=2, ensure_ascii=False))
    elif orden == "notas":
        print(json.dumps(notas(), indent=2, ensure_ascii=False))
    elif orden == "recordatorio":
        print(json.dumps(poner_recordatorio(argv[2] if len(argv) > 2 else "",
                                           argv[3] if len(argv) > 3 else ""),
                         indent=2, ensure_ascii=False))
    elif orden == "temporizador":
        print(json.dumps(poner_recordatorio(f"temporizador de {argv[2]} segundos",
                                            cuando=f"{argv[2]} segundos", tipo="temporizador"),
                         indent=2, ensure_ascii=False))
    elif orden == "pendientes":
        print(json.dumps(recordatorios(pendientes=True), indent=2, ensure_ascii=False))
    elif orden == "resumen":
        print(resumen_hablado())
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
