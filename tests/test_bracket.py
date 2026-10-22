import unittest
from unittest import mock

import FreeCAD
import Part

import bracket
from skeleton import params
from test_skeleton import scene_errors

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


class WrenchTest(unittest.TestCase):
    """Ключ к болту подвеса: над плечом вокруг оси Щита пусто."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_body_over_hang_point_blocks_wrench(self):
        # кубик 10 мм на оси Щита, в 5 мм над верхом плеча
        bodies = {
            "Поворот": Part.makeBox(10, 10, 10, V(-5, -5, bracket.arm_top() + 5)),
        }

        errors = bracket_errors(bodies)

        self.assertError(errors, "Поворот", "ключ", "болт подвеса", "мм³")

    def test_wrench_check_is_silent_without_bracket_bodies(self):
        cases = {
            "нет тел": {},
            "Уголок и Поворот null": {"Уголок": Part.Shape(), "Поворот": Part.Shape()},
        }
        for name, bodies in cases.items():
            with self.subTest(name):
                self.assertEqual(bracket_errors(bodies), [])

    def test_brace_landing_90_mm_from_jamb_blocks_wrench(self):
        # до оси Щита 10 мм: подкос заходит в зону ключа r25
        with mock.patch.dict(vars(params), {"BRACE_ARM_REACH": 90}):
            errors = scene_errors()

        self.assertError(errors, "Поворот", "ключ", "болт подвеса")

    def test_brace_landing_75_mm_from_jamb_only_touches_wrench_zone(self):
        with mock.patch.dict(vars(params), {"BRACE_ARM_REACH": 75}):
            errors = scene_errors()

        wrench_errors = []
        for error in errors:
            if "ключ" in error:
                wrench_errors.append(error)
        self.assertEqual(wrench_errors, [])
