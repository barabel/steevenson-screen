import unittest
from unittest import mock

import FreeCAD
import Part

import scene
import skeleton
from checks import check
from skeleton import params

V = FreeCAD.Vector


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


def skeleton_errors(bodies):
    """Подставные тела → проверки Скелета."""
    errors = []
    for check_fn in skeleton.CHECKS:
        errors += check_fn(bodies)
    return errors


class SkeletonChecksTest(unittest.TestCase):
    """Проверки Скелета на подставных телах: тела → список ошибок."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

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
