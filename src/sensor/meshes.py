"""Меши-референсы Датчика из STL производителя — только для глаз.

Читаются как есть: в твёрдые тела не превращаются и не чинятся, res/ не меняется.
"""
from pathlib import Path

import Mesh

RES = Path(__file__).resolve().parents[2] / "res" / "pok005lv2"
FILES = [
    ("CaseBottom", "Корпус, нижняя половина", "pok5L-btm.stl"),
    ("CaseTop", "Корпус, верхняя половина", "pok5l-Top.stl"),
    ("Hanger", "Вешалка", "pok5l-Hook.stl"),
]


def load(doc):
    """Добавляет меши в doc как Mesh::Feature, возвращает их списком."""
    objects = []
    for name, label, file_name in FILES:
        obj = doc.addObject("Mesh::Feature", name)
        obj.Label = label
        obj.Mesh = Mesh.Mesh(str(RES / file_name))
        objects.append(obj)
    return objects
