"""Clima real para el atuendo y el HUD (funciones 9 y 52).

Hasta hoy `state()` leía una temperatura fija de `CORT_CITY_TEMP_C` (22 °C) y el
HUD presumía de dar el clima sin darlo. Este módulo lo sustituye por un hecho
medido, con dos decisiones escritas antes que el código:

1. **Apagado por defecto.** Sin `CORT_CITY` no sale **ni una petición** de esta
   máquina. El core era 100 % local y sigue siéndolo hasta que alguien escriba
   una ciudad; además el nombre de la ciudad se envía a un tercero (Open-Meteo),
   así que es información que se comparte y se comparte a propósito.
2. **Nunca bloquea ni revienta.** `state()` se llama dentro del bucle del
   WebSocket: una petición HTTP síncrona ahí parararía a todos los clientes
   mientras el servicio tarda. Por eso `refresh()` es `async` y corre en una
   tarea de fondo, y lo que `state()` lee es la **última foto en caché**. Si el
   servicio cae, la foto vieja se queda y CORT sigue funcionando.

Fuente: Open-Meteo (https://open-meteo.com), sin clave y con uso gratuito. Se
elige por eso: `brain.py` ya habla por HTTP con `httpx`, y no hay ninguna
credencial que subir ni meter en un `.env`.
"""
from __future__ import annotations

import asyncio
import os
import time

import httpx

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

TIMEOUT_S = float(os.getenv("CORT_WEATHER_TIMEOUT_S", "6"))
# Cada cuánto se vuelve a pedir. Por debajo de 10 minutos sería molestar a un
# servicio gratuito por un número que cambia lento.
TTL_S = float(os.getenv("CORT_WEATHER_TTL_S", "900"))

_cache: dict = {"data": None, "fetched_at": 0.0, "error": None}
_coords: dict[str, tuple[float, float]] = {}


def city() -> str | None:
    """La ciudad configurada, o None. Sin ciudad no hay clima ni peticiones."""
    return (os.getenv("CORT_CITY") or "").strip() or None


def enabled() -> bool:
    return city() is not None


def snapshot() -> dict | None:
    """La última foto válida, o None si nunca hubo una o se pasó de vieja.

    No hace ninguna petición: es lo que puede llamar `state()` sin congelar el
    bucle del WebSocket.
    """
    data = _cache["data"]
    if data is None:
        return None
    if time.monotonic() - _cache["fetched_at"] > TTL_S * 3:
        # Tres TTL: un fallo pasajero del servicio no borra el clima del HUD,
        # pero un dato de hace horas ya no es un hecho, es una anécdota.
        return None
    return data


def last_error() -> str | None:
    return _cache["error"]


def _reset() -> None:
    """Deja la caché vacía. Para las pruebas, no para el arranque."""
    _cache.update({"data": None, "fetched_at": 0.0, "error": None})
    _coords.clear()


async def _geocode(name: str, client: httpx.AsyncClient) -> tuple[float, float] | None:
    if name in _coords:
        return _coords[name]
    res = await client.get(GEOCODE_URL, params={"name": name, "count": 1, "language": "es"})
    res.raise_for_status()
    results = res.json().get("results") or []
    if not results:
        return None
    first = results[0]
    pair = (float(first["latitude"]), float(first["longitude"]))
    _coords[name] = pair
    return pair


async def refresh(client: httpx.AsyncClient | None = None) -> dict | None:
    """Pide clima nuevo y lo deja en caché. Nunca lanza: guarda el motivo en `error`."""
    name = city()
    if name is None:
        _cache["error"] = None
        return None
    own = client is None
    client = client or httpx.AsyncClient(timeout=TIMEOUT_S)
    try:
        coords = await _geocode(name, client)
        if coords is None:
            _cache["error"] = f"ciudad no encontrada: {name}"
            return None
        res = await client.get(FORECAST_URL, params={
            "latitude": coords[0], "longitude": coords[1],
            "current": "temperature_2m,weather_code,wind_speed_10m", "timezone": "auto"})
        res.raise_for_status()
        current = res.json().get("current") or {}
        temp = current.get("temperature_2m")
        if temp is None:
            _cache["error"] = "respuesta sin temperatura"
            return None
        data = {"city": name, "temp_c": float(temp),
                "code": current.get("weather_code"),
                "wind_kmh": current.get("wind_speed_10m")}
        _cache["data"] = data
        _cache["fetched_at"] = time.monotonic()
        _cache["error"] = None
        return data
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        # `httpx.HTTPError` cubre tiempo de espera, DNS y 4xx/5xx por raise_for_status.
        _cache["error"] = str(exc) or exc.__class__.__name__
        return snapshot()
    finally:
        if own:
            await client.aclose()


async def keep_updating() -> None:
    """Tarea de fondo: refresca cada TTL. Con la ciudad sin configurar no empieza."""
    if not enabled():
        return
    while True:
        await refresh()
        await asyncio.sleep(TTL_S)
