"""Проверки геометрии: тела сцены (Label → Shape) → список ошибок, пусто = ок.

Проверка — функция bodies → список ошибок. Фазы дописывают свои в CHECKS,
существующие не меняют.
"""


def valid(bodies):
    errors = []
    for name, shape in bodies.items():
        if not shape.isValid():
            errors.append(f"{name}: isValid — геометрия битая")
    return errors


def one_solid(bodies):
    errors = []
    for name, shape in bodies.items():
        count = len(shape.Solids)
        if count != 1:
            errors.append(f"{name}: 1 solid — solid'ов {count}")
    return errors


def positive_volume(bodies):
    errors = []
    for name, shape in bodies.items():
        if shape.Volume <= 0:
            errors.append(f"{name}: объём > 0 — объём {shape.Volume:g} мм³")
    return errors


MAX_OVERLAP = 0.001  # мм³, шум булевых операций


def no_overlaps(bodies):
    errors = []
    names = list(bodies)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            volume = bodies[a].common(bodies[b]).Volume
            if volume > MAX_OVERLAP:
                errors.append(f"{a} × {b}: пересечение — {volume:g} мм³")
    return errors


CHECKS = [valid, one_solid, positive_volume, no_overlaps]


def check(bodies):
    errors = []
    for one_check in CHECKS:
        errors += one_check(bodies)
    return errors
