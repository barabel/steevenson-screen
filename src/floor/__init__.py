"""Дно и Держатель Щита; проверки Дна и Держателя.

Метки и размеры — из Скелета. Строит тела под теми же метками, что были
у Черновиков Дна и Держателя в Скелете.
"""
import math

import FreeCAD
import Part

import thread
from checks import GAP_TOLERANCE, MAX_OVERLAP
from sensor import PLUG
from sensor import params as sensor_params
from skeleton import BEYOND, BOTTOM_DISH, FLOOR, HOLDER, params, revolved

V = FreeCAD.Vector
X = V(1, 0, 0)
Y = V(0, 1, 0)
Z = V(0, 0, 1)


def grip(top, root):
    """Хват: Обечайка радиусом root от top вниз, снаружи на ней кольцо с рёбрами.

    top — низ витков, он же низ резьбового кольца. Верх кольца — на
    FLOOR_GRIP_GAP ниже, скошен от Обечайки наружу; пазы между рёбрами
    вертикальные, сквозь всю высоту кольца. Тело вращения от оси: середину
    вынимает Дно.
    """
    ring_top = top - params.FLOOR_GRIP_GAP
    low = ring_top - params.FLOOR_GRIP_HEIGHT
    outer = params.FLOOR_GRIP_DIAMETER / 2
    slope = (outer - root) * math.tan(math.radians(params.FLOOR_GRIP_CHAMFER_ANGLE))
    ring = revolved([
        (0, low),
        (outer, low),
        (outer, ring_top - slope),
        (root, ring_top),
        (root, top),
        (0, top),
    ])
    radius = params.FLOOR_GRIP_FLUTE_DIAMETER / 2
    flutes = []
    for i in range(params.FLOOR_GRIP_FLUTE_COUNT):
        angle = math.radians(i * 360 / params.FLOOR_GRIP_FLUTE_COUNT)
        flutes.append(Part.makeCylinder(
            radius,
            params.FLOOR_GRIP_HEIGHT + BEYOND,
            V(outer * math.cos(angle), outer * math.sin(angle), low - BEYOND),
            Z,
        ))
    return ring.cut(flutes)


def floor():
    """Дно: сверху Диск, вниз от него Обечайка с наружной резьбой, внизу хват.

    Верх Диска — в верхе Дна Скелета, на низе Полки Нижней Тарелки: это
    упор, касание без пересечения. Витки — модулем резьбы с зазором Скелета,
    по всей длине резьбового кольца и от его низа: спираль та же, зуб
    посередине впадины кольца. Заход с фаской — сверху, у Диска: этот конец
    входит в кольцо первым. Стенка за впадинами — как у кольца. Хват — под
    резьбовым кольцом с зазором, его не касается: второго упора нет. В Диске —
    дренаж: отверстия по окружности, насквозь.
    """
    diameter = params.THREAD_DIAMETER
    length = params.THREAD_LENGTH
    clearance = params.THREAD_CLEARANCE
    bottom = params.floor_top() - length
    root = diameter / 2 - params.THREAD_DEPTH - clearance
    low = bottom - params.FLOOR_GRIP_GAP - params.FLOOR_GRIP_HEIGHT
    disk_bottom = params.floor_top() - params.FLOOR_DISK_THICKNESS
    bore = Part.makeCylinder(
        root - params.THREAD_RING_WALL,
        disk_bottom - low + BEYOND,
        V(0, 0, low - BEYOND),
        Z,
    )
    drains = []
    for i in range(params.FLOOR_DRAIN_COUNT):
        angle = math.radians(i * 360 / params.FLOOR_DRAIN_COUNT)
        drains.append(Part.makeCylinder(
            params.FLOOR_DRAIN_DIAMETER / 2,
            params.FLOOR_DISK_THICKNESS + 2 * BEYOND,
            V(
                params.FLOOR_DRAIN_RADIUS * math.cos(angle),
                params.FLOOR_DRAIN_RADIUS * math.sin(angle),
                disk_bottom - BEYOND,
            ),
            Z,
        ))
    sleeve = thread.external(diameter, length, clearance).translated(V(0, 0, bottom))
    return sleeve.fuse(grip(bottom, root)).cut([bore] + drains)


# градусы, половина центрального угла восьмигранника (360 / 8 / 2): от
# середины грани до угла
OCTAGON_HALF_ANGLE = 22.5


def hook_section(center, radial):
    """Сечение Крючка: правильный восьмигранник под ключ HOOK_SECTION.

    Плоскость сечения — radial и Y, грани смотрят по radial и по Y.
    """
    corner = params.HOOK_SECTION / 2 / math.cos(math.radians(OCTAGON_HALF_ANGLE))
    points = []
    for i in range(8):
        angle = math.radians(OCTAGON_HALF_ANGLE * (2 * i + 1))
        points.append(
            center
            + radial * (corner * math.cos(angle))
            + Y * (corner * math.sin(angle)),
        )
    return Part.Face(Part.makePolygon(points + points[:1]))


