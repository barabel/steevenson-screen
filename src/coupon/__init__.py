"""Пробник резьбы Дна: кольца Тарелки и Дна, проверка их пары.

В сцену Щита не входит: Прогон строит Пробник в отдельный документ.
Кольца — в натуральную величину резьбы Скелета, ось — Z, низ на z = 0,
как в собранном Щите: вход кольца Тарелки снизу, кольца Дна сверху. Это
и ориентация печати: кольцо Тарелки — входом на стол, кольцо Дна —
донышком. Раскладка — сетка 2×2 в XY, только сдвиги: поворот вокруг Z
сбил бы фазу спирали в проверке пары.
"""
import FreeCAD
import Part

import thread
from checks import MAX_OVERLAP
from skeleton import BEYOND
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


def notches(count):
    """count насечек на донышке кольца Дна, сверху, вглубь на NOTCH_DEPTH.

    Параллельные пазы вдоль Y, посередине донышка: далеко от стенки, резьбу
    не задевают; видны, если заглянуть в кольцо.
    """
    slots = []
    for index in range(count):
        x = (index - (count - 1) / 2) * params.NOTCH_STEP
        slots.append(Part.makeBox(
            params.NOTCH_WIDTH,
            params.NOTCH_LENGTH,
            params.NOTCH_DEPTH + BEYOND,
            V(
                x - params.NOTCH_WIDTH / 2,
                -params.NOTCH_LENGTH / 2,
                params.FLOOR_BOTTOM - params.NOTCH_DEPTH,
            ),
        ))
    return Part.makeCompound(slots)


def floor_ring(clearance, count):
    """Кольцо Дна: наружная резьба с зазором clearance, донышко снизу.

    Стенка за впадинами — как у кольца Тарелки. На донышке count насечек.
    Донышко стоит на столе: нижний торец с фаской.
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
    ring = thread.external(diameter, length, clearance, bed_chamfer=True)
    return ring.cut([bore, notches(count)])


def rings():
    """Кольца в раскладке: метка → Shape.

    Сетка в 2 столбца, ячейка — Ø кольца Тарелки и отступ. Кольцо Тарелки
    первое, за ним кольца Дна в порядке набора; у n-го кольца Дна n насечек.
    """
    cell = skeleton_params.THREAD_DIAMETER + 2 * skeleton_params.THREAD_RING_WALL + params.SPACING
    shapes = {DISH_RING: dish_ring()}
    for index, clearance in enumerate(params.CLEARANCES, start=1):
        shapes[floor_ring_label(clearance)] = floor_ring(clearance, index)
    layout = {}
    for index, (label, shape) in enumerate(shapes.items()):
        column, row = index % 2, index // 2
        layout[label] = shape.translated(V(column * cell, -row * cell, 0))
    return layout


def stl_names():
    """Имена STL колец, латиницей: метка → имя без расширения."""
    names = {DISH_RING: "ring-dish"}
    for clearance in params.CLEARANCES:
        names[floor_ring_label(clearance)] = f"ring-floor-{clearance:g}"
    return names


AXIS_DECIMALS = 2  # ось кольца в XY — с точностью до 0.01 мм


def screwed_in(shape, into):
    """shape, поставленная соосно в into на ту же высоту.

    Ось — центр габарита в XY, округлённый до AXIS_DECIMALS знаков: габарит
    врёт на ~1e-7 мм, и на почти соосных кольцах common молча отдаёт
    пустоту. Сдвиг по оси кратен шагу: фаза спирали не меняется, зуб
    наружной резьбы остаётся посередине впадины.
    """
    box = shape.optimalBoundingBox()
    target = into.optimalBoundingBox()
    pitch = skeleton_params.THREAD_PITCH
    return shape.translated(V(
        round(target.Center.x, AXIS_DECIMALS) - round(box.Center.x, AXIS_DECIMALS),
        round(target.Center.y, AXIS_DECIMALS) - round(box.Center.y, AXIS_DECIMALS),
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


def bed(bodies):
    """Раскладка на столе: габарит по X, Y не больше стола, по Z не выше."""
    shapes = []
    for shape in bodies.values():
        if not shape.isNull():
            shapes.append(shape)
    if not shapes:
        return []
    box = Part.makeCompound(shapes).optimalBoundingBox()
    size = (box.XLength, box.YLength, box.ZMax)
    if all(length <= limit for length, limit in zip(size, params.BED)):
        return []
    layout = " × ".join(f"{length:.1f}" for length in size)
    table = " × ".join(f"{limit:g}" for limit in params.BED)
    return [f"стол: габарит раскладки {layout} мм — стол {table} мм"]


CHECKS = [pair, bed]  # bodies → список ошибок, как в checks.py


def build(doc):
    """Добавляет кольца в doc, возвращает их объекты."""
    objects = []
    for label, shape in rings().items():
        obj = doc.addObject("Part::Feature", "Ring")
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    return objects
