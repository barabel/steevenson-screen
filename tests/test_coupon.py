import unittest
from unittest import mock

import FreeCAD
import Part

import coupon
import skeleton
from checks import check
from coupon import params


def coupon_bodies():
    """Пробник из параметров → тела по меткам, без build.cmd."""
    doc = FreeCAD.newDocument("coupon_test")
    try:
        objects = coupon.build(doc)
        doc.recompute()
        bodies = {}
        for obj in objects:
            bodies[obj.Label] = obj.Shape
        return bodies
    finally:
        FreeCAD.closeDocument(doc.Name)


def coupon_errors(bodies):
    """Тела → проверки фазы 0 и проверки Пробника."""
    errors = check(bodies)
    for check_fn in coupon.CHECKS:
        errors += check_fn(bodies)
    return errors


class CouponTest(unittest.TestCase):
    """Пробник: подмена параметров или тел → список ошибок."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_coupon_from_params_has_no_errors(self):
        errors = coupon_errors(coupon_bodies())

        self.assertEqual(errors, [])

    def test_coupon_of_other_diameter_and_pitch_has_no_errors(self):
        with mock.patch.dict(vars(skeleton.params), {"THREAD_DIAMETER": 60, "THREAD_PITCH": 4}):
            errors = coupon_errors(coupon_bodies())

        self.assertEqual(errors, [])

    def test_negative_clearance_breaks_pair_by_overlap(self):
        with mock.patch.dict(vars(params), {"CLEARANCES": [-0.3]}):
            errors = coupon_errors(coupon_bodies())

        self.assertError(errors, "Кольцо Дна -0.3", "Кольцо Тарелки", "пересечение", "мм³")

    def test_bed_smaller_than_layout_breaks_bed(self):
        with mock.patch.dict(vars(params), {"BED": (150, 150, 10)}):
            errors = coupon.bed(coupon_bodies())

        self.assertError(errors, "стол", "150 × 150 × 10 мм")

    def test_smooth_floor_ring_with_wrong_gap_breaks_pair_gap(self):
        bodies = coupon_bodies()
        # гладкий цилиндр Ø86 в вершинах кольца Тарелки Ø87: щель 0.5, а не 0.4
        bodies["Кольцо Дна 0.4"] = Part.makeCylinder(43, 15)

        errors = coupon.pair(bodies)

        self.assertError(errors, "Кольцо Дна 0.4", "Кольцо Тарелки", "зазор", "0.500 мм")

    def test_floor_ring_offset_by_geometry_screws_in_coaxially(self):
        bodies = coupon_bodies()
        # гладкий цилиндр Ø86.2 в вершинах Ø87: щель 0.4; сдвинут геометрией, Placement нулевой
        bodies["Кольцо Дна 0.4"] = Part.makeCylinder(43.1, 15, FreeCAD.Vector(150, 50, 0))

        errors = coupon.pair(bodies)

        self.assertEqual(errors, [])
