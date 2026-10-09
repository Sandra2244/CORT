"""La puerta de la red: qué puede entrar en CORT desde fuera de su propia máquina.

El core no tiene usuarios ni sesión, y durante todo el prototipo eso ha sido
suficiente: escucha en `127.0.0.1`, y quien llega a ese puerto ya tiene una
cuenta abierta en el equipo. Publicarlo en la Wi-Fi (`--lan`) quita la premisa,
y deja una sola pregunta sin responder: **¿quién abrió este lazo?** Aquí la
responde un token compartido que la propia persona escribe en su `.env`.

Tres reglas cierran el diseño:

1. **Sin token no hay red.** Arrancar con `CORT_HOST` fuera de `127.0.0.1` y
   `CORT_LAN_TOKEN` vacío se niega antes de levantar el servidor, con el motivo
   escrito. Un puerto abierto sin contraseña es el control del PC a merced de
   todo el Wi-Fi, y eso no se decide por olvido de una variable.
2. **En local no se pide token.** El criterio es **la dirección en la que se
   pidió escuchar** (`CORT_HOST`), no la del vecino: mientras el core esté
   atado a `127.0.0.1` no hay nadie a quien autorizar. Cuando está publicado,
   el vecino de bucle invertido sigue entrando sin llave —es la dueña del
   portátil, y exigirle un token sería un paso de más para llegar a sí misma—.
3. **La comparación es de tiempo constante** (`hmac.compare_digest`). Un `==`
   sobre un secreto sale al primer carácter distinto, y ese tiempo se puede
   medir desde la red.

No hay lista de direcciones permitidas a propósito: una casa con DHCP cambiante
no puede escribirla, y un `X-Forwarded-For` se inventa. Y el arranque soportado
es `scripts/cort.py`, que es quien pone `CORT_HOST`: quien lance `uvicorn` a
mano con `--host 0.0.0.0` sin tocar el entorno se salta este criterio, y lo hace
sabiéndolo porque el lanzador se lo dijo.

Tampoco es un candado de verdad: sin TLS el token viaja en claro por la Wi-Fi,
así que protege de quien pasa por ahí, no de quien escucha el aire. Eso está
escrito en `docs/ARCHITECTURE.md` y en el aviso que pinta el lanzador, no
escondido detrás de un escudo verde.
"""
from __future__ import annotations

import hmac
import ipaddress
import os

__all__ = ["es_local", "host_de_escucha", "token_configurado",
           "rechazo_de_arranque", "autorizado"]

#: El nombre que significa «esta misma máquina».
_LOCALES = {"localhost"}


def es_local(direccion: str | None) -> bool:
    """True si la dirección es el propio equipo: `127.0.0.0/8`, `::1` o `localhost`.

    Se compara como red, no como cadena: `127.0.0.53` es tan local como
    `127.0.0.1`. Y lo que no se puede parsear **no** es local —fallar hacia el
    lado cerrado es lo que hace que un valor raro escrito en el `.env` no abra
    la puerta en vez de cerrarla—.
    """
    if not direccion:
        return False
    texto = direccion.strip()
    if texto.lower() in _LOCALES:
        return True
    # `::ffff:127.0.0.1` es lo que devuelve una pila dual en algunos sistemas.
    if texto.startswith("::ffff:") and es_local(texto[len("::ffff:"):]):
        return True
    try:
        return ipaddress.ip_address(texto).is_loopback
    except ValueError:
        return False


def host_de_escucha() -> str:
    """Dónde se pidió escuchar. El mismo valor que lee `server.py` para arrancar."""
    return os.getenv("CORT_HOST", "127.0.0.1").strip()


def token_configurado() -> str:
    """El secreto de la red, o cadena vacía si no se puso.

    Se recorta: un `CORT_LAN_TOKEN= ` (un espacio al final, escrito sin querer
    en el `.env`) daría la sensación de estar protegido y la comparación sería
    contra `" "`.
    """
    return os.getenv("CORT_LAN_TOKEN", "").strip()


def rechazo_de_arranque(host: str, token: str) -> str | None:
    """El motivo por el que **no** hay que arrancar, o `None` si se puede."""
    if es_local(host) or token:
        return None
    return (f"CORT_HOST={host or '(vacío)'} saca el core de esta máquina y no hay "
            "CORT_LAN_TOKEN puesto. No se abre un puerto sin contraseña: escribe un "
            "secreto en el .env (CORT_LAN_TOKEN=algo-largo) o quita --lan.")


def autorizado(host: str | None, peer: str | None, token: str,
               recibido: str | None) -> bool:
    """Si este lazo puede abrirse.

    Cuatro casos, y el orden importa:

    - `host` local → **dentro** sin preguntar. No hay a quién temerle en
      `127.0.0.1`.
    - `host` publicado y `peer` de bucle invertido → **dentro**: el portátil
      puede estar en `--lan` para el teléfono y seguir abriéndose a sí mismo
      desde `127.0.0.1` sin escribir nada.
    - `host` publicado, vecino de la red y token correcto → **dentro**.
    - `host` publicado, vecino de la red y **sin** token puesto → **fuera**.
      Este caso no debería existir (`rechazo_de_arranque` lo corta al arrancar),
      pero si aparece, la respuesta es no: un `True` por defecto sería justo la
      puerta abierta que este módulo viene a cerrar.
    """
    if es_local(host):
        return True
    if es_local(peer):
        return True
    if not token:
        return False
    return hmac.compare_digest(token, (recibido or "").strip())
