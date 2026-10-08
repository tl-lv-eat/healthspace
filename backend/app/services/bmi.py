from __future__ import annotations


def calc_bmi(weight_kg: float, height_cm: float) -> float | None:
    if height_cm is None or weight_kg is None:
        return None
    if float(height_cm) <= 0 or float(weight_kg) <= 0:
        return None
    h = float(height_cm) / 100.0
    return round(float(weight_kg) / (h * h), 1)
