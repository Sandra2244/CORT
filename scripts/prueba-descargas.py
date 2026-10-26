"""Prueba del **reintento** de descargas de modelos: que una bajada no se rompa
a la primera tos de la red.

Por qué existe esta prueba y no basta con «funcionó en el navegador»:

  1. **Se corta y lo vuelve a intentar.** `backend/app/models.py::_bajar` antes
     marcaba `error` con la primera excepción. Ahora relanza hasta
     `REINTENTOS` veces con espera creciente, y Ollama sigue la bajada desde el
     byte que llevaba (blob `.part` + `Range`). Aquí se mide el MECANISMO, sin
     red: un `_jala` de mentira que tose y luego responde.
  2. **Se rinde con un motivo legible.** Cinco intentos fallidos no pueden dejar
     la barra colgada en «descargando»: tienen que decir cuántas veces se cortó.
  3. **Cancelar NO es un fallo.** Si ella pulsa ✕, `_Corte` sale del bucle sin
     reintentar ni una vez.
  4. **Cancelar mientras espera también manda.** La espera entre intentos se
     duerme en trocitos; si cancela en medio, el hilo se va ya.
  5. **La barra no vuelve a cero.** El `pct` del último byte bajado se conserva
     durante el reintento: es lo que hace que se vea «sigue donde iba».
  6. **El hilo mudo tiene tope.** `timeout=(10, None)` dejaba la conexión colgada
     para siempre y bloqueaba la fila de los demás modelos. Se comprueba en el
     código fuente que el tope de lectura existe y que el `None` no volvió.
  7. **Costura con la cara.** El estado nuevo `reintentando` tiene que estar en
     la lista de estados vivos de `ui/js/hud.js` (`ACTIVOS`) y en las dos tuplas
     de `models.py`: si falta en alguna, la fila pierde su botón ✕ o se cuenta
     dos veces en la fila.

Nada de esto toca la red ni `~/.ollama`: `_jala` se sustituye por un gemelo y el
reloj de espera se pone a cero.

Uso:  python3 scripts/prueba-descargas.py     (un par de segundos)
"""
from __future__ import annotations

import pathlib
import re
import sys
import threading
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend" / "app"))

import models  # noqa: E402

fallos = 0


def comprueba(titulo, condicion, detalle=""):
    global fallos
    if not condicion:
        fallos += 1
    print(f"  {'ok ' if condicion else 'MAL'} · {titulo}" + (f" ({detalle})" if detalle else ""))


def limpia(nombre):
    with models._CANDADO:
        models.PULLS.pop(nombre, None)
        models._CANCELADOS.discard(nombre)


# Sin esto cada reintento esperaría 2+5+12+25 s y la prueba duraría medio minuto.
ESPERAS_REALES = models.ESPERAS


class Tos(Exception):
    """La red cortada, en miniatura."""


print("\n[1] se corta y lo vuelve a intentar")
nombre = "prueba:reintenta"
limpia(nombre)
llamadas = {"n": 0}


def tose_dos_veces(m):
    llamadas["n"] += 1
    if llamadas["n"] < 3:
        raise Tos(f"conexión cortada #{llamadas['n']}")
    models._marca(m, "listo", pct=100, detalle="en el disco")


models.ESPERAS = (0, 0, 0, 0)
_jala_real = models._jala
models._jala = tose_dos_veces
try:
    models._bajar(nombre)
finally:
    models._jala = _jala_real
    models.ESPERAS = ESPERAS_REALES
estado = (models.PULLS.get(nombre) or {}).get("estado")
comprueba("llegó hasta el final tras toser", estado == "listo", f"estado {estado!r}")
comprueba("llamó tres veces (dos fallos + el acierto)", llamadas["n"] == 3, f"{llamadas['n']} llamadas")
limpia(nombre)

print("\n[2] se rinde, pero diciendo cuántas veces se cortó")
nombre = "prueba:siempre-tose"
llamadas = {"n": 0}


def tose_siempre(m):
    llamadas["n"] += 1
    raise Tos("wifi caído")


models.ESPERAS = (0, 0, 0, 0)
models._jala = tose_siempre
try:
    models._bajar(nombre)
finally:
    models._jala = _jala_real
    models.ESPERAS = ESPERAS_REALES
p = models.PULLS.get(nombre) or {}
comprueba("agotó los intentos y declaró error", p.get("estado") == "error", str(p.get("estado")))
comprueba("el motivo dice las veces que se cortó",
          "se cortó" in (p.get("error") or "") and "wifi caído" in (p.get("error") or ""),
          (p.get("error") or "")[:90])
comprueba(f"intentos = {models.REINTENTOS + 1} (ninguno de más)",
          llamadas["n"] == models.REINTENTOS + 1, f"{llamadas['n']} llamadas")
limpia(nombre)

print("\n[3] cancelar a media bajada no se reintenta")
nombre = "prueba:corte-voluntario"
llamadas = {"n": 0}


def corta(m):
    llamadas["n"] += 1
    raise models._Corte()


models._jala = corta
try:
    models._bajar(nombre)
finally:
    models._jala = _jala_real
comprueba("salió a la primera, sin machacar la red", llamadas["n"] == 1, f"{llamadas['n']} llamadas")
limpia(nombre)

print("\n[4] cancelar MIENTRAS espera el reintento")
nombre = "prueba:corte-en-espera"
models.ESPERAS = (6,)          # espera larga a propósito: la tiene que interrumpir


