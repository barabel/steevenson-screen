"""Дно и Держатель Щита; проверки Дна и Держателя.

Метки и размеры — из Скелета. Строит тела под теми же метками, что были
у Черновиков Дна и Держателя в Скелете.
"""
import math

import FreeCAD
import Part

import thread
from sensor import params as sensor_params
from skeleton import BEYOND, FLOOR, HOLDER, params, revolved

V = FreeCAD.Vector
X = V(1, 0, 0)
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
    резьбовым кольцом с зазором, его не касается: второго упора нет.
    """
    diameter = params.THREAD_DIAMETER
    length = params.THREAD_LENGTH
    clearance = params.THREAD_CLEARANCE
    bottom = params.floor_top() - length
    root = diameter / 2 - params.THREAD_DEPTH - clearance
    low = bottom - params.FLOOR_GRIP_GAP - params.FLOOR_GRIP_HEIGHT
    bore = Part.makeCylinder(
        root - params.THREAD_RING_WALL,
        params.floor_top() - params.FLOOR_DISK_THICKNESS - low + BEYOND,
        V(0, 0, low - BEYOND),
        Z,
    )
    sleeve = thread.external(diameter, length, clearance).translated(V(0, 0, bottom))
    return sleeve.fuse(grip(bottom, root)).cut(bore)


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
