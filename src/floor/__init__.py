"""Дно и Держатель Щита; проверки Дна и Держателя.

Метки и размеры — из Скелета. Строит тела под теми же метками, что были
у Черновиков Дна и Держателя в Скелете.
"""
import math

import FreeCAD
import Part

from checks import MAX_OVERLAP
from sensor import PLUG
from sensor import params as sensor_params
from skeleton import FLOOR, HOLDER, params

V = FreeCAD.Vector
X = V(1, 0, 0)
Y = V(0, 1, 0)
Z = V(0, 0, 1)


def floor():
    """Дно: цилиндр в резьбовом кольце по сердечнику наружной резьбы, без витков.

    Сердечник — впадины витков Дна с зазором резьбы: Дно проходит
    внутри витков резьбового кольца, не задевая их.
    """
    radius = (
        params.THREAD_DIAMETER / 2
        - params.THREAD_DEPTH
        - params.THREAD_CLEARANCE
    )
    return Part.makeCylinder(
        radius,
        params.THREAD_LENGTH,
        V(0, 0, params.floor_top() - params.THREAD_LENGTH),
        Z,
    )


def hook_section(center, radial):
    """Сечение Крючка: правильный восьмигранник под ключ HOOK_SECTION.

    Плоскость сечения — radial и Y, грани смотрят по radial и по Y.
    """
    corner = params.HOOK_SECTION / 2 / math.cos(math.radians(22.5))
    points = []
    for i in range(9):
        angle = math.radians(22.5 + 45 * i)
        points.append(
            center
            + radial * (corner * math.cos(angle))
            + Y * (corner * math.sin(angle)),
        )
    return Part.Face(Part.makePolygon(points))


def holder():
    """Держатель: пластина на Дне за Корпусом, наверху Крючок через Ушко.

    Корпус опирается на пластину спиной. Крючок — одна дуга по форме крючка
    Вешалки: из пластины чуть вниз, низ дуги под центром отверстия Ушка,
    кончик вверх. Центр дуги — над центром отверстия, на такой высоте, что
    верх отверстия у передней грани Ушка лежит на внутренней стороне дуги —
    на углах её грани, без пересечения. Крючок — у края пластины по Y:
    при печати на боку оба начинаются от стола.
    """
    ear = params.sensor_shift()  # центр отверстия Ушка
    face = ear.x + sensor_params.CASE_X  # спина Корпуса
    thickness = params.HOLDER_THICKNESS
    half = params.HOOK_SECTION / 2
    bend = sensor_params.HANGER_BEND_RADIUS
    inner = bend - half  # внутренняя сторона дуги
    flat = half * math.tan(math.radians(22.5))  # половина грани сечения
    # верх отверстия над углом грани сечения, на передней грани Ушка
    hole_top = math.sqrt((sensor_params.EAR_INNER_DIAMETER / 2) ** 2 - flat ** 2)
    ear_front = sensor_params.EAR_X + sensor_params.EAR_THICKNESS
    center = ear + V(0, 0, hole_top + math.sqrt(inner ** 2 - ear_front ** 2))
    start = math.radians(90 - sensor_params.HANGER_BEND_ANGLE)  # от низа дуги
    radial = V(math.sin(start), 0, -math.cos(start))
    tangent = V(math.cos(start), 0, math.sin(start))
    section = hook_section(center + radial * bend, radial)
    # ось −Y: от низа дуги к +X, кончик вверх
    arc = section.revolve(center, Y * -1, sensor_params.HANGER_BEND_ANGLE)
    # стержень от начала дуги назад до середины толщины пластины
    stem_length = (center.x + radial.x * bend - (face - thickness / 2)) / tangent.x
    stem = section.extrude(tangent * -stem_length)
    floor_top = params.floor_top()
    # верх пластины — по центру дуги, вровень с кончиком: стержень внутри неё
    plate = Part.makeBox(
        thickness,
        params.HOLDER_WIDTH,
        center.z - floor_top,
        V(face - thickness, -half, floor_top),
    )
    return plate.fuse([stem, arc]).removeSplitter()


def shapes():
    """Дно и Держатель: метка → Shape."""
    return {
        FLOOR: floor(),
        HOLDER: holder(),
    }


def hangs_on_hook(bodies):
    """Висит на Крючке: Держатель проходит сквозь отверстие Ушка Заглушки.

    Отверстие — из параметров Датчика и переноса Датчика. Держатель занимает
    часть его объёма — Крючок в Ушке; что Крючок не врезается в Ушко, ловит
    проверка пересечений. Нет Заглушки или Держателя или кто-то из них
    null — молчит.
    """
    plug_shape = bodies.get(PLUG)
    holder_shape = bodies.get(HOLDER)
    if plug_shape is None or holder_shape is None:
        return []
    if plug_shape.isNull() or holder_shape.isNull():
        return []
    hole = Part.makeCylinder(
        sensor_params.EAR_INNER_DIAMETER / 2,
        sensor_params.EAR_THICKNESS,
        params.sensor_shift() + V(sensor_params.EAR_X, 0, 0),
        X,
    )
    hit = holder_shape.common(hole)
    volume = 0 if hit.isNull() else hit.Volume  # мимо — null
    if volume > MAX_OVERLAP:
        return []
    return [
        f"{HOLDER}: Крючок не проходит сквозь Ушко {PLUG}"
        f" — в отверстии Ушка {volume:g} мм³ Держателя",
    ]


# bodies → список ошибок, как в checks.py
CHECKS = [hangs_on_hook]


def build(doc):
    """Добавляет Дно и Держатель в doc, возвращает (тела, референсы)."""
    objects = []
    for label, shape in shapes().items():
        obj = doc.addObject("Part::Feature", "Floor")
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    return objects, []
