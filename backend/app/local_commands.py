"""Comandos locales instantáneos de CORT — sin IA, sin internet."""
from __future__ import annotations

from datetime import datetime

import psutil


def now() -> str:
    return f"Son las {datetime.now().strftime('%H:%M')} del día de hoy."


def today() -> str:
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    d = datetime.now()
    return f"Hoy es {dias[d.weekday()]}, {d.day} de {meses[d.month - 1]} de {d.year}."


def battery() -> str:
    b = psutil.sensors_battery()
    if b is None:
        return "Este equipo no reporta batería; probablemente sea un PC de escritorio."
    estado = "conectado a la corriente" if b.power_plugged else "con batería"
    return f"Batería al {b.percent:.0f} %, {estado}."


def system_stats() -> str:
    cpu = psutil.cpu_percent(interval=0.4)
    ram = psutil.virtual_memory()
    disco = psutil.disk_usage("/")
    return (f"CPU {cpu:.0f} % · RAM {ram.percent:.0f} % "
            f"({ram.used / 1e9:.1f} de {ram.total / 1e9:.1f} GB) · "
            f"Disco {disco.percent:.0f} % usado.")


def greeting() -> str:
    h = datetime.now().hour
    saludo = "Buenos días" if 6 <= h < 13 else ("Buenas tardes" if h < 21 else "Buenas noches")
    return f"{saludo}. CORT a sus órdenes."
