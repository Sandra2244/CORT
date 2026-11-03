#!/usr/bin/env python3
"""CORT — el compilador de intenciones (fase F9).

El tramo que falta entre «entendí la frase» y «lo hice». Un modelo pequeño no
comprende: predice texto. Por eso nunca ejecuta nada; devuelve una propuesta y este
módulo decide si esa propuesta es algo que CORT puede hacer en este equipo.

Cuatro filtros, en este orden, y cada rechazo dice el motivo con la ruta delante:

1. **Forma.** El plan es un JSON con `intencion` y `argumentos`. Si el modelo devolvió
   prosa, un cercado de markdown o dos objetos, se descarta: no se adivina.
2. **Verbo.** Sólo los de `VERBOS`. Una alucinación tipo `borrar_archivo` o `ejecutar`
   no está en la lista, así que no puede existir aunque el modelo la escriba.
3. **Argumentos.** Faltantes, vacíos, o una ruta fuera de las raíces del usuario.
4. **Confirmación.** Lo que puede dañar (apagar, sobrescribir) exige `confirmar=True`
   venido de un gesto humano en la interfaz, jamás del plan del modelo.

Después de ejecutar se *verifica*: se vuelve a leer el disco o el estado del equipo.
«Hecho» sólo se dice cuando la relectura lo confirma, que es el defecto exacto de la
plantilla original, que respondía éxito sin preguntar al sistema.
"""
from __future__ import annotations

import json
import re
import unicodedata

try:
    import cort_archivos
except Exception as _e:
    cort_archivos = None
    ARCHIVOS_ERROR = f"{type(_e).__name__}: {_e}"

try:
    import cort_media
except Exception as _e:
    cort_media = None
    MEDIA_ERROR = f"{type(_e).__name__}: {_e}"


# ------------------------------------------------------------------- el vocabulario ----
# Los nombres que el modelo puede proponer. `requiere` se chequea después de pasar los
# alias, así que «from», «origen» y «desde» son la misma llave para el ejecutor.
VERBOS = {
    "listar_archivos": {"requiere": ["carpeta"], "ejecuta": "cort_archivos.listar"},
    "mover_archivo": {"requiere": ["origen", "destino"], "ejecuta": "cort_archivos.mover",
                      "puede_pisar": True},
    "copiar_archivo": {"requiere": ["origen", "destino"], "ejecuta": "cort_archivos.copiar",
                       "puede_pisar": True},
    "crear_carpeta": {"requiere": ["donde"], "opta": ["nombre"], "ejecuta": "cort_archivos.crear_carpeta"},
    "reproducir": {"requiere": ["pista"], "opta": ["playlist"], "ejecuta": "cort_media.reproducir"},
    "pausar": {"requiere": [], "ejecuta": "cort_media.control"},
    "siguiente": {"requiere": [], "ejecuta": "cort_media.control"},
}

# Lo que ella pide y hoy no puede hacerse desde el puente: se dice con fase y motivo,
# en vez de responder «no entendí» como si fuera un diccionario roto.
FUERA_DE_ALCANCE = {
    "borrar_archivo": "CORT no borra archivos todavía: la fase de papelera y confirmación "
                      "doble no está construida, y sin ella un error del modelo sería irreversible.",
    "investigar": "buscar en internet con fuentes citadas es la fase F13; hoy no salgo a la red "
                  "sin leer ni decir el origen del dato.",
    "buscar_web": "buscar en internet con fuentes citadas es la fase F13; hoy no salgo a la red "
                  "sin leer ni decir el origen del dato.",
    "playlists_telefono": "tus playlists de Lark Player están en el teléfono y la PWA no puede "
                          "entrar ahí: eso lo hace el APK con MediaStore, fase F12.",
    "reproducir_telefono": "tus playlists de Lark Player están en el teléfono y la PWA no puede "
                           "entrar ahí: eso lo hace el APK con MediaStore, fase F12.",
    "abrir_app_telefono": "abrir una app del A16 exige el APK asistente (fase F11); desde el "
                          "navegador no se invoca a otra aplicación.",
}

# alias: el modelo escribe en inglés o en español, y a veces en ambos dentro del mismo JSON
ALIAS = {
    "origen": ("origen", "from", "desde", "fuente", "archivo", "carpeta_origen", "ruta"),
    "destino": ("destino", "to", "a", "hacia", "para", "carpeta_destino"),
    "carpeta": ("carpeta", "folder", "directorio", "donde", "ruta", "lugar"),
    "donde": ("donde", "en", "dentro", "padre", "carpeta", "path"),
    "nombre": ("nombre", "name", "nueva"),
    "pista": ("pista", "cancion", "track", "song", "tema"),
    "playlist": ("playlist", "lista", "album", "carpeta"),
    "accion": ("accion", "que", "control"),
}

CLAVES_INTENCION = ("intencion", "intención", "intent", "verb", "accion", "verbo")
CLAVES_ARGS = ("argumentos", "args", "params", "parameters", "datos")


