import unittest
from unittest import mock

import FreeCAD

import scene
from checks import check
from skeleton import params


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
