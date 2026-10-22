import unittest

import FreeCAD
import Part

import bracket
import stack
from checks import MAX_OVERLAP

V = FreeCAD.Vector


class SpacerTest(unittest.TestCase):
    """Узел подвеса: болт M6 по оси Щита сквозь плечо, Проставку и Крышку."""

    def test_hang_bolt_passes_arm_spacer_and_lid_to_nut(self):
        # болт M6: от верха плеча (проставка 20 + плечо 4) до низа гайки
        # в Крышке (верх гайки — на 5 мм под Точкой подвеса, высота 5)
        bolt = Part.makeCylinder(3, 34, V(0, 0, -10))
        bodies = {
            "Поворот": bracket.turn(),
            "Проставка": bracket.spacer(),
            "Крышка": stack.lid(),
        }

        for name, shape in bodies.items():
            with self.subTest(name):
                self.assertLess(shape.common(bolt).Volume, MAX_OVERLAP)

    def test_spacer_stands_on_lid_and_holds_arm_in_slot(self):
        # касания: сдвиг на 1 мм в сторону другого тела даёт пересечение
        spacer = bracket.spacer()
        lid = stack.lid()
        turn = bracket.turn()
        cases = {
            "Проставка на верху Крышки": (spacer, lid, V(0, 0, -1)),
            "плечо на дне паза": (turn, spacer, V(0, 0, -1)),
            "стенка паза сбоку плеча, +Y": (turn, spacer, V(0, 1, 0)),
            "стенка паза сбоку плеча, −Y": (turn, spacer, V(0, -1, 0)),
        }

        for name, (moved, other, shift) in cases.items():
            with self.subTest(name):
                self.assertLess(moved.common(other).Volume, MAX_OVERLAP)
                self.assertGreater(
                    moved.translated(shift).common(other).Volume,
                    MAX_OVERLAP,
                )
