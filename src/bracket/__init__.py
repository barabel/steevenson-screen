"""Кронштейн Щита: Уголок и Поворот, Проставка под плечом; проверки Кронштейна.

Размеры — из Скелета. Плоскость Откоса — x = −JAMB_SHIFT, проём — с её
стороны −X. Фасад — плоскость y = facade_to_axis(), рама — дальше по +Y.

Поворот — стойкой вверх: стойка по плоскости Откоса со стороны Щита, плечо
внизу, над Крышкой на высоте Проставки, от плоскости Откоса к +X за ось Щита.
Уголок — вдоль плоскости Откоса со стороны проёма: от рамы минус отступ до
дальней от Фасада грани стойки, низ его вертикальной полки — на уровне верха
плеча. Стойка касается вертикальной полки Уголка по плоскости Откоса.
Проставка — между верхом Крышки и плечом, плечо лежит в её пазу.
"""
import math

import FreeCAD
import Part

from checks import GAP_TOLERANCE, MAX_OVERLAP
from skeleton import BEYOND, params

V = FreeCAD.Vector
X = V(1, 0, 0)
Z = V(0, 0, 1)

ANGLE = "Уголок"
TURN = "Поворот"
SPACER = "Проставка"


def arm_top():
    """Z верха плеча Поворота: низ плеча — на высоте Проставки над Точкой подвеса."""
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


def brace():
    """Подкос: полоса во внутреннем углу Поворота, от стойки к плечу.

    Наружный край — от внутренней грани стойки на BRACE_POST_RISE над верхом
    плеча до плеча в BRACE_ARM_REACH от плоскости Откоса; внутренний — к углу,
    на толщину полосы. Подкос касается стойки и плеча гранями.
    """
    jamb = -params.JAMB_SHIFT
    post_face = jamb + params.TURN_THICKNESS
    bottom = arm_top()
    top = bottom + params.BRACE_POST_RISE
    foot = jamb + params.BRACE_ARM_REACH
    run = foot - post_face
    rise = params.BRACE_POST_RISE
    slant = math.hypot(run, rise)
    thickness = params.BRACE_THICKNESS
    y = -params.BRACE_WIDTH / 2
    outline = Part.makePolygon([
        V(post_face, y, top),
        V(foot, y, bottom),
        V(foot - thickness * slant / rise, y, bottom),
        V(post_face, y, top - thickness * slant / run),
        V(post_face, y, top),
    ])
    return Part.Face(outline).extrude(V(0, params.BRACE_WIDTH, 0))


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
    turn_shape = post.fuse(arm).removeSplitter().fuse(brace()).removeSplitter().cut(hole)
    return turn_shape.cut(bolt_holes())


def spacer():
    """Проставка: цилиндр от верха Крышки до дна паза и стенки паза выше.

    Плечо Поворота лежит на дне паза, стенки — по бокам плеча: Проставка
    не проворачивается под ним. Отверстие под болт подвеса — по оси Щита.
    Печать низом на стол, паз сверху: стенки растут от дна, нависаний нет.
    """
    clearance = params.HANG_CLEARANCE
    radius = params.SPACER_DIAMETER / 2
    height = params.SPACER_HEIGHT + params.SPACER_WALL_HEIGHT
    slot_width = params.TURN_WIDTH + 2 * clearance
    body = Part.makeCylinder(radius, height, V(0, 0, 0), Z)
    slot = Part.makeBox(
        2 * (radius + BEYOND),
        slot_width,
        params.SPACER_WALL_HEIGHT + BEYOND,
        V(-radius - BEYOND, -slot_width / 2, params.SPACER_HEIGHT),
    )
    hole = Part.makeCylinder(
        params.HANG_BOLT_DIAMETER / 2 + clearance,
        height + 2 * BEYOND,
        V(0, 0, -BEYOND),
        Z,
    )
    return body.cut(slot).cut(hole).removeSplitter()


def shapes():
    """Тела Кронштейна: метка → Shape."""
    return {
        ANGLE: angle(),
        TURN: turn(),
        SPACER: spacer(),
    }


def angle_and_turn(bodies):
    """Уголок и Поворот из bodies, кроме отсутствующих и null: список (метка, Shape)."""
    result = []
    for name in (ANGLE, TURN):
        shape = bodies.get(name)
        if shape is not None and not shape.isNull():
            result.append((name, shape))
    return result


def beside_shield(bodies):
    """Сбоку от Щита пусто: низ Уголка и Поворота не ниже низа плеча."""
    errors = []
    for name, shape in angle_and_turn(bodies):
        depth = params.SPACER_HEIGHT - shape.BoundBox.ZMin
        if depth > GAP_TOLERANCE:
            errors.append(
                f"{name}: сбоку от Щита — на {depth:.2f} мм ниже низа плеча",
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
        for name, shape in angle_and_turn(bodies):
            hit = shape.common(place)
            volume = 0 if hit.isNull() else hit.Volume  # мимо — null
            if volume > MAX_OVERLAP:
                errors.append(
                    f"{name}: гайка {number} снизу болта {TURN}↔{ANGLE}"
                    f" не встаёт в угол — в её месте {volume:.1f} мм³",
                )
    return errors


def wrench_reaches_bolt(bodies):
    """Ключ к болту: зона ключа над плечом не пересекается с Уголком и Поворотом.

    Зона — цилиндр вокруг оси Щита от верха плеча вверх. Плечо касается её
    снизу, подкос на пределе — по границе: это не пересечение. Нет тела или
    оно null — молчит.
    """
    zone = Part.makeCylinder(
        params.WRENCH_RADIUS,
        params.WRENCH_HEIGHT,
        V(0, 0, arm_top()),
        Z,
    )
    errors = []
    for name, shape in angle_and_turn(bodies):
        hit = shape.common(zone)
        volume = 0 if hit.isNull() else hit.Volume  # мимо — null
        if volume > MAX_OVERLAP:
            errors.append(
                f"{name}: закрывает болт подвеса, ключ не подлезет"
                f" — в зоне ключа r{params.WRENCH_RADIUS:g} {volume:.2f} мм³",
            )
    return errors


# bodies → список ошибок, как в checks.py; проверки Кронштейна — сюда
CHECKS = [
    nuts_in_corner,
    beside_shield,
    wrench_reaches_bolt,
]


def build(doc):
    """Добавляет Уголок, Поворот и Проставку в doc, возвращает (тела, референсы).

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
