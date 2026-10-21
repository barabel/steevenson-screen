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


def profile(top, hole, drip=False):
    """Тело вращения Тарелки: Полка от радиуса hole и конус от её наружного края.

    Верх Полки — на высоте top. Конус идёт вниз и наружу под CONE_ANGLE;
    его нижняя поверхность встречает низ Полки чуть внутри её края.
    С drip у отверстия — Капельник: его нижний край на радиусе hole,
    Полка начинается от его верхнего края.
    """
    shelf = params.SHELF_RADIUS
    outer = params.DISH_DIAMETER / 2
    rise = params.cone_rise()
    wall = params.DISH_WALL
    cone_wall = params.cone_wall_height()
    inner = shelf - (cone_wall - wall) / math.tan(math.radians(params.CONE_ANGLE))
    if drip:
        drop = wall + params.DRIP_DROP
        inset = params.DRIP_INSET
        # низ Капельника шириной в стенку по нормали к его наклону
        tip = hole + wall * math.hypot(inset, drop) / drop
        start = hole + inset
        lip = [
            (tip + (drop - wall) * inset / drop, top - wall),
            (tip, top - drop),
            (hole, top - drop),
        ]
    else:
        start = hole
        lip = [(hole, top - wall)]
    return revolved([
        (start, top),
        (shelf, top),
        (outer, top - rise),
        (outer, top - rise - cone_wall),
        (inner, top - wall),
    ] + lip)


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
    """Стойки Тарелки с верхом Полки на top: свисают до Полки нижней Тарелки.

    Низ — на верхе Полки нижней Тарелки, касание без пересечения. Верх —
    в середине своей Полки: сливается с ней без совпадающих граней.
    """
    bottom = top - params.DISH_PITCH
    height = params.DISH_PITCH - params.DISH_WALL / 2
    result = []
    for center in standoff_centers():
        result.append(Part.makeCylinder(
            params.STANDOFF_DIAMETER / 2,
            height,
            center + V(0, 0, bottom),
            Z,
        ))
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
    """Тарелка index (1…DISH_COUNT − 1) со Стойками до Полки соседней снизу."""
    top = params.dish_top(index)
    body = profile(top, params.DISH_HOLE_DIAMETER / 2, drip=True).fuse(standoffs(top))
    return stud_holes(body).removeSplitter()


def thread_ring():
    """Резьбовое кольцо под Полкой Нижней Тарелки, без витков.

    Верх — в середине Полки: врезан в неё. Низ — на THREAD_LENGTH ниже
    низа Полки.
    """
    inner = params.THREAD_DIAMETER / 2
    outer = inner + params.THREAD_RING_WALL
    top = params.floor_top() + params.DISH_WALL / 2
    bottom = params.floor_top() - params.THREAD_LENGTH
    return revolved([
        (inner, top),
        (outer, top),
        (outer, bottom),
        (inner, bottom),
    ])


def bottom_dish():
    """Нижняя Тарелка: профиль Тарелки и резьбовое кольцо под Полкой, без Стоек."""
    top = params.dish_top(params.DISH_COUNT)
    body = profile(top, params.DISH_HOLE_DIAMETER / 2).fuse(thread_ring())
    return stud_holes(body).removeSplitter()


def lid():
    """Крышка: Полка сплошная до оси, верх плоский в Точке подвеса; Стойки до Тарелки 1."""
    top = params.dish_top(0)
    body = profile(top, 0).fuse(standoffs(top))
    return stud_holes(body).removeSplitter()


def shapes():
    """Стопка сверху вниз: метка → Shape."""
    result = {LID: lid()}
    for index in range(1, params.DISH_COUNT):
        result[f"Тарелка {index}"] = dish(index)
    result[BOTTOM_DISH] = bottom_dish()
    return result


def standoffs_ring(bodies):
    """Отверстия под Шпильки на осях Стоек не задевают резьбовое кольцо.

    Шпилька проходит сквозь Полку Нижней Тарелки и выходит под неё рядом
    с кольцом. Полка и кольцо слиты в одно тело, проверка пересечений
    конфликт не видит: тела строятся отдельно из параметров Скелета,
    bodies не нужны.
    """
    ring = thread_ring()
    volume = 0
    for shape in stud_rods(ring):
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