def plate_corner():
    """Угол пластины Держателя: задняя грань по X, край у Крючка по Y, верх Диска.

    Задняя грань — за спиной Корпуса на толщину пластины; Крючок — у края
    пластины по Y, пластина от него к +Y на HOLDER_WIDTH.
    """
    return V(
        params.sensor_shift().x + sensor_params.CASE_X - params.HOLDER_THICKNESS,
        -params.HOOK_SECTION / 2,
        params.floor_top(),
    )


def holder():
    """Держатель: Пятка на Диске, пластина за Корпусом, наверху Крючок через Ушко.

    Пятка — от задней грани пластины к −X, в сторону от Носика, касается
    Диска без пересечения. Корпус опирается на пластину спиной. Крючок — одна
    дуга по форме крючка Вешалки: из пластины чуть вниз, низ дуги под центром
    отверстия Ушка, кончик вверх. Центр дуги — над центром отверстия, на
    такой высоте, что верх отверстия у передней грани Ушка лежит на
    внутренней стороне дуги — на углах её грани, без пересечения. Крючок —
    у края пластины по Y: при печати на боку оба начинаются от стола.
    """
    ear = params.sensor_shift()  # центр отверстия Ушка
    corner = plate_corner()
    thickness = params.HOLDER_THICKNESS
    half = params.HOOK_SECTION / 2
    bend = sensor_params.HANGER_BEND_RADIUS
    inner = bend - half  # внутренняя сторона дуги
    flat = half * math.tan(math.radians(OCTAGON_HALF_ANGLE))  # половина грани сечения
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
    stem_length = (center.x + radial.x * bend - (corner.x + thickness / 2)) / tangent.x
    stem = section.extrude(tangent * -stem_length)
    # верх пластины — по центру дуги, вровень с кончиком: стержень внутри неё
    plate = Part.makeBox(
        thickness,
        params.HOLDER_WIDTH,
        center.z - corner.z,
        corner,
    )
    heel = Part.makeBox(
        params.HEEL_LENGTH,
        params.HOLDER_WIDTH,
        params.HEEL_THICKNESS,
        corner - V(params.HEEL_LENGTH, 0, 0),
    )
    return plate.fuse([heel, stem, arc]).removeSplitter()


def screw_holes():
    """Отверстия под два винта M4 Держатель↔Дно: насквозь через Диск и Пятку.

    Оси — посередине длины Пятки, рядом по Y симметрично середине ширины
    пластины.
    """
    corner = plate_corner()
    x = corner.x - params.HEEL_LENGTH / 2
    middle = corner.y + params.HOLDER_WIDTH / 2
    bottom = params.floor_top() - params.FLOOR_DISK_THICKNESS - BEYOND
    depth = params.FLOOR_DISK_THICKNESS + params.HEEL_THICKNESS + 2 * BEYOND
    holes = []
    for side in (-1, 1):
        y = middle + side * params.HEEL_SCREW_SPACING / 2
        holes.append(
            Part.makeCylinder(
                params.STUD_HOLE_DIAMETER / 2,
                depth,
                V(x, y, bottom),
                Z,
            ),
        )
    return holes


def shapes():
    """Дно и Держатель: метка → Shape. Отверстия под винты — в обоих, соосно."""
    holes = screw_holes()
    return {
        FLOOR: floor().cut(holes),
        HOLDER: holder().cut(holes),
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


def thread_pair(bodies):
    """Пара резьб: Дно в резьбовом кольце Нижней Тарелки без пересечения, щель = зазору.

    Щель — от пояса резьбы Дна до Нижней Тарелки: от низа кольца на шаг не
    доходя до низа Полки. Касание Диска с Полкой — упор, а не щель, и что
    у Дна ниже кольца, в пояс не входит. Допуск щели — как у пары Пробника.
    Нет Дна или Нижней Тарелки или кто-то из них null — молчит.
    """
    floor_shape = bodies.get(FLOOR)
    dish = bodies.get(BOTTOM_DISH)
    if floor_shape is None or dish is None:
        return []
    if floor_shape.isNull() or dish.isNull():
        return []
    errors = []
    volume = floor_shape.common(dish).Volume
    if volume > MAX_OVERLAP:
        errors.append(
            f"{FLOOR} ↔ {BOTTOM_DISH}: пара резьб без пересечения"
            f" — пересечение {volume:.2f} мм³",
        )
    belt = Part.makeCylinder(
        params.THREAD_DIAMETER / 2 + params.THREAD_RING_WALL,  # до наружной стенки кольца
        params.THREAD_LENGTH - params.THREAD_PITCH,
        V(0, 0, params.floor_top() - params.THREAD_LENGTH),
        Z,
    )
    gap = floor_shape.common(belt).distToShape(dish)[0]
    clearance = params.THREAD_CLEARANCE
    if abs(gap - clearance) > GAP_TOLERANCE:
        errors.append(
            f"{FLOOR} ↔ {BOTTOM_DISH}: щель резьбы = зазору {clearance:g} мм"
            f" — {gap:.3f} мм",
        )
    return errors


# bodies → список ошибок, как в checks.py
CHECKS = [hangs_on_hook, thread_pair]


def build(doc):
    """Добавляет Дно и Держатель в doc, возвращает (тела, референсы)."""
    objects = []
    for label, shape in shapes().items():
        obj = doc.addObject("Part::Feature", "Floor")
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    return objects, []
