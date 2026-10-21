"""Стопка Щита: Крышка, Тарелки 1…N−1, Нижняя Тарелка; проверки стопки.

Метки и размеры — из Скелета. Строит тела под теми же метками, что были
у Черновиков стопки в Скелете.
"""
import math

import FreeCAD
import Part

from checks import MAX_OVERLAP
from skeleton import BEYOND, BOTTOM_DISH, LID, params, revolved

from .shadow import shadow

V = FreeCAD.Vector
Z = V(0, 0, 1)


def band(top, height):
    """Кольцевой слой конуса Тарелки.

    От поверхности с краем отверстия на высоте top вниз на height по вертикали.
    """
    hole = params.DISH_HOLE_DIAMETER / 2
    outer = params.DISH_DIAMETER / 2
    rise = params.DISH_RISE
    return revolved([
        (hole, top),
        (outer, top - rise),
        (outer, top - rise - height),
        (hole, top - height),
    ])


def standoff_centers():
    """Оси Стоек в плане."""
    centers = []
    for i in range(params.STANDOFF_COUNT):
        angle = math.radians(params.STANDOFF_ANGLE + i * 360 / params.STANDOFF_COUNT)
        centers.append(V(
            params.STANDOFF_RADIUS * math.cos(angle),
            params.STANDOFF_RADIUS * math.sin(angle),
            0,
        ))
    return centers


def standoffs(top):
    """Стойки Тарелки: от её стенки вверх до нижней поверхности соседней.

    Цилиндр Стойки обрезан слоем между нижними поверхностями двух Тарелок:
    низ — по своей стенке, верх — по соседней, касание без пересечения.
    """
    wall = params.dish_wall_height()
    pitch = params.DISH_PITCH
    span = band(top + pitch - wall, pitch)
    height = params.DISH_RISE + wall + pitch
    result = []
    for center in standoff_centers():
        cylinder = Part.makeCylinder(
            params.STANDOFF_DIAMETER / 2,
            height,
            center + V(0, 0, top - params.DISH_RISE - wall),
            Z,
        )
        result.append(cylinder.common(span))
    return result


def stud_rods(shape):
    """Цилиндры отверстий под Шпильки по осям Стоек, по Z насквозь через shape."""
    box = shape.BoundBox
    rods = []
    for center in standoff_centers():
        rods.append(Part.makeCylinder(
            params.STUD_HOLE_DIAMETER / 2,
            box.ZLength + 2 * BEYOND,
            center + V(0, 0, box.ZMin - BEYOND),
            Z,
        ))
    return rods


def stud_holes(shape):
    """shape с отверстиями под Шпильки по осям Стоек, насквозь по Z."""
    return shape.cut(stud_rods(shape))


def dish(index):
    """Тарелка index (1…DISH_COUNT) со Стойками до соседней сверху."""
    top = params.dish_top(index)
    body = band(top, params.dish_wall_height()).fuse(standoffs(top))
    return stud_holes(body).removeSplitter()


def thread_ring():
    """Резьбовое кольцо под Нижней Тарелкой, без витков.

    Верх кольца — по средней линии стенки конуса: врезан в Тарелку, наружу
    не выходит. Низ — на THREAD_LENGTH ниже, чем конус у внутренней стенки.
    """
    inner = params.THREAD_DIAMETER / 2
    outer = inner + params.THREAD_RING_WALL
    middle = params.dish_wall_height() / 2
    bottom = params.floor_top() - params.THREAD_LENGTH
    return revolved([
        (inner, params.dish_bottom_at(inner) + middle),
        (outer, params.dish_bottom_at(outer) + middle),
        (outer, bottom),
        (inner, bottom),
    ])


def bottom_dish():
    """Нижняя Тарелка: Тарелка со Стойками и резьбовым кольцом снизу."""
    return dish(params.DISH_COUNT).fuse(thread_ring()).removeSplitter()


def lid():
    """Крышка: Тарелка с закрытым отверстием, верх — в Точке подвеса."""
    wall = params.dish_wall_height()
    cover = Part.makeCylinder(
        params.DISH_HOLE_DIAMETER / 2,
        wall,
        V(0, 0, params.dish_top(0) - wall),
        Z,
    )
    body = band(params.dish_top(0), wall).fuse(cover)
    return stud_holes(body).removeSplitter()


def shapes():
    """Стопка сверху вниз: метка → Shape."""
    result = {LID: lid()}
    for index in range(1, params.DISH_COUNT):
        result[f"Тарелка {index}"] = dish(index)
    result[BOTTOM_DISH] = bottom_dish()
    return result


def standoffs_ring(bodies):
    """Стойки Нижней Тарелки с отверстиями под Шпильки не задевают резьбовое кольцо.

    Стойки и кольцо слиты в одно тело, проверка пересечений их не видит:
    тела строятся отдельно из параметров Скелета, bodies не нужны.
    """
    ring = thread_ring()
    top = params.dish_top(params.DISH_COUNT)
    volume = 0
    for shape in standoffs(top) + stud_rods(ring):
        volume += ring.common(shape).Volume
    if volume > MAX_OVERLAP:
        return [
            f"{BOTTOM_DISH}: Стойки и резьбовое кольцо не пересекаются"
            f" — пересечение {volume:.2f} мм³",
        ]
    return []


def clearance(bodies):
    """Просвет между соседними телами стопки не меньше DISH_MIN_CLEARANCE.

    Меряется по сечению плоскостью через ось Щита посередине между Стойками:
    Стойки в него не попадают, а у тел вращения кратчайшее расстояние лежит
    в такой плоскости. Нет соседа или он null — пару пропускает.
    """
    names = [LID]
    for index in range(1, params.DISH_COUNT):
        names.append(f"Тарелка {index}")
    names.append(BOTTOM_DISH)
    angle = math.radians(params.STANDOFF_ANGLE + 180 / params.STANDOFF_COUNT)
    normal = V(-math.sin(angle), math.cos(angle), 0)
    minimum = params.DISH_MIN_CLEARANCE
    errors = []
    for upper, lower in zip(names, names[1:]):
        pair = [bodies.get(upper), bodies.get(lower)]
        if any(shape is None or shape.isNull() for shape in pair):
            continue
        sections = []
        for shape in pair:
            sections.append(Part.Compound(shape.slice(normal, 0)))
        gap = round(sections[0].distToShape(sections[1])[0], 2)
        if gap < minimum:
            errors.append(
                f"{upper} ↔ {lower}: просвет ≥ {minimum:g} мм — {gap:.2f} мм",
            )
    return errors


# bodies → список ошибок, как в checks.py
CHECKS = [standoffs_ring, shadow, clearance]


def build(doc):
    """Добавляет тела стопки в doc, возвращает (тела, референсы)."""
    objects = []
    for label, shape in shapes().items():
        obj = doc.addObject("Part::Feature", "Stack")
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    return objects, []
