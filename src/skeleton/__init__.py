"""Скелет Щита: Черновики деталей из параметров Скелета, проверки Скелета.

Черновик — упрощённое тело детали под её меткой. Фаза детали убирает свой
Черновик отсюда и добавляет в сцену свой пакет с той же меткой.
"""
import math

import FreeCAD
import Part

from . import params

V = FreeCAD.Vector
X = V(1, 0, 0)
Z = V(0, 0, 1)

LID = "Крышка"
BOTTOM_DISH = "Нижняя Тарелка"
FLOOR = "Дно"
HOLDER = "Держатель"


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


def floor():
    """Дно: цилиндр в резьбовом кольце с радиальным зазором резьбы."""
    radius = params.THREAD_DIAMETER / 2 - params.THREAD_CLEARANCE
    return Part.makeCylinder(
        radius,
        params.THREAD_LENGTH,
        V(0, 0, params.floor_top() - params.THREAD_LENGTH),
        Z,
    )


def holder():
    """Держатель: пластина на Дне за Корпусом, наверху Крючок через Ушко.

    Корпус опирается на пластину спиной. Крючок — прямой стержень, Ушко
    лежит на нём верхом отверстия; вылет — как у крючка Вешалки.
    """
    sensor = params.sensor
    ear = params.sensor_shift()  # центр отверстия Ушка
    face = ear.x + sensor.CASE_X  # спина Корпуса
    rod = sensor.HANGER_ROD_DIAMETER / 2
    rod_z = ear.z + sensor.EAR_INNER_DIAMETER / 2 - rod
    thickness = params.HOLDER_THICKNESS
    width = params.HOLDER_WIDTH
    floor_top = params.floor_top()
    # верх пластины — по оси стержня: стержень не касается её верха
    plate = Part.makeBox(
        thickness,
        width,
        rod_z - floor_top,
        V(face - thickness, -width / 2, floor_top),
    )
    hook = Part.makeCylinder(
        rod,
        thickness + sensor.HANGER_REACH - sensor.HANGER_PLATE_THICKNESS,
        V(face - thickness, 0, rod_z),
        X,
    )
    return plate.fuse(hook).removeSplitter()


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
    """Черновики: метка → Shape, стопка сверху вниз, затем Дно и Держатель."""
    shapes = {LID: lid()}
    for index in range(1, params.DISH_COUNT):
        shapes[f"Тарелка {index}"] = dish(index)
    shapes[BOTTOM_DISH] = bottom_dish()
    shapes[FLOOR] = floor()
    shapes[HOLDER] = holder()
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
