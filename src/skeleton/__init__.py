"""Скелет Щита: Черновики деталей из параметров Скелета, проверки Скелета.

Черновик — упрощённое тело детали под её меткой. Фаза детали убирает свой
Черновик отсюда и добавляет в сцену свой пакет с той же меткой.
"""
import math

import FreeCAD
import Part

from checks import MAX_OVERLAP
from sensor import PLUG
from sensor import params as sensor_params

from . import params

V = FreeCAD.Vector
X = V(1, 0, 0)
Z = V(0, 0, 1)

LID = "Крышка"
BOTTOM_DISH = "Нижняя Тарелка"
FLOOR = "Дно"
HOLDER = "Держатель"
BRACKET = "Кронштейн"


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


def floor():
    """Дно: цилиндр в резьбовом кольце по сердечнику наружной резьбы, без витков.

    Сердечник — впадины витков Дна с зазором резьбы: Черновик проходит
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


def holder():
    """Держатель: пластина на Дне за Корпусом, наверху Крючок через Ушко.

    Корпус опирается на пластину спиной. Крючок — прямой стержень, Ушко
    лежит на нём верхом отверстия; вылет — как у крючка Вешалки.
    """
    ear = params.sensor_shift()  # центр отверстия Ушка
    face = ear.x + sensor_params.CASE_X  # спина Корпуса
    rod = sensor_params.HANGER_ROD_DIAMETER / 2
    rod_z = ear.z + sensor_params.EAR_INNER_DIAMETER / 2 - rod
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
        thickness + sensor_params.HANGER_REACH - sensor_params.HANGER_PLATE_THICKNESS,
        V(face - thickness, 0, rod_z),
        X,
    )
    return plate.fuse(hook).removeSplitter()


def bracket():
    """Кронштейн: пластина на плоскости Откоса и консоль над Точкой подвеса.

    Консоль — на высоте проставки, за ось Щита на половину своей ширины.
    """
    jamb = params.jamb_x()
    arm_top = params.SPACER_HEIGHT + params.BRACKET_ARM_THICKNESS
    plate = Part.makeBox(
        params.BRACKET_PLATE_THICKNESS,
        params.BRACKET_PLATE_WIDTH,
        params.BRACKET_PLATE_HEIGHT,
        V(
            jamb,
            -params.BRACKET_PLATE_WIDTH / 2,
            arm_top - params.BRACKET_PLATE_HEIGHT,
        ),
    )
    arm = Part.makeBox(
        params.bracket_reach() + params.BRACKET_ARM_WIDTH / 2,
        params.BRACKET_ARM_WIDTH,
        params.BRACKET_ARM_THICKNESS,
        V(jamb, -params.BRACKET_ARM_WIDTH / 2, params.SPACER_HEIGHT),
    )
    return plate.fuse(arm).removeSplitter()


def drafts():
    """Черновики: метка → Shape — Дно, Держатель, Кронштейн."""
    return {
        FLOOR: floor(),
        HOLDER: holder(),
        BRACKET: bracket(),
    }


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
    """Добавляет Черновики в doc, возвращает (тела, референсы).

    Пишет в лог вылет Кронштейна: по нему Кронштейн покупают.
    """
    print(f"вылет Кронштейна: {params.bracket_reach():g} мм", flush=True)
    objects = []
    for label, shape in drafts().items():
        obj = doc.addObject("Part::Feature", "Draft")
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    return objects, []
