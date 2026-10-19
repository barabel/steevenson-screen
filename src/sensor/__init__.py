"""Датчик POK005L: тела и референсы сцены, проверки Датчика.

Строится в своей системе координат (см. params), в Щит ставится переносом
из Скелета: одним и тем же для Заглушки и мешей.
"""
import FreeCAD
import Part

from . import meshes
from .params import (
    CASE_DIAMETER,
    CASE_THICKNESS,
    CASE_X,
    CASE_Z,
    EAR_INNER_DIAMETER,
    EAR_OUTER_DIAMETER,
    EAR_THICKNESS,
    EAR_X,
    NOSE_DIAMETER,
    NOSE_LENGTH,
    NOSE_X,
)

V = FreeCAD.Vector
X = V(1, 0, 0)
DOWN = V(0, 0, -1)

PLUG = "Заглушка"


def sensor_shift():
    """Перенос Датчика в Щит из Скелета.

    Импорт при вызове, не при загрузке: параметры Скелета читают параметры
    Датчика, импорт skeleton здесь замкнул бы цикл через sensor/__init__.
    """
    from skeleton import params as skeleton_params

    return skeleton_params.sensor_shift()


def plug():
    """Заглушка из параметров в Щите: диск Корпуса + Носик + Ушко, один solid."""
    case_radius = CASE_DIAMETER / 2
    case = Part.makeCylinder(case_radius, CASE_THICKNESS, V(CASE_X, 0, CASE_Z), X)
    # Носик начинается на оси диска: целиком врезан в диск, торчит из-под него
    nose = Part.makeCylinder(
        NOSE_DIAMETER / 2,
        case_radius + NOSE_LENGTH,
        V(NOSE_X, 0, CASE_Z),
        DOWN,
    )
    ear = Part.makeCylinder(
        EAR_OUTER_DIAMETER / 2,
        EAR_THICKNESS,
        V(EAR_X, 0, 0),
        X,
    )
    hole = Part.makeCylinder(
        EAR_INNER_DIAMETER / 2,
        EAR_THICKNESS,
        V(EAR_X, 0, 0),
        X,
    )
    shape = case.fuse([nose, ear.cut(hole)]).removeSplitter()
    return shape.translated(sensor_shift())


MAX_GABARIT_DELTA = 0.5  # мм


def gabarit(bodies):
    """Габарит Заглушки против габарита свинченных мешей Корпуса, по осям.
    Меши сдвинуты в Щит тем же переносом, что и Заглушка.

    Нет Заглушки или она null — молчит: это ловят тест Прогона и checks.valid.
    """
    shape = bodies.get(PLUG)
    if shape is None or shape.isNull():
        return []
    box = shape.BoundBox
    case = FreeCAD.BoundBox(meshes.case_box())  # копия: case_box в кэше
    case.move(sensor_shift())
    errors = []
    for axis in "XYZ":
        low = getattr(box, f"{axis}Min")
        high = getattr(box, f"{axis}Max")
        case_low = getattr(case, f"{axis}Min")
        case_high = getattr(case, f"{axis}Max")
        delta = max(abs(low - case_low), abs(high - case_high))
        if delta > MAX_GABARIT_DELTA:
            errors.append(
                f"{PLUG}: габарит по {axis} расходится с мешами Корпуса"
                f" на {delta:.2f} мм ({low:.2f}…{high:.2f}"
                f" против {case_low:.2f}…{case_high:.2f})",
            )
    return errors


CHECKS = [gabarit]  # bodies → список ошибок, как в checks.py


def build(doc):
    """Добавляет объекты Датчика в doc, возвращает (тела, референсы)."""
    obj = doc.addObject("Part::Feature", "Plug")
    obj.Label = PLUG
    obj.Shape = plug()
    return [obj], meshes.load(doc, sensor_shift())
