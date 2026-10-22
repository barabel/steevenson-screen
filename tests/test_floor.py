import unittest

import FreeCAD
import Part

import floor

V = FreeCAD.Vector


def floor_errors(bodies):
    """Подставные тела → проверки Дна и Держателя."""
    errors = []
    for check_fn in floor.CHECKS:
        errors += check_fn(bodies)
    return errors


class FloorTest(unittest.TestCase):
    """Проверки Дна и Держателя на подставных телах: тела → список ошибок."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_holder_away_from_ear_hole_does_not_hang_plug(self):
        bodies = {
            "Заглушка": Part.makeBox(10, 10, 10),
            "Держатель": Part.makeBox(10, 10, 10, V(500, 500, 500)),
        }

        errors = floor_errors(bodies)

        self.assertError(errors, "Крючок", "Ушко")

    def test_hook_check_is_silent_without_plug_or_holder(self):
        away = Part.makeBox(10, 10, 10, V(500, 500, 500))
        cases = {
            "нет Заглушки": {"Держатель": away},
            "нет Держателя": {"Заглушка": away},
        }
        for name, bodies in cases.items():
            with self.subTest(name):
                self.assertEqual(floor_errors(bodies), [])
