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


class BesideShieldTest(unittest.TestCase):
    """Проверка «сбоку от Щита пусто» на подставных телах."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_turn_with_post_down_is_beside_shield(self):
        # переворот вокруг оси плеча: стойка 150 мм уходит вниз,
        # её низ — на 150 − 4 (толщина плеча) = 146 мм ниже низа плеча
        center = V(0, 0, params.SPACER_HEIGHT + params.TURN_THICKNESS / 2)
        post_down = bracket.turn()
        post_down.rotate(center, V(1, 0, 0), 180)
        bodies = {"Поворот": post_down}

        errors = bracket_errors(bodies)

        self.assertError(errors, "Поворот", "сбоку от Щита", "146.00 мм")

    def test_beside_shield_is_silent_without_angle_and_turn(self):
        cases = {
            "нет Уголка и Поворота": {},
            "тела null": {"Уголок": Part.Shape(), "Поворот": Part.Shape()},
        }
        for name, bodies in cases.items():
            with self.subTest(name):
                self.assertEqual(bracket_errors(bodies), [])

    def test_bracket_from_params_is_not_beside_shield(self):
        errors = bracket_errors(bracket.shapes())

        self.assertEqual(errors, [])
