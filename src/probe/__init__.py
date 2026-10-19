"""Пробник резьбы Дна: кольца Тарелки и Дна, проверка их пары.

В сцену Щита не входит: Прогон строит Пробник в отдельный документ.
Кольца — в натуральную величину резьбы Скелета, ось — Z, низ на z = 0,
как в собранном Щите: вход кольца Тарелки снизу, кольца Дна сверху.
"""
import FreeCAD
import Part

import thread
from checks import MAX_OVERLAP
from skeleton import params as skeleton_params

from . import params

V = FreeCAD.Vector
Z = V(0, 0, 1)

DISH_RING = "Кольцо Тарелки"


def floor_ring_label(clearance):
    return f"Кольцо Дна {clearance:g}"


def dish_ring():
    """Кольцо Тарелки: внутренняя резьба номинальная.

    Стенка за впадинами — как у резьбового кольца Нижней Тарелки.
    """
    diameter = skeleton_params.THREAD_DIAMETER
    length = skeleton_params.THREAD_LENGTH
    blank = Part.makeCylinder(diameter / 2 + skeleton_params.THREAD_RING_WALL, length)
    return blank.cut(thread.internal(diameter, length))


def floor_ring(clearance):
    """Кольцо Дна: наружная резьба с зазором clearance, донышко снизу.

    Стенка за впадинами — как у кольца Тарелки.
    """
    diameter = skeleton_params.THREAD_DIAMETER
    length = skeleton_params.THREAD_LENGTH
    root = diameter / 2 - skeleton_params.THREAD_DEPTH - clearance
    bore = Part.makeCylinder(
        root - skeleton_params.THREAD_RING_WALL,
        length,
        V(0, 0, params.FLOOR_BOTTOM),
        Z,
    )
    return thread.external(diameter, length, clearance).cut(bore)


def rings():
    """Кольца в раскладке: метка → Shape. Кольцо Тарелки в начале, кольца Дна — рядом по X."""
    radius = skeleton_params.THREAD_DIAMETER / 2
    shapes = {DISH_RING: dish_ring()}
    x = radius + skeleton_params.THREAD_RING_WALL + params.SPACING + radius
    for clearance in params.CLEARANCES:
        shapes[floor_ring_label(clearance)] = floor_ring(clearance).translated(V(x, 0, 0))
        x += 2 * radius + params.SPACING
    return shapes


def stl_names():
    """Имена STL колец, латиницей: метка → имя без расширения."""
    names = {DISH_RING: "ring-dish"}
    for clearance in params.CLEARANCES:
        names[floor_ring_label(clearance)] = f"ring-floor-{clearance:g}"
    return names


def screwed_in(shape, into):
    """shape, поставленная соосно в into на ту же высоту.

    Сдвиг по оси кратен шагу: фаза спирали не меняется, зуб наружной
    резьбы остаётся посередине впадины.
    """
    box = shape.optimalBoundingBox()
    target = into.optimalBoundingBox()
    pitch = skeleton_params.THREAD_PITCH
    return shape.translated(V(
        target.Center.x - box.Center.x,
        target.Center.y - box.Center.y,
        round((target.ZMin - box.ZMin) / pitch) * pitch,
    ))


GAP_TOLERANCE = 0.02  # мм, на щели пары


def pair(bodies):
    """Каждое кольцо Дна, вкрученное в кольцо Тарелки: не пересекается, щель = зазору.

    Зазор кольца — из набора Пробника по метке. Нет кольца Тарелки или
    кольца Дна, или кто-то из них null — молчит.
    """
    dish = bodies.get(DISH_RING)
    if dish is None or dish.isNull():
        return []
    errors = []
    for clearance in params.CLEARANCES:
        label = floor_ring_label(clearance)
        floor = bodies.get(label)
        if floor is None or floor.isNull():
            continue
        screwed = screwed_in(floor, dish)
        volume = screwed.common(dish).Volume
        if volume > MAX_OVERLAP:
            errors.append(f"{label} в {DISH_RING}: пересечение — {volume:.2f} мм³")
        gap = screwed.distToShape(dish)[0]
        if abs(gap - clearance) > GAP_TOLERANCE:
            errors.append(
                f"{label} в {DISH_RING}: зазор {clearance:g} мм — щель {gap:.3f} мм",
            )
    return errors


CHECKS = [pair]  # bodies → список ошибок, как в checks.py


def build(doc):
    """Добавляет кольца в doc, возвращает их объекты."""
    objects = []
    for label, shape in rings().items():
        obj = doc.addObject("Part::Feature", "Ring")
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    return objects
