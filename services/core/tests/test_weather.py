"""Pruebas del clima (`cort_core/weather.py`).

Nada de aquí sale a la red: el cliente va montado sobre `httpx.MockTransport`, el
mismo truco de `test_brain.py`. En una máquina de 1,8 GiB con un servicio externo
de por medio, una prueba que depende del clima de verdad es una prueba que falla
cuando llueve.
"""
import unittest
from unittest import mock

import httpx

from cort_core import weather

GEO_OK = {"results": [{"name": "Bogotá", "latitude": 4.6097, "longitude": -74.0817}]}
GEO_EMPTY = {"results": []}
FORECAST_OK = {"current": {"temperature_2m": 8.5, "weather_code": 3, "wind_speed_10m": 12.4}}


def transport(responses: dict[str, object], seen: list[str]) -> httpx.MockTransport:
    """Un transport de mentira que responde según el `host` pedido.

    La forma del json no importa aquí: lo que se está probando es que el módulo
    sepa **a dónde** ir y qué hacer cuando algo de eso falla.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host)
        body = responses.get(request.url.host)
        if body == "boom":
            return httpx.Response(500, json={})
        if isinstance(body, BaseException):
            raise body
        if body is None:
            return httpx.Response(404, json={})
        return httpx.Response(200, json=body)
    return httpx.MockTransport(handler)


class TestClima(unittest.TestCase):
    def setUp(self):
        weather._reset()
        self.seen: list[str] = []

    def async_call(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_sin_ciudad_no_sale_ni_una_peticion(self):
        # El corazón del asunto: el core era 100 % local. Un adorno del HUD no
        # puede abrir la máquina a un tercero sin que alguien lo pida.
        with mock.patch.dict(weather.os.environ, {}, clear=True):
            self.assertIsNone(weather.city())
            self.assertFalse(weather.enabled())
            client = httpx.AsyncClient(transport=transport({}, self.seen))
            self.async_call(weather.refresh(client))
            self.assertEqual(self.seen, [])
            self.assertIsNone(weather.snapshot())

    def test_con_ciudad_busca_y_luego_pide_el_forecast(self):
        with mock.patch.dict(weather.os.environ, {"CORT_CITY": "Bogotá"}):
            client = httpx.AsyncClient(transport=transport(
                {"geocoding-api.open-meteo.com": GEO_OK,
                 "api.open-meteo.com": FORECAST_OK}, self.seen))
            data = self.async_call(weather.refresh(client))
            self.assertEqual(data["city"], "Bogotá")
            self.assertEqual(data["temp_c"], 8.5)
            self.assertEqual(self.seen, ["geocoding-api.open-meteo.com", "api.open-meteo.com"])
            self.assertEqual(weather.snapshot()["temp_c"], 8.5)

    def test_la_ciudad_se_resuelve_una_sola_vez(self):
        # La segunda `refresh` no debe volver al geocoder: el nombre de la ciudad
        # es lo que se envía fuera, y repetirlo cada 15 minutos es regalar dato.
        with mock.patch.dict(weather.os.environ, {"CORT_CITY": "Bogotá"}):
            client = httpx.AsyncClient(transport=transport(
                {"geocoding-api.open-meteo.com": GEO_OK,
                 "api.open-meteo.com": FORECAST_OK}, self.seen))
            self.async_call(weather.refresh(client))
            self.async_call(weather.refresh(client))
            self.assertEqual(self.seen.count("geocoding-api.open-meteo.com"), 1)

    def test_ciudad_inexistente_no_inventa_un_clima(self):
        with mock.patch.dict(weather.os.environ, {"CORT_CITY": "Xicuco-9999"}):
            client = httpx.AsyncClient(transport=transport(
                {"geocoding-api.open-meteo.com": GEO_EMPTY}, self.seen))
            self.assertIsNone(self.async_call(weather.refresh(client)))
            self.assertIsNone(weather.snapshot())
            self.assertIn("no encontrada", weather.last_error())

    def test_un_500_del_servicio_no_es_un_clima(self):
        # El transporte también puede devolver un error HTTP en vez de reventar.
        # `raise_for_status` lo convierte en `HTTPStatusError` y el módulo lo
        # anota: un 500 pintado como "0 °C" sería un holograma mintiendo.
        with mock.patch.dict(weather.os.environ, {"CORT_CITY": "Bogotá"}):
            client = httpx.AsyncClient(transport=transport(
                {"geocoding-api.open-meteo.com": GEO_OK, "api.open-meteo.com": "boom"},
                self.seen))
            self.assertIsNone(self.async_call(weather.refresh(client)))
            self.assertIsNone(weather.snapshot())
            self.assertIn("500", weather.last_error())

    def test_la_caida_del_servicio_no_borra_el_clima_anterior(self):
        # Un corte de red pasajero no deja al HUD sin temperatura: se queda la
        # última foto y el error queda escrito para quien lo pregunte.
        with mock.patch.dict(weather.os.environ, {"CORT_CITY": "Bogotá"}):
            good = httpx.AsyncClient(transport=transport(
                {"geocoding-api.open-meteo.com": GEO_OK,
                 "api.open-meteo.com": FORECAST_OK}, self.seen))
            self.async_call(weather.refresh(good))
            bad = httpx.AsyncClient(transport=transport(
                {"api.open-meteo.com": httpx.ConnectError("sin ruta al servicio")}, self.seen))
            # `refresh` devuelve la foto vieja, no `None`: es el contrato del
            # adorno —un corte de red no deja al HUD sin temperatura.
            self.assertEqual(self.async_call(weather.refresh(bad))["temp_c"], 8.5)
            self.assertEqual(weather.snapshot()["temp_c"], 8.5)
            self.assertIn("sin ruta", weather.last_error())

    def test_una_respuesta_sin_temperatura_no_es_un_cero(self):
        # 0 °C es un valor legítimo y confundirlo con "no vino" pintaría un
        # atuendo de invierno con un `if not temp`. Aquí se distingue.
        with mock.patch.dict(weather.os.environ, {"CORT_CITY": "Medellín"}):
            client = httpx.AsyncClient(transport=transport(
                {"geocoding-api.open-meteo.com": GEO_OK,
                 "api.open-meteo.com": {"current": {"temperature_2m": 0.0}}}, self.seen))
            data = self.async_call(weather.refresh(client))
            self.assertEqual(data["temp_c"], 0.0)

            weather._reset()
            broken = httpx.AsyncClient(transport=transport(
                {"geocoding-api.open-meteo.com": GEO_OK,
                 "api.open-meteo.com": {"current": {}}}, self.seen))
            self.assertIsNone(self.async_call(weather.refresh(broken)))
            self.assertIn("sin temperatura", weather.last_error())

    def test_una_foto_muy_vieja_deja_de_ser_un_hecho(self):
        with mock.patch.dict(weather.os.environ, {"CORT_CITY": "Bogotá"}):
            client = httpx.AsyncClient(transport=transport(
                {"geocoding-api.open-meteo.com": GEO_OK,
                 "api.open-meteo.com": FORECAST_OK}, self.seen))
            self.async_call(weather.refresh(client))
            # Seis TTL sin poder refrescar: el número es una anécdota, no un dato.
            weather._cache["fetched_at"] -= weather.TTL_S * 4
            self.assertIsNone(weather.snapshot())

    def test_el_atuendo_usa_la_temperatura_real(self):
        # Une el clima con `outfit.py`: con 3 °C toca `hoodie`, no el traje de
        # 22°. Si el clima no llegara al `pick_outfit` esta prueba se cae sola.
        from cort_core.outfit import pick_outfit
        self.assertEqual(pick_outfit(15, 3.0), "hoodie")
        self.assertEqual(pick_outfit(15, 31.0), "light")
        self.assertEqual(pick_outfit(15, 22.0), "work")


if __name__ == "__main__":
    unittest.main()
