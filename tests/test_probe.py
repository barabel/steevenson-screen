import unittest
from unittest import mock

import FreeCAD
import Part

import probe
import skeleton
from checks import check
from probe import params


def probe_bodies():
    """Пробник из параметров → тела по меткам, без build.cmd."""
    doc = FreeCAD.newDocument("probe_test")
    try:
        objects = probe.build(doc)
        doc.recompute()
        bodies = {}
        for obj in objects:
            bodies[obj.Label] = obj.Shape
        return bodies
    finally:
        FreeCAD.closeDocument(doc.Name)


def probe_errors(bodies):
    """Тела → проверки фазы 0 и проверки Пробника."""
    errors = check(bodies)
    for check_fn in probe.CHECKS:
        errors += check_fn(bodies)
    return errors


class ProbeTest(unittest.TestCase):
    """Пробник: подмена параметров или тел → список ошибок."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_probe_from_params_has_no_errors(self):
        errors = probe_errors(probe_bodies())

        self.assertEqual(errors, [])

    def test_probe_of_other_diameter_and_pitch_has_no_errors(self):
        with mock.patch.dict(vars(skeleton.params), {"THREAD_DIAMETER": 60, "THREAD_PITCH": 4}):
            errors = probe_errors(probe_bodies())

        self.assertEqual(errors, [])

    def test_negative_clearance_breaks_pair_by_overlap(self):
        with mock.patch.dict(vars(params), {"CLEARANCES": [-0.3]}):
            errors = probe_errors(probe_bodies())

        self.assertError(errors, "Кольцо Дна -0.3", "Кольцо Тарелки", "пересечение", "мм³")

    def test_bed_smaller_than_layout_breaks_bed(self):
        with mock.patch.dict(vars(params), {"BED": (150, 150, 10)}):
            errors = probe.bed(probe_bodies())

        self.assertError(errors, "стол", "150 × 150 × 10 мм")

    def test_smooth_floor_ring_with_wrong_gap_breaks_pair_gap(self):
        bodies = probe_bodies()
        # гладкий цилиндр Ø86 в вершинах кольца Тарелки Ø87: щель 0.5, а не 0.4
        bodies["Кольцо Дна 0.4"] = Part.makeCylinder(43, 15)

        errors = probe.pair(bodies)

        self.assertError(errors, "Кольцо Дна 0.4", "Кольцо Тарелки", "зазор", "0.500 мм")
