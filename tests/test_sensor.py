import unittest

import FreeCAD
import Part

import sensor
from checks import check

V = FreeCAD.Vector


def sensor_check(bodies):
    errors = check(bodies)
    for check_fn in sensor.CHECKS:
        errors += check_fn(bodies)
    return errors


def grown(shape, axis):
    """shape с выступом: габарит больше на 2 мм по axis, в сторону минуса."""
    box = shape.BoundBox
    start = V(box.Center.x, box.Center.y, box.Center.z)
    size = [1, 1, 1]
    index = "XYZ".index(axis)
    start[index] = getattr(box, f"{axis}Min") - 2
    size[index] = 2 + 1  # на 1 мм внутрь: тело остаётся одним solid
    bump = Part.makeBox(*size, start)
    return shape.fuse(bump).removeSplitter()


class SensorTest(unittest.TestCase):
    """Проверки Датчика: тела сцены → список ошибок."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_plug_from_params_has_no_errors(self):
        errors = sensor_check({"Заглушка": sensor.plug()})

        self.assertEqual(errors, [])

    def test_plug_grown_by_2_mm_breaks_gabarit(self):
        for axis in "XYZ":
            with self.subTest(axis=axis):
                errors = sensor_check({"Заглушка": grown(sensor.plug(), axis)})

                self.assertError(errors, "Заглушка", "габарит", f"по {axis}", "мм")
