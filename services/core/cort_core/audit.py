"""La bitácora de lo que CORT **no** dejó hacer: quién lo intentó y desde dónde.

`security.py` decide si un lazo se abre; este módulo apunta los que se cerraron.
Hasta hoy el core rechazaba en silencio, y eso dejaba la pregunta sin respuesta
para la dueña del portátil: *«¿alguien estuvo probando?»*. Un portero que no
lleva registro no puede decir nada al día siguiente.

Cuatro reglas, y las cuatro vienen de un riesgo concreto:

1. **El secreto nunca se escribe.** El detalle lo alimenta input de la otra
   parte (el nombre de un archivo, un query). Si alguien mete el token en un
   nombre, en el disco queda la señal `«llave»`, no el token. Y si el valor no
   venía del aire sino de una comparación, ni se mira: aquí no se guarda nunca
   lo que llegó en `?token=`.
2. **Una línea por evento, y sólo JSON.** El ataque clásico a un log es un
   `\\n` en medio del texto: quien lo logra se fabrica una línea limpia en mitad
   de un registro sucio. Todo carácter de control se convierte en espacio antes
   de serializar, y el texto se recorta.
3. **Motivos de una lista cerrada.** Seis cosas pueden quedar apuntadas, y ni
   una más. Un registro donde quien escribe puede inventar categorías es un
   registro que no se puede leer.
4. **Registrar no puede tumbar nada.** Si el disco está lleno, la bitácora
   devuelve `False` y el servidor sigue cerrando puertas igual. Un fallo
   *escribiendo* jamás puede abrir una.

El archivo vive en `services/core/data/`, que está en `.gitignore`: una lista de
direcciones y nombres intentados es dato de la casa de la usuaria, no material
de un repositorio público. Y **no cifra nada**: quien pueda leer su disco puede
leerla, igual que puede leer su `memory.db`. Lo que protege es la puerta, no la
bitácora.

No es un antivirus. Un registro de rechazos no detiene malware; es la primera
capa de lo que ella pidió como «base y proyección contra malware»: saber que
algo intentó entrar, y por cuál de las puertas.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import security

__all__ = ["MOTIVOS", "DETALLE_MAX", "LIMITE_BYTES", "ruta_de_bitacora",
           "normaliza", "linea", "registrar", "recientes"]

#: Los seis rechazos que existen. Coinciden con los que `server.py` puede
#: producir; si un módulo nuevo quiere otro, primero entra aquí.
MOTIVOS = (
    "acceso-sin-llave",        # pidió la red y no traía `?token=`
    "llave-incorrecta",        # traía una y no era la del .env
    "ruta-rechazada",          # un nombre con forma de evasión (`..`, `/`, `%00`)
    "extension-no-permitida",  # pidió un archivo que CORT no sirve (.txt, .py…)
    "archivo-fuera-de-la-carpeta",  # resolvió fuera de `CORT_AVATAR_DIR`
    "arranque-sin-llave",      # alguien intentó publicar el core sin secreto
)

#: Cuánto texto del otro lado cabe en una línea. Suficiente para un nombre de
#: archivo; bastante menos que un payload.
DETALLE_MAX = 120

#: La bitácora se recorta al pasarse de esto. No es un límite de estética: sin
#: él, un vecino terco que insista mil veces por segundo escribe mil líneas y
#: llena el disco de esta máquina, que ya bastante tiene con 1,8 GiB.
LIMITE_BYTES = 64_000

#: Al lado de `memory.db`, en la carpeta que ignora `.gitignore`. `audit.py` vive
#: un nivel más arriba que `memory/store.py`, así que el `parents` no es igual.
_DEFAULT = Path(__file__).resolve().parents[1] / "data" / "rechazos.jsonl"

# Todo lo que no sea imprimible, incluido el salto de línea y el tabulador.
_CONTROLES = "".join(chr(c) for c in range(32)) + "\x7f"


def ruta_de_bitacora() -> Path:
    """Dónde se escribe. `CORT_AUDIT_LOG` permite apuntar a otro sitio en las
    pruebas sin tocar el registro real de nadie."""
    bruto = os.getenv("CORT_AUDIT_LOG", "").strip()
    return Path(bruto).expanduser() if bruto else _DEFAULT


def normaliza(detalle: object) -> str:
    """El texto que llega del otro lado, convertido en algo que no puede falsear
    una línea ni contener el secreto."""
    texto = detalle if isinstance(detalle, str) else ("" if detalle is None else str(detalle))
    for ch in _CONTROLES:
        texto = texto.replace(ch, " ")
    texto = " ".join(texto.split())[:DETALLE_MAX]
    # El secreto configurado, si aparece escrito dentro, se sustituye. Se lee en
    # cada llamada y no al importar: las pruebas lo ponen y lo quitan, y un valor
    # congelado al importar sería un coladero con forma de caché.
    secreto = security.token_configurado()
    if secreto and secreto in texto:
        texto = texto.replace(secreto, "«llave»")[:DETALLE_MAX]
    return texto


def linea(motivo: str, origen: object, detalle: object,
          cuando: datetime | None = None) -> str:
    """La forma de un evento: una línea JSON con hora, motivo, quién y qué.

    `cuando` es un argumento y no una llamada a `now()` dentro, para que las
    pruebas puedan comprobar el texto exacto.
    """
    return json.dumps({
        "iso": (cuando or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "motivo": motivo,
        "origen": normaliza(origen)[:45],
        "detalle": normaliza(detalle),
    }, ensure_ascii=False) + "\n"


def registrar(motivo: str, origen: object = "", detalle: object = "") -> bool:
    """Apunta un rechazo. Devuelve `True` sólo si quedó escrito.

    Un motivo fuera de la lista se rechaza **sin escribir**, y cualquier fallo de
    disco se traga y devuelve `False`: quien llama es el servidor cerrando una
    puerta, y ese trabajo no se puede interrumpir por culpa del registro.
    """
    if motivo not in MOTIVOS:
        return False
    ruta = ruta_de_bitacora()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("a", encoding="utf-8") as f:
            f.write(linea(motivo, origen, detalle))
        if ruta.stat().st_size > LIMITE_BYTES:
            _recortar(ruta)
    except OSError:
        return False
    return True


def _recortar(ruta: Path) -> None:
    """Se queda con la cola, que es lo más nuevo, y la escribe entera.

    Primero se corta por *bytes* y luego se reordena por líneas: quedarse con los
    primeros N bytes partiría una línea por la mitad, y la bitácora dejaría de
    poder leerse.
    """
    crudos = ruta.read_text(encoding="utf-8", errors="replace").splitlines()
    guardadas: list[str] = []
    total = 0
    for bruto in reversed(crudos):
        peso = len(bruto.encode("utf-8")) + 1
        if guardadas and total + peso > LIMITE_BYTES:
            break
        guardadas.append(bruto)
        total += peso
    ruta.write_text("".join(b + "\n" for b in reversed(guardadas)), encoding="utf-8")


def recientes(maximo: int = 20) -> list[dict]:
    """Los últimos intentos, **del más nuevo al más viejo**.

    Lee y tira lo que no sea JSON válido: un archivo tocado a mano, una línea a
    medias escritas por un corte de luz. La lectura de la bitácora nunca puede
    ser la causa de que CORT no arranque.
    """
    ruta = ruta_de_bitacora()
    if not ruta.is_file():
        return []
    cuadros: list[dict] = []
    try:
        crudos = ruta.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for bruto in reversed(crudos):
        if len(cuadros) >= maximo:
            break
        try:
            cuadro = json.loads(bruto)
        except ValueError:
            continue
        if isinstance(cuadro, dict) and cuadro.get("motivo") in MOTIVOS:
            cuadros.append(cuadro)
    return cuadros


def resumen(cuadros: list[dict], ruta: Path) -> str:
    """Lo que pinta `python -m cort_core.audit` en la terminal."""
    if not cuadros:
        return f"Bitácora de rechazos: sin rechazos registrados en {ruta}."
    lineas = [f"Bitácora de rechazos: {len(cuadros)} intentos apuntados en {ruta}"]
    for c in cuadros:
        lineas.append(f"  {c.get('iso', '?')}  {c.get('motivo', '?'):<28}"
                      f"  {c.get('origen') or '—':<22}  {c.get('detalle') or ''}")
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    import sys

    from .env import load_env

    # El `.env` se lee aquí y no al importar: este módulo también lo usa el
    # servidor, y un lector de terminal que ignora `CORT_AUDIT_LOG` buscaría el
    # registro en el sitio equivocado y diría «sin rechazos» delante de uno lleno.
    load_env()
    tope = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20
    destino = ruta_de_bitacora()
    print(resumen(recientes(tope), destino), end="")
