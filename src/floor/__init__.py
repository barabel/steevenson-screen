"""Дно и Держатель Щита; проверки Дна и Держателя.

Метки и размеры — из Скелета. Строит тела под теми же метками, что были
у Черновиков Дна и Держателя в Скелете.
"""
import FreeCAD
import Part

from sensor import params as sensor_params
from skeleton import FLOOR, HOLDER, params

V = FreeCAD.Vector
X = V(1, 0, 0)
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


def shapes():
    """Дно и Держатель: метка → Shape."""
    return {
        FLOOR: floor(),
        HOLDER: holder(),
    }


# bodies → список ошибок, как в checks.py
CHECKS = []


def build(doc):
    """Добавляет Дно и Держатель в doc, возвращает (тела, референсы)."""
    objects = []
    for label, shape in shapes().items():
        obj = doc.addObject("Part::Feature", "Floor")
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    return objects, []