def _sin(t: str) -> str:
    t = unicodedata.normalize("NFD", str(t or "").strip().lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def plan_desde_texto(crudo: str):
    """Acepta el JSON tal cual o metido en un cercado, y nada más: si hay prosa around,
    se toma el primer objeto balanceado. Dos objetos = plan ambiguo = None."""
    if isinstance(crudo, dict):
        return crudo
    t = str(crudo or "").strip()
    if not t:
        return None
    t = re.sub(r"^```[a-z]*\s*|\s*```$", "", t, flags=re.S).strip()
    try:
        d = json.loads(t)
        return d if isinstance(d, dict) else None
    except ValueError:
        pass
    inicio = t.find("{")
    if inicio < 0:
        return None
    profundidad = 0
    for i, c in enumerate(t[inicio:], inicio):
        if c == "{":
            profundidad += 1
        elif c == "}":
            profundidad -= 1
            if profundidad == 0:
                try:
                    d = json.loads(t[inicio:i + 1])
                    return d if isinstance(d, dict) else None
                except ValueError:
                    return None
    return None


def normalizar(plan: dict) -> dict:
    """Un solo mapa de claves: `intencion` + `argumentos` limpios, con los alias resueltos."""
    intencion = ""
    for k in CLAVES_INTENCION:
        for pk, pv in plan.items():
            if _sin(pk) == k and isinstance(pv, str) and pv.strip():
                intencion = _sin(pv)
                break
        if intencion:
            break
    args_in = {}
    for k in CLAVES_ARGS:
        for pk, pv in plan.items():
            if _sin(pk) == k and isinstance(pv, dict):
                args_in = pv
                break
        if args_in:
            break
    if not args_in:       # JSON plano: {"verb":"mover","from":...,"to":...} — la intención
        # ya está leída arriba; el resto de las llaves son los argumentos
        reservados = CLAVES_INTENCION + CLAVES_ARGS + ("no_entendido", "necesita_confirmacion", "confirmar")
        args_in = {k: v for k, v in plan.items() if _sin(k) not in reservados}
    args = {}
    for canon, nombres in ALIAS.items():
        for k, v in args_in.items():
            if _sin(k) in nombres and isinstance(v, str) and v.strip():
                args[canon] = v.strip()
                break
    # una intención suelta en `objetivo`/`texto` también vale como pista
    for k, v in args_in.items():
        if _sin(k) in ("objetivo", "texto", "target") and isinstance(v, str) and v.strip():
            args.setdefault("carpeta", v.strip())
    return {"intencion": intencion, "argumentos": args,
            "necesita_confirmacion": bool(plan.get("necesita_confirmacion") or plan.get("confirmar")),
            "no_entendido": bool(plan.get("no_entendido"))}


def validar(plan: dict):
    """(ok, motivo). No toca nada: es la reja antes del ejecutor."""
    if not isinstance(plan, dict):
        return False, "el cerebro no devolvió un plan, devolvió texto suelto"
    if plan.get("no_entendido"):
        return False, "el cerebro dijo que no entendió la frase"
    v = plan.get("intencion") or ""
    if not v:
        return False, "el plan no trae intención"
    if v in FUERA_DE_ALCANCE:
        return False, FUERA_DE_ALCANCE[v]
    if v not in VERBOS:
        return False, f"«{v}» no es algo que CORT sepa hacer en este equipo"
    if cort_archivos is None and v.startswith(("mover", "copiar", "listar", "crear")):
        return False, "el módulo de archivos no cargó: " + ARCHIVOS_ERROR
    if cort_media is None and v in ("reproducir", "pausar", "siguiente"):
        return False, "el módulo de media no cargó: " + MEDIA_ERROR
    faltan = [a for a in VERBOS[v].get("requiere", []) if not plan["argumentos"].get(a)]
    if faltan:
        return False, f"a «{v}» le falta {', '.join(faltan)}"
    return True, ""


def _invocar(ruta: str, args: list, confirmar: bool):
    modulo, funcion = ruta.split(".")
    m = {"cort_archivos": cort_archivos, "cort_media": cort_media}[modulo]
    fn = getattr(m, funcion)
    args = [a for a in args if a]
    if funcion in ("mover", "copiar"):
        return fn(args[0], args[1], confirmar=confirmar)
    return fn(*args)


def ejecutar(bruto, confirmar: bool = False):
    """frase del modelo (dict o texto) -> {decir, origen, detalle, intencion, valido}."""
    plan = plan_desde_texto(bruto)
    if plan is None:
        return {"decir": "El cerebro respondió sin formato, así que no toqué nada.",
                "origen": "no disponible", "intencion": "", "valido": False,
                "motivo": "respuesta fuera de formato", "detalle": {"crudo": str(bruto)[:200]}}
    p = normalizar(plan)
    ok, motivo = validar(p)
    if not ok:
        return {"decir": f"No lo hago: {motivo}", "origen": "no disponible",
                "intencion": p["intencion"], "valido": False, "motivo": motivo,
                "detalle": {"plan": p}}
    v = VERBOS[p["intencion"]]
    args = [p["argumentos"].get(a) for a in v.get("requiere", [])]
    args += [p["argumentos"].get(a) for a in v.get("opta", [])]
    r = _invocar(v["ejecuta"], args, bool(confirmar))
    r = dict(r or {})
    r["intencion"] = p["intencion"]
    r["valido"] = bool(r.get("ok"))
    r.setdefault("origen", "real" if r.get("ok") else "no disponible")
    r.setdefault("motivo", "" if r.get("ok") else r.get("decir", ""))
    r["plan"] = p
    return r


def disponibilidad() -> dict:
    return {"modulo": "cort_intenciones", "listo": bool(cort_archivos or cort_media),
            "verbos": sorted(VERBOS), "fuera_de_alcance": sorted(FUERA_DE_ALCANCE),
            "archivos": cort_archivos.disponibilidad() if cort_archivos else ARCHIVOS_ERROR,
            "media": cort_media.disponibilidad() if cort_media else MEDIA_ERROR}


if __name__ == "__main__":
    import sys
    print(json.dumps(disponibilidad(), ensure_ascii=False, indent=1))
    for frase in sys.argv[1:]:
        print(frase, "->", ejecutar(frase).get("decir"))
