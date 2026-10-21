import math
import unittest
from unittest import mock

import FreeCAD
import Part

import scene
import skeleton
import stack
from checks import MAX_OVERLAP, check
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

    def test_lid_5_mm_above_holder_breaks_hook_gap(self):
        errors = skeleton_errors({
            "Держатель": box(0),
            "Крышка": Part.makeBox(10, 10, 10, V(0, 0, 15)),
        })

        self.assertError(errors, "Держатель", "зазор", "Крышка", "5.00 мм")

    def test_two_dishes_fewer_break_plug_gap(self):
        with mock.patch.dict(vars(params), {"DISH_COUNT": params.DISH_COUNT - 2}):
            errors = scene_errors()

        self.assertError(errors, "Заглушка", "зазор", "мм")

    def test_standoffs_over_thread_ring_break_bottom_dish(self):
        with mock.patch.dict(vars(params), {"STANDOFF_RADIUS": 46}):
            errors = scene_errors()

        self.assertError(errors, "Нижняя Тарелка", "Стойки", "резьбовое кольцо")

    def test_standoffs_at_r53_put_washer_against_thread_ring(self):
        with mock.patch.dict(vars(params), {"STANDOFF_RADIUS": 53}):
            errors = scene_errors()

        self.assertError(errors, "Нижняя Тарелка", "шайба", "резьбовое кольцо", "мм")

    def test_skeleton_from_params_has_no_errors(self):
        cases = {
            "по умолчанию": {},
            "N + 1": {"DISH_COUNT": params.DISH_COUNT + 1},
            "Ø 160": {"DISH_DIAMETER": 160},
        }
        for name, changes in cases.items():
            with self.subTest(name):
                with mock.patch.dict(vars(params), changes):
                    errors = scene_errors()

                self.assertEqual(errors, [])

    def test_smaller_dish_gives_shorter_bracket_reach(self):
        reach = params.bracket_reach()
        with mock.patch.dict(vars(params), {"DISH_DIAMETER": 140}):
            self.assertLess(params.bracket_reach(), reach)

    def test_dish_140_breaks_shadow(self):
        with mock.patch.dict(vars(params), {"DISH_DIAMETER": 140}):
            errors = scene_errors()

        self.assertError(errors, "Заглушка", "тень")

    def test_shelf_wider_than_dish_names_diameter_and_shelf(self):
        with mock.patch.dict(vars(params), {"DISH_DIAMETER": 120}):
            with self.assertRaises(ValueError) as caught:
                scene_errors()

        message = str(caught.exception)
        for word in ["Ø", "120", "Полк", "62"]:
            self.assertIn(word, message)

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

    def test_dishes_5_mm_apart_break_clearance(self):
        bodies = {
            "Тарелка 2": Part.makeCylinder(70, 2),
            "Тарелка 3": Part.makeCylinder(70, 2, V(0, 0, -7)),
        }

        errors = []
        for check_fn in stack.CHECKS:
            errors += check_fn(bodies)

        self.assertError(errors, "просвет", "Тарелка 2", "Тарелка 3", "5.00 мм")

    def test_lid_takes_m6_nut_from_below_under_5_mm_of_plastic(self):
        lid = stack.lid()
        # гайка M6: под ключ 10, высота 5; верх — на 5 мм под Точкой подвеса
        corner = 5 / math.cos(math.radians(30))
        corners = []
        for i in range(7):
            angle = math.radians(60 * i)
            corners.append(V(
                corner * math.cos(angle),
                corner * math.sin(angle),
                -10,
            ))
        nut = Part.Face(Part.makePolygon(corners)).extrude(V(0, 0, 5))
        bolt = Part.makeCylinder(3, 12, V(0, 0, -11))
        cover = Part.makeCylinder(5, 5, V(0, 0, -5)).cut(
            Part.makeCylinder(3.5, 5, V(0, 0, -5)),
        )

        self.assertLess(lid.common(nut.fuse(bolt)).Volume, MAX_OVERLAP)
        self.assertAlmostEqual(lid.common(cover).Volume, cover.Volume, places=2)

    def test_pitch_12_breaks_clearance(self):
        with mock.patch.dict(vars(params), {"DISH_PITCH": 12}):
            errors = scene_errors()

        self.assertError(errors, "просвет", "мм")

    def test_drip_8_mm_below_shelf_breaks_clearance(self):
        with mock.patch.dict(vars(params), {"DRIP_DROP": 8}):
            errors = scene_errors()

        # у Нижней Тарелки Полка до Ø отверстия, под низом Капельника: 16 − 2 − 8
        self.assertError(errors, "просвет", "Нижняя Тарелка", "6.00 мм")
