import unittest

import FreeCAD
import Part

import bracket
from skeleton import params

V = FreeCAD.Vector


def bracket_errors(bodies):
    """Подставные тела → проверки Кронштейна."""
    errors = []
    for check_fn in bracket.CHECKS:
        errors += check_fn(bodies)
    return errors


class NutsInCornerTest(unittest.TestCase):
    """Гайки в углу: места гаек M6 Поворот↔Уголок у стойки свободны."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_solid_gusset_in_corner_takes_nut_place(self):
        # сплошная косынка 40×40 во внутреннем углу над плечом
        post_inside = -params.JAMB_SHIFT + params.TURN_THICKNESS
        gusset = Part.makeBox(
            40,
            params.TURN_WIDTH,
            40,
            V(post_inside, -params.TURN_WIDTH / 2, bracket.arm_top()),
        )
        bodies = {
            "Уголок": bracket.angle(),
            "Поворот": bracket.turn().fuse(gusset).removeSplitter(),
        }

        errors = bracket_errors(bodies)

        self.assertError(errors, "Поворот", "гайка", "мм³")

    def test_nut_check_is_silent_without_turn(self):
        cases = {
            "нет Поворота": {"Уголок": bracket.angle()},
            "Поворот null": {"Уголок": bracket.angle(), "Поворот": Part.Shape()},
        }
        for name, bodies in cases.items():
            with self.subTest(name):
                self.assertEqual(bracket_errors(bodies), [])
