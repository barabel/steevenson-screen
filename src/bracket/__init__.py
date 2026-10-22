"""Кронштейн Щита: Уголок и Поворот; проверки Кронштейна.

Размеры — из Скелета. Плоскость Откоса — x = −JAMB_SHIFT, проём — с её
стороны −X. Фасад — плоскость y = facade_to_axis(), рама — дальше по +Y.

Поворот — стойкой вверх: стойка по плоскости Откоса со стороны Щита, плечо
внизу, над Крышкой на высоте проставки, от плоскости Откоса к +X за ось Щита.
Уголок — вдоль плоскости Откоса со стороны проёма: от рамы минус отступ до
дальней от Фасада грани стойки, низ его вертикальной полки — на уровне верха
плеча. Стойка касается вертикальной полки Уголка по плоскости Откоса.
"""
import FreeCAD
import Part

from checks import GAP_TOLERANCE, MAX_OVERLAP
from skeleton import params

V = FreeCAD.Vector
X = V(1, 0, 0)
Z = V(0, 0, 1)
BEYOND = 1  # вырез выходит за грани тела: без совпадающих граней

ANGLE = "Уголок"
TURN = "Поворот"


def arm_top():
    """Z верха плеча Поворота: низ плеча — на высоте проставки над Точкой подвеса."""
    return params.SPACER_HEIGHT + params.TURN_THICKNESS


def bolt_holes():
    """Отверстия под болты M6 Поворот↔Уголок: сквозь вертикальную полку Уголка и стойку."""
    start = -params.JAMB_SHIFT - params.ANGLE_THICKNESS - BEYOND
    depth = params.ANGLE_THICKNESS + params.TURN_THICKNESS + 2 * BEYOND
    holes = []
    for height in params.TURN_BOLT_HEIGHTS:
        holes.append(
            Part.makeCylinder(
                params.TURN_BOLT_DIAMETER / 2,
                depth,
                V(start, 0, arm_top() + height),
                X,
            ),
        )
    return holes


def nut_places():
    """Места гаек с шайбами болтов Поворот↔Уголок: от внутренней стороны стойки к +X."""
    inside = -params.JAMB_SHIFT + params.TURN_THICKNESS
    places = []
    for height in params.TURN_BOLT_HEIGHTS:
        places.append(
            Part.makeCylinder(
                params.TURN_NUT_PLACE_DIAMETER / 2,
                params.TURN_NUT_PLACE_DEPTH,
                V(inside, 0, arm_top() + height),
                X,
            ),
        )
    return places


def angle():
    """Уголок: профиль L, вытянутый по Y.

    Вертикальная полка — со стороны проёма, касается плоскости Откоса,
    горизонтальная — сверху, к −X.
    """
    jamb = -params.JAMB_SHIFT
    start = -params.TURN_WIDTH / 2
    length = params.angle_length()
    leg = params.ANGLE_LEG
    thickness = params.ANGLE_THICKNESS
    bottom = arm_top()
    vertical = Part.makeBox(
        thickness,
        length,
        leg,
        V(jamb - thickness, start, bottom),
    )
    horizontal = Part.makeBox(
        leg,
        length,
        thickness,
        V(jamb - leg, start, bottom + leg - thickness),
    )
    angle_shape = vertical.fuse(horizontal).removeSplitter()
    return angle_shape.cut(bolt_holes())


def turn():
    """Поворот: стойка вверх от плеча, плечо — по центру оси Щита по Y.

    В плече — отверстие под болт подвеса по оси Щита, с зазором как у
    отверстия в Крышке.
    """
    jamb = -params.JAMB_SHIFT
    width = params.TURN_WIDTH
    thickness = params.TURN_THICKNESS
    bottom = params.SPACER_HEIGHT
    post = Part.makeBox(
        thickness,
        width,
        params.TURN_POST_HEIGHT,
        V(jamb, -width / 2, bottom),
    )
    arm = Part.makeBox(
        params.TURN_ARM_LENGTH,
        width,
        thickness,
        V(jamb, -width / 2, bottom),
    )
    hole = Part.makeCylinder(
        params.HANG_BOLT_DIAMETER / 2 + params.HANG_CLEARANCE,
        thickness,
        V(0, 0, bottom),
        Z,
    )
    turn_shape = post.fuse(arm).removeSplitter().cut(hole)
    return turn_shape.cut(bolt_holes())


def shapes():
    """Тела Кронштейна: метка → Shape."""
    return {
        ANGLE: angle(),
        TURN: turn(),
    }


def beside_shield(bodies):
    """Сбоку от Щита пусто: низ Уголка и Поворота не ниже низа плеча."""
    errors = []
    for name in (ANGLE, TURN):
        shape = bodies.get(name)
        if shape is None or shape.isNull():
            continue
        depth = params.SPACER_HEIGHT - shape.BoundBox.ZMin
        if depth > GAP_TOLERANCE:
            errors.append(
                f"{name}: сбоку от Щита пусто"
                f" — на {depth:.2f} мм ниже низа плеча",
            )
    return errors


def nuts_in_corner(bodies):
    """Гайки в углу: место каждой гайки болтов Поворот↔Уголок свободно от Поворота и Уголка.

    Нет Поворота или он null — молчит.
    """
    turn_shape = bodies.get(TURN)
    if turn_shape is None or turn_shape.isNull():
        return []
    errors = []
    for number, place in enumerate(nut_places(), 1):
        for name in (TURN, ANGLE):
            shape = bodies.get(name)
            if shape is None or shape.isNull():
                continue
            hit = shape.common(place)
            volume = 0 if hit.isNull() else hit.Volume  # мимо — null
            if volume > MAX_OVERLAP:
                errors.append(
                    f"{name}: гайка {number} снизу болта {TURN}↔{ANGLE}"
                    f" не встаёт в угол — в её месте {volume:.1f} мм³",
                )
    return errors


# bodies → список ошибок, как в checks.py; проверки Кронштейна — сюда
CHECKS = [
    nuts_in_corner,
    beside_shield,
]


def build(doc):
    """Добавляет Уголок и Поворот в doc, возвращает (тела, референсы).

    Пишет в лог длину Уголка и расстояние от плоскости Откоса до болта
    подвеса на Повороте: по ним Кронштейн покупают.
    """
    print(
        f"длина Уголка: {params.angle_length():g} мм,"
        f" от плоскости Откоса до болта подвеса: {params.JAMB_SHIFT:g} мм",
        flush=True,
    )
    objects = []
    for label, shape in shapes().items():
        obj = doc.addObject("Part::Feature", "Bracket")
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    return objects, []
