"""Кронштейн Щита; проверки Кронштейна.

Размеры — из Скелета. Строит тело под той же меткой, что была у Черновика
Кронштейна в Скелете.
"""
import FreeCAD
import Part

from skeleton import params

V = FreeCAD.Vector

BRACKET = "Кронштейн"


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


def shapes():
    """Кронштейн: метка → Shape."""
    return {
        BRACKET: bracket(),
    }


# bodies → список ошибок, как в checks.py
CHECKS = []


def build(doc):
    """Добавляет Кронштейн в doc, возвращает (тела, референсы).

    Пишет в лог вылет Кронштейна: по нему Кронштейн покупают.
    """
    print(f"вылет Кронштейна: {params.bracket_reach():g} мм", flush=True)
    objects = []
    for label, shape in shapes().items():
        obj = doc.addObject("Part::Feature", "Bracket")
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    return objects, []
