"""Скелет Щита: Черновики деталей из параметров Скелета, проверки Скелета.

Черновик — упрощённое тело детали под её меткой. Фаза детали убирает свой
Черновик отсюда и добавляет в сцену свой пакет с той же меткой.
"""
import math

import FreeCAD
import Part

from . import params

V = FreeCAD.Vector
Z = V(0, 0, 1)

LID = "Крышка"
BOTTOM_DISH = "Нижняя Тарелка"


def revolved(points):
    """Тело вращения вокруг оси Щита: замкнутый контур (r, z) в плоскости XZ."""
    vertices = []
    for r, z in points + points[:1]:
        vertices.append(V(r, 0, z))
    return Part.Face(Part.makePolygon(vertices)).revolve(V(), Z, 360)


def band(top, height):
    """Кольцевой слой конуса Тарелки: от поверхности с краем отверстия
    на высоте top вниз на height по вертикали."""
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

    Цилиндр бобышки обрезан слоем между нижними поверхностями двух Тарелок:
    низ — по своей стенке, верх — по соседней, касание без пересечения.
    """
    wall = params.dish_wall_height()
    pitch = params.DISH_PITCH
    span = band(top + pitch - wall, pitch)
    height = params.DISH_RISE + wall + pitch
    bosses = []
    for center in standoff_centers():
        boss = Part.makeCylinder(
            params.STANDOFF_DIAMETER / 2,
            height,
            center + V(0, 0, top - params.DISH_RISE - wall),
            Z,
        )
        bosses.append(boss.common(span))
    return bosses


def stud_holes(shape):
    """shape с отверстиями под Шпильки по осям Стоек, насквозь по Z."""
    box = shape.BoundBox
    holes = []
    for center in standoff_centers():
        holes.append(Part.makeCylinder(
            params.STUD_HOLE_DIAMETER / 2,
            box.ZLength + 2,
            center + V(0, 0, box.ZMin - 1),
            Z,
        ))
    return shape.cut(holes)


def dish(index):
    """Тарелка index (1…DISH_COUNT) со Стойками до соседней сверху."""
    top = params.dish_top(index)
    body = band(top, params.dish_wall_height()).fuse(standoffs(top))
    return stud_holes(body).removeSplitter()


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


def drafts():
    """Черновики стопки: метка → Shape, сверху вниз."""
    shapes = {LID: lid()}
    for index in range(1, params.DISH_COUNT):
        shapes[f"Тарелка {index}"] = dish(index)
    shapes[BOTTOM_DISH] = dish(params.DISH_COUNT)
    return shapes


CHECKS = []  # bodies → список ошибок, как в checks.py


def build(doc):
    """Добавляет Черновики в doc, возвращает (тела, референсы)."""
    objects = []
    for label, shape in drafts().items():
        obj = doc.addObject("Part::Feature", "Draft")
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    return objects, []
