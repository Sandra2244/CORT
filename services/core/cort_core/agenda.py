"""La agenda: alarmas y recordatorios que sobreviven a cerrar CORT.

Los temporizadores (`timer.py`) viven mientras dura la conexión y mueren con
ella; una alarma de las 7 de la mañana no puede. Por eso esto se guarda en un
archivo (`services/core/data/agenda.json`, ya fuera del repositorio por
`.gitignore`) y se relee al arrancar.

Lo que NO hace: sonar sola. CORT es un programa en una pestaña del navegador, no
un servicio del sistema. La alarma suena si el core está encendido y la cara
abierta a la hora; si no, **queda pendiente y se avisa en cuanto alguien abre la
cara** («se te pasó la alarma de las 7:00»). Prometer más sería mentir, y una
alarma que no suena sin avisar es el peor fallo de una alarma.

Sin reloj propio: el `reloj` es inyectable y cada método recibe `ahora` cuando
importa, así que las pruebas no esperan a que pase el tiempo. Y sin hilo: quien
la usa pide `segundos_hasta_proximo` y duerme exactamente eso; con la agenda
vacía el coste en reposo es cero.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

#: Cuántos pendientes como mucho. Una alarma por error repetido 10 000 veces no
#: debe llenar el disco ni el bucle que las atiende.
MAX_PENDIENTES = 100
#: Largo máximo del texto de un recordatorio.
MAX_TEXTO = 200

_DEFAULT = Path(__file__).resolve().parents[1] / "data" / "agenda.json"


def ruta_por_defecto() -> Path:
    return Path(os.getenv("CORT_AGENDA_FILE") or _DEFAULT)


class Agenda:
    def __init__(self, ruta: Path | None = None):
        self.ruta = Path(ruta) if ruta else ruta_por_defecto()
        self.items: list[dict] = []
        self._siguiente_id = 1
        self._cargar()

    # -- disco --------------------------------------------------------------------
    def _cargar(self) -> None:
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            items = datos.get("items", []) if isinstance(datos, dict) else []
        except (OSError, ValueError):
            # Sin archivo, o dañado: se empieza vacía. Un archivo roto no debe
            # impedir arrancar CORT, y nunca se borra el original aquí.
            items = []
        validos = []
        for it in items:
            try:
                datetime.fromisoformat(it["cuando"])
                validos.append({"id": int(it["id"]), "tipo": str(it["tipo"]),
                                "cuando": str(it["cuando"]), "texto": str(it.get("texto", ""))[:MAX_TEXTO],
                                "entregado": bool(it.get("entregado", False))})
            except (KeyError, TypeError, ValueError):
                continue
        self.items = validos
        self._siguiente_id = max((i["id"] for i in validos), default=0) + 1

    def _guardar(self) -> None:
        """Escribe a un archivo temporal y lo renombra: si se corta la luz a
        medio escribir, queda la agenda de antes y no un JSON a medias."""
        try:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.ruta.parent, prefix=".agenda-", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"items": self.items}, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.ruta)
        except OSError:
            # Sin disco, la agenda sigue viva en memoria hasta cerrar: peor que
            # guardarla, mejor que perder la alarma que se acaba de pedir.
            pass

    # -- altas y bajas ------------------------------------------------------------
    def agregar(self, tipo: str, cuando: datetime, texto: str = "") -> dict:
        if len(self.pendientes()) >= MAX_PENDIENTES:
            raise ValueError(f"ya hay {MAX_PENDIENTES} pendientes; cancela alguno")
        item = {"id": self._siguiente_id, "tipo": tipo,
                "cuando": cuando.replace(tzinfo=None, microsecond=0).isoformat(timespec="seconds"),
                "texto": " ".join(str(texto).split())[:MAX_TEXTO], "entregado": False}
        self._siguiente_id += 1
        self.items.append(item)
        self._guardar()
        return dict(item)

    def pendientes(self) -> list[dict]:
        """Lo que aún no sonó, lo más próximo primero."""
        return sorted((dict(i) for i in self.items if not i["entregado"]),
                      key=lambda i: i["cuando"])

    def cancelar(self, tipo: str | None = None, texto: str | None = None) -> int:
        """Quita pendientes y dice cuántos. Sin filtros, todos; con `tipo`
        («alarma» o «recordatorio»), sólo ésos; con `texto`, los que lo contengan."""
        antes = len(self.pendientes())
        t = (texto or "").lower().strip()
        self.items = [i for i in self.items if i["entregado"]
                      or not ((tipo is None or i["tipo"] == tipo)
                              and (not t or t in i["texto"].lower()))]
        quitados = antes - len(self.pendientes())
        if quitados:
            self._guardar()
        return quitados

    def cancelar_id(self, id_: int) -> bool:
        antes = len(self.items)
        self.items = [i for i in self.items if not (i["id"] == id_ and not i["entregado"])]
        if len(self.items) != antes:
            self._guardar()
            return True
        return False

    # -- el reloj -----------------------------------------------------------------
    def vencidos(self, ahora: datetime) -> list[dict]:
        """Lo que ya tocaba sonar y aún no se avisó, en orden."""
        ahora_s = ahora.replace(tzinfo=None, microsecond=0).isoformat(timespec="seconds")
        return [i for i in self.pendientes() if i["cuando"] <= ahora_s]

    def marcar_entregado(self, id_: int) -> None:
        for i in self.items:
            if i["id"] == id_ and not i["entregado"]:
                i["entregado"] = True
                self._guardar()
                break
        # Lo ya entregado hace tiempo no se queda para siempre en el archivo.
        if len(self.items) > 4 * MAX_PENDIENTES:
            self.items = [i for i in self.items if not i["entregado"]] + \
                         [i for i in self.items if i["entregado"]][-MAX_PENDIENTES:]
            self._guardar()

    def segundos_hasta_proximo(self, ahora: datetime) -> float | None:
        """Cuánto falta para el próximo pendiente **futuro**, o `None` si no hay.

        Los ya vencidos no cuentan: si no hay a quién avisarlos (nadie tiene la
        cara abierta), contarlos haría un bucle que gira sin dormir.
        """
        a = ahora.replace(tzinfo=None)
        futuros = [datetime.fromisoformat(i["cuando"]) for i in self.pendientes()
                   if datetime.fromisoformat(i["cuando"]) > a]
        if not futuros:
            return None
        return max(0.0, (min(futuros) - a).total_seconds())


def marco(item: dict, *, atrasada: bool = False) -> dict:
    """El cuadro que viaja por el WebSocket cuando suena algo."""
    return {"type": "alarm", "id": item["id"], "tipo": item["tipo"],
            "texto": item["texto"], "cuando": item["cuando"][11:16], "atrasada": atrasada}
