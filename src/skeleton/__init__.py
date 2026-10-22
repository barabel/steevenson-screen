"""Скелет Щита: метки деталей, общие построения, проверки Скелета.

Параметры — в skeleton.params. Тел Скелет не строит: их строят пакеты деталей.
"""
import math

import FreeCAD
import Part

from checks import MAX_OVERLAP
from sensor import PLUG

from . import params

V = FreeCAD.Vector
Z = V(0, 0, 1)

LID = "Крышка"
BOTTOM_DISH = "Нижняя Тарелка"
FLOOR = "Дно"
HOLDER = "Держатель"


def dish_label(index):
    """Метка Тарелки index, 1…DISH_COUNT − 1."""
    return f"Тарелка {index}"


# мм за габаритом тела: сквозное отверстие и путь выхода не кончаются на грани
BEYOND = 1


def revolved(points):
    """Тело вращения вокруг оси Щита: замкнутый контур (r, z) в плоскости XZ."""
    vertices = []
    for r, z in points + points[:1]:
        vertices.append(V(r, 0, z))
    return Part.Face(Part.makePolygon(vertices)).revolve(V(), Z, 360)


def gap_error(name, shape, other, other_shape, minimum):
    """Ошибка зазора от тела name до тела other меньше minimum, иначе None.

    Зазор сравнивается с точностью, с которой пишется, — 0.01 мм: зазор,
    ровный по построению, не падает от шума float.
    """
    gap = round(shape.distToShape(other_shape)[0], 2)
    if gap < minimum:
        return f"{name}: зазор до {other} ≥ {minimum:g} мм — {gap:.2f} мм"
    return None


def plug_gap(bodies):
    """Воздух вокруг Заглушки: до каждого тела, кроме Держателя, не меньше PLUG_MIN_GAP.

    Держатель держит Датчик и касается Ушка по задумке. Нет Заглушки или она
    null — молчит, как проверка габарита Датчика.
    """
    shape = bodies.get(PLUG)
    if shape is None or shape.isNull():
        return []
    errors = []
    for name, body in bodies.items():
        if name in (PLUG, HOLDER) or body.isNull():
            continue
        error = gap_error(PLUG, shape, name, body, params.PLUG_MIN_GAP)
        if error:
            errors.append(error)
    return errors


def hook_gap(bodies):
    """Над Крючком: от Держателя до Крышки не меньше HOOK_TO_LID_GAP.

    Верх Держателя — верх Крючка. Нет Держателя или Крышки или кто-то из них
    null — молчит.
    """
    holder_shape = bodies.get(HOLDER)
    lid_shape = bodies.get(LID)
    if holder_shape is None or lid_shape is None:
        return []
    if holder_shape.isNull() or lid_shape.isNull():
        return []
    error = gap_error(HOLDER, holder_shape, LID, lid_shape, params.HOOK_TO_LID_GAP)
    return [error] if error else []


TESSELLATION = 0.01  # мм, допуск триангуляции: радиус тела точнее зазоров


def axis_radius(shape):
    """Наибольшее расстояние тела от оси Щита, по точкам триангуляции."""
    points, _ = shape.tessellate(TESSELLATION)
    radii = []
    for point in points:
        radii.append(math.hypot(point.x, point.y))
    return max(radii)


def down_exit(bodies):
    """Выход вниз: Дно, Держатель и Заглушка уходят вниз из Щита, ничего не задевая.

    Так меняют батарейку, не снимая Щит. Проверка по радиусам: путь тела —
    цилиндр вокруг оси Щита радиусом его дальней от оси точки, от верха тела
    до низа Щита. Тело Щита в этом цилиндре — задевание. Цилиндр шире
    настоящего пути, поэтому проверка задевание не пропустит, но может
    поднять ложное у тела не на оси.

    Путь Дна с Нижней Тарелкой не сравнивается: Дно выкручивается, его
    витки идут по виткам резьбового кольца — это закрывает пара резьб.

    Нет Дна, Держателя или Заглушки или кто-то из них null — молчит.
    """
    leaving = [FLOOR, HOLDER, PLUG]
    for name in leaving:
        if name not in bodies or bodies[name].isNull():
            return []
    staying = {}
    bottom = math.inf  # ниже всех тел Щита: тело вышло целиком
    for name, shape in bodies.items():
        if name not in leaving and not shape.isNull():
            staying[name] = shape
            bottom = min(bottom, shape.BoundBox.ZMin - BEYOND)
    errors = []
    for name in leaving:
        shape = bodies[name]
        radius = axis_radius(shape)
        height = shape.BoundBox.ZMax - bottom
        path = Part.makeCylinder(radius, height, V(0, 0, bottom), Z)
        for other, other_shape in staying.items():
            if (name, other) == (FLOOR, BOTTOM_DISH):
                continue
            hit = path.common(other_shape)
            if not hit.isNull() and hit.Volume > MAX_OVERLAP:  # мимо — null
                errors.append(
                    f"{name}: выход вниз — задевает {other},"
                    f" {name} до {radius:.2f} мм от оси Щита",
                )
    return errors


# bodies → список ошибок, как в checks.py
CHECKS = [plug_gap, hook_gap, down_exit]


def build(doc):
    """Тел и референсов у Скелета нет: в сцене он только ради CHECKS."""
    return [], []
