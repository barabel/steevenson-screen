"""Кронштейн Щита: Уголок и Поворот, Проставка под плечом; проверки Кронштейна.

Размеры — из Скелета. Плоскость Откоса — x = −JAMB_SHIFT, проём — с её
стороны −X. Фасад — плоскость y = facade_to_axis(), рама — дальше по +Y.

Поворот — стойкой вверх: стойка по плоскости Откоса со стороны Щита, плечо
внизу, над Крышкой на высоте проставки, от плоскости Откоса к +X за ось Щита.
Уголок — вдоль плоскости Откоса со стороны проёма: от рамы минус отступ до
дальней от Фасада грани стойки, низ его вертикальной полки — на уровне верха
плеча. Стойка касается вертикальной полки Уголка по плоскости Откоса.
Проставка — между верхом Крышки и плечом, плечо лежит в её пазу.
"""
import FreeCAD
import Part

from skeleton import BEYOND, params

V = FreeCAD.Vector
Z = V(0, 0, 1)

ANGLE = "Уголок"
TURN = "Поворот"
SPACER = "Проставка"


def arm_top():
    """Z верха плеча Поворота: низ плеча — на высоте проставки над Точкой подвеса."""
    return params.SPACER_HEIGHT + params.TURN_THICKNESS


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
    return vertical.fuse(horizontal).removeSplitter()


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
    return post.fuse(arm).removeSplitter().cut(hole)


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


# bodies → список ошибок, как в checks.py; проверки Кронштейна — сюда
CHECKS = []


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
