import unittest
from unittest import mock

import FreeCAD
import Part

from skeleton import params
from test_skeleton import scene_errors, stack_errors

V = FreeCAD.Vector


def plug():
    return Part.makeBox(10, 10, 10, V(-5, -5, -5))


def closed_box():
    """Коробка со стенкой 2 вокруг plug(), внутри воздух 10 мм."""
    outer = Part.makeBox(34, 34, 34, V(-17, -17, -17))
    inner = Part.makeBox(30, 30, 30, V(-15, -15, -15))
    return outer.cut(inner)


class ShadowTest(unittest.TestCase):
    """Проверка тени: тела → ошибки; параметры Скелета → сцена → ошибки."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_plug_alone_is_in_sun(self):
        errors = stack_errors({"Заглушка": plug()})

        self.assertError(errors, "Заглушка", "тень", "°")

    def test_plug_in_closed_box_is_in_shadow(self):
        errors = stack_errors({"Заглушка": plug(), "Коробка": closed_box()})

        self.assertEqual(errors, [])

    def test_hang_bolt_hole_over_plug_is_closed_by_nut(self):
        # верх коробки — в Точке подвеса, сквозь него отверстие болта M6;
        # гайка с болтом в гнезде под верхом закрывают его
        lid = Part.makeBox(34, 34, 34, V(-17, -17, -34)).cut(
            Part.makeBox(30, 30, 30, V(-15, -15, -32)),
        )
        hole = Part.makeCylinder(3.25, 4, V(0, 0, -3))
        bodies = {
            "Заглушка": Part.makeBox(10, 10, 5, V(-5, -5, -30)),
            "Коробка": lid.cut(hole),
        }

        self.assertEqual(stack_errors(bodies), [])

    def test_no_plug_is_silent(self):
        cases = {
            "нет Заглушки": {"Коробка": closed_box()},
            "Заглушка null": {"Заглушка": Part.Shape()},
        }
        for name, bodies in cases.items():
            with self.subTest(name):
                self.assertEqual(stack_errors(bodies), [])

    def test_pitch_30_lets_sun_onto_plug(self):
        with mock.patch.dict(vars(params), {"DISH_PITCH": 30}):
            errors = scene_errors()

        self.assertError(errors, "Заглушка", "тень", "°")
