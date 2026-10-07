"""Elige atuendo y modo visual según hora y temperatura (función real de CORT)."""

def pick_outfit(hour: int, temp_c: float) -> str:
    if not 0 <= hour <= 23:
        raise ValueError("hour debe estar entre 0 y 23")
    if hour >= 22 or hour < 6:
        return "night"
    if temp_c <= 12:
        return "hoodie"
    if temp_c >= 28:
        return "light"
    if 9 <= hour < 18:
        return "work"
    return "casual"
