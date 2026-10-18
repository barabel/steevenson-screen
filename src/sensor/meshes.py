"""Меши-референсы Датчика из STL производителя — только для глаз.

Читаются как есть: в твёрдые тела не превращаются и не чинятся, res/ не меняется.
В позу висения (систему координат Датчика, см. params) ставятся через Placement:
половины Корпуса свинчены, Вешалка зацеплена за Ушко.
"""
from pathlib import Path

import FreeCAD
import Mesh

from .params import SCREW_DEPTH

V = FreeCAD.Vector
Placement = FreeCAD.Placement
Rotation = FreeCAD.Rotation

RES = Path(__file__).resolve().parents[2] / "res" / "pok005lv2"

# Точки в координатах STL, замерены по мешам. Половины Корпуса лежат
# наружной гранью на z = 0, ось резьбы — по z; у нижней Ушко в +y, Носик в −y.
BOTTOM_AXIS = V(26.036, 116.354, 0)  # ось резьбы нижней половины
BOTTOM_RIM = 9.6  # торец стенки нижней половины
EYE = V(26.036, 146.354, 1.5)  # центр отверстия Ушка: Ø6, Ушко z 0..3
TOP_AXIS = V(51.448, 172.003, 0)  # ось резьбы верхней половины
TOP_END = 13.0  # торец резьбы верхней половины
# Точка Вешалки, которая приходит в центр отверстия Ушка: x — ось стержня,
# y — верх стержня в месте опоры Ушка минус радиус отверстия, z — середина
# Ушка. Пластина z 0..1, стержень торчит по z и загибается в +y.
HANGER_REST = V(10.648, 170.33, 3.0)

# STL → поза висения: z (ось резьбы) → X, y (к Ушку) → Z, x → Y.
POSE = Rotation(V(1, 1, 1), 120)


def moved(point, rotation=Rotation()):
    """Placement: point — в начало координат, затем поворот rotation."""
    return Placement(V(), rotation).multiply(Placement(point * -1, Rotation()))


def screwed_top():
    """Верхняя половина в координатах STL нижней: перевёрнута, на её оси,
    торец резьбы на SCREW_DEPTH ниже торца стенки нижней. Поворот вокруг оси —
    тот, при котором витки не пересекаются."""
    end = V(BOTTOM_AXIS.x, BOTTOM_AXIS.y, BOTTOM_RIM - SCREW_DEPTH)
    flip = Rotation(V(1, 0, 0), 180)
    return Placement(end, Rotation()).multiply(moved(TOP_AXIS + V(0, 0, TOP_END), flip))


FILES = [
    ("CaseBottom", "Корпус, нижняя половина", "pok5L-btm.stl", moved(EYE, POSE)),
    (
        "CaseTop",
        "Корпус, верхняя половина",
        "pok5l-Top.stl",
        moved(EYE, POSE).multiply(screwed_top()),
    ),
    ("Hanger", "Вешалка", "pok5l-Hook.stl", moved(HANGER_REST, POSE)),
]


def load(doc):
    """Добавляет меши в doc как Mesh::Feature в позе висения, возвращает списком."""
    objects = []
    for name, label, file_name, placement in FILES:
        obj = doc.addObject("Mesh::Feature", name)
        obj.Label = label
        obj.Mesh = Mesh.Mesh(str(RES / file_name))
        obj.Placement = placement
        objects.append(obj)
    return objects
