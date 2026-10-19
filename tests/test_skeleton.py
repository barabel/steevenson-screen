import unittest
from unittest import mock

import FreeCAD
import Part

import scene
import skeleton
from checks import check
from skeleton import params

V = FreeCAD.Vector


def box(x):
    return Part.makeBox(10, 10, 10, V(x, 0, 0))


def skeleton_errors(bodies):
    """Подставные тела → проверки Скелета."""
    errors = []
    for check_fn in skeleton.CHECKS:
        errors += check_fn(bodies)
    return errors


def scene_errors():
    """Сцена из параметров Скелета → тела → все проверки, без build.cmd."""
    doc = FreeCAD.newDocument("skeleton_test")
    try:
        body_objects, _ = scene.build(doc)
        doc.recompute()
        bodies = {}
        for obj in body_objects:
            bodies[obj.Label] = obj.Shape
        errors = check(bodies)
        for check_fn in scene.checks():
            errors += check_fn(bodies)
        return errors
    finally:
        FreeCAD.closeDocument(doc.Name)


class SkeletonTest(unittest.TestCase):
    """Скелет из параметров: подмена параметров → тела → список ошибок."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_body_5_mm_from_plug_breaks_gap(self):
        errors = skeleton_errors({"Заглушка": box(0), "Тарелка 3": box(15)})

        self.assertError(errors, "Заглушка", "зазор", "Тарелка 3", "5.00 мм")

    def test_body_at_min_gap_within_float_noise_is_not_a_gap_error(self):
        errors = skeleton_errors({"Заглушка": box(0), "Дно": box(20 - 1e-6)})

        self.assertEqual(errors, [])

    def test_holder_touching_plug_is_not_a_gap_error(self):
        errors = skeleton_errors({"Заглушка": box(0), "Держатель": box(10)})

        self.assertEqual(errors, [])

    def test_two_dishes_fewer_break_plug_gap(self):
        with mock.patch.dict(vars(params), {"DISH_COUNT": params.DISH_COUNT - 2}):
            errors = scene_errors()

        self.assertError(errors, "Заглушка", "зазор", "мм")

    def test_skeleton_from_params_has_no_errors(self):
        cases = {
            "по умолчанию": {},
            "Ø 120": {"DISH_DIAMETER": 120},
            "N + 1": {"DISH_COUNT": params.DISH_COUNT + 1},
        }
        for name, changes in cases.items():
            with self.subTest(name):
                with mock.patch.dict(vars(params), changes):
                    errors = scene_errors()

                self.assertEqual(errors, [])

    def test_smaller_dish_gives_shorter_bracket_reach(self):
        reach = params.bracket_reach()
        with mock.patch.dict(vars(params), {"DISH_DIAMETER": 120}):
            self.assertLess(params.bracket_reach(), reach)

    def test_holder_wider_than_bottom_dish_hole(self):
        ring = Part.makeCylinder(40, 5).cut(Part.makeCylinder(30, 5))
        bodies = {
            "Нижняя Тарелка": ring,
            "Дно": Part.makeCylinder(25, 5),
            "Держатель": Part.makeBox(70, 4, 10, V(-35, -2, 10)),
            "Заглушка": Part.makeBox(10, 10, 10, V(-5, -5, 20)),
        }

        errors = skeleton_errors(bodies)

        self.assertError(errors, "выход вниз", "Нижняя Тарелка")