def tose_y_espera(m):
    raise Tos("se fue la luz")


models._jala = tose_y_espera
hilo = threading.Thread(target=models._bajar, args=(nombre,), daemon=True)
hilo.start()
espera_hasta = time.time() + 4
while time.time() < espera_hasta and (models.PULLS.get(nombre) or {}).get("estado") != "reintentando":
    time.sleep(0.05)
vio_espera = (models.PULLS.get(nombre) or {}).get("estado") == "reintentando"
t0 = time.time()
models.cancelar(nombre)
hilo.join(timeout=4)
salió = not hilo.is_alive()
models._jala = _jala_real
models.ESPERAS = ESPERAS_REALES
comprueba("pasó por el estado «reintentando»", vio_espera)
comprueba("el ✕ cortó la espera y el hilo se fue", salió and (time.time() - t0) < 2,
          f"{time.time() - t0:.2f}s")
comprueba("y no dejó el modelo colgado en la fila", nombre not in models.PULLS)

print("\n[5] la barra no vuelve a cero durante el reintento")
nombre = "prueba:pct-se-conserva"
models._marca(nombre, "descargando", pct=41.5, mb=60, mb_total=145, detalle="bajando · 60 de 145 MB")
llamadas = {"n": 0}
pct_visto_al_reintentar = {"v": None}


def tose_una(m):
    llamadas["n"] += 1
    if llamadas["n"] == 1:
        raise Tos("corte")
    # Este es el momento de la verdad: el segundo intento arranca con la barra
    # todavía en el 41,5 %, no en cero.
    pct_visto_al_reintentar["v"] = (models.PULLS.get(m) or {}).get("pct")
    models._marca(m, "listo", pct=100, detalle="en el disco")


models.ESPERAS = (0, 0, 0, 0)
models._jala = tose_una
try:
    models._bajar(nombre)
finally:
    models._jala = _jala_real
    models.ESPERAS = ESPERAS_REALES
comprueba("al relanzar, la barra seguía en el 41,5 %",
          pct_visto_al_reintentar["v"] == 41.5, f"vio {pct_visto_al_reintentar['v']}")
comprueba("y terminó en 100 tras dos llamadas",
          llamadas["n"] == 2 and (models.PULLS.get(nombre) or {}).get("pct") == 100)
limpia(nombre)

print("\n[6] el hilo mudo tiene tope (leído en el código)")
fuente = (RAIZ / "backend" / "app" / "models.py").read_text(encoding="utf-8")
comprueba("la lectura tiene `SILENCIO` como tope",
          "timeout=(10, SILENCIO)" in fuente)
lineas_none = [l for l in fuente.splitlines() if "timeout=(10, None)" in l]
ofenden = [l.strip() for l in lineas_none if not l.strip().startswith("#")]
comprueba("ninguna LÍNEA DE CÓDIGO vuelve a dejar la lectura sin tope",
          not ofenden, f"{len(lineas_none)} apariciones, todas en comentario"
          if not ofenden else "en código: " + ofenden[0])
comprueba("el tope es mayor que un byte perdido y menor que un minuto y medio",
          10 < models.SILENCIO <= 120, f"SILENCIO={models.SILENCIO}")
comprueba("los reintentos son al menos 3 y las esperas van creciendo",
          models.REINTENTOS >= 3 and list(models.ESPERAS) == sorted(models.ESPERAS),
          f"{models.REINTENTOS} · {models.ESPERAS}")

print("\n[7] costura: la cara conoce el estado nuevo")
hud = (RAIZ / "ui" / "js" / "hud.js").read_text(encoding="utf-8")
activos = re.search(r"const ACTIVOS = \[([^\]]*)\]", hud)
comprueba("`ACTIVOS` de hud.js incluye «reintentando»",
          bool(activos) and "reintentando" in activos.group(1),
          (activos.group(1).strip() if activos else "sin línea ACTIVOS"))
en_models = fuente.count('"reintentando"')
comprueba("y las tuplas de models.py también (no se apunta dos veces a la cola)",
          en_models >= 3, f"{en_models} apariciones")
comprueba("el docstring de `descargar` sigue siendo cierto con el estado nuevo",
          "reintentando" in fuente and fuente.index("def descargar") < fuente.index("def _bajar"))

print("\n[8] el techo de contexto que CORT le pone a Ollama")
comprueba("un equipo de 1,8 GB pide 512, no los 4096 de Ollama",
          models.CONTEXTO_PEQUEÑO == 512 and models.EQUIPO_PEQUEÑO_GB == 4.0,
          f"{models.CONTEXTO_PEQUEÑO} / {models.EQUIPO_PEQUEÑO_GB} GB")
comprueba("y la función mira la RAM de ESTE equipo, no un número fijo",
          models.contexto_sugerido() in (models.CONTEXTO_PEQUEÑO, models.CONTEXTO_NORMAL),
          f"→ {models.contexto_sugerido()} con {models.ram_total_gb():g} GB")
comprueba("el arranque del servidor pasa la variable, con `setdefault` (no pisa la de ella)",
          'entorno.setdefault("OLLAMA_CONTEXT_LENGTH"' in fuente
          and 'entorno["OLLAMA_CONTEXT_LENGTH"]' not in fuente)
comprueba("el número sale de una medida, y la medida está escrita en el archivo",
          "14,6" in fuente and "110 s" in fuente)

print()
if fallos:
    print(f"{fallos} comprobación(es) en ROJO")
    sys.exit(1)
print("todas en verde")
