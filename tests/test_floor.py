import unittest
from unittest import mock

import FreeCAD
import Part

import floor
import stack
from skeleton import params
from test_skeleton import scene_errors

V = FreeCAD.Vector


def floor_errors(bodies):
    """Подставные тела → проверки Дна и Держателя."""
    errors = []
    for check_fn in floor.CHECKS:
        errors += check_fn(bodies)
    return errors


class FloorTest(unittest.TestCase):
    """Проверки Дна и Держателя на подставных телах: тела → список ошибок."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_holder_away_from_ear_hole_does_not_hang_plug(self):
        bodies = {
            "Заглушка": Part.makeBox(10, 10, 10),
            "Держатель": Part.makeBox(10, 10, 10, V(500, 500, 500)),
        }

        errors = floor_errors(bodies)

        self.assertError(errors, "Крючок", "Ушко")

    def test_hook_check_is_silent_without_plug_or_holder(self):
        away = Part.makeBox(10, 10, 10, V(500, 500, 500))
        cases = {
            "нет Заглушки": {"Держатель": away},
            "нет Держателя": {"Заглушка": away},
        }
        for name, bodies in cases.items():
            with self.subTest(name):
                self.assertEqual(floor_errors(bodies), [])

    def test_floor_shifted_down_in_thread_ring_breaks_thread_pair(self):
        # 0.2 мм по оси — доля шага: щель по нормали с одной стороны зуба меньше зазора
        bodies = {
            "Нижняя Тарелка": stack.bottom_dish(),
            "Дно": floor.floor().translated(V(0, 0, -0.2)),
        }

        errors = floor_errors(bodies)

        self.assertError(errors, "Дно", "Нижняя Тарелка", "щель", "мм")

    def test_thread_pair_is_silent_without_floor(self):
        bodies = {"Нижняя Тарелка": stack.bottom_dish()}

        self.assertEqual(floor_errors(bodies), [])

    def test_grip_raised_into_thread_ring_overlaps_bottom_dish(self):
        # верх хвата на 5 мм выше низа резьбового кольца
        with mock.patch.dict(vars(params), {"FLOOR_GRIP_GAP": -5}):
            errors = scene_errors()

        self.assertError(errors, "Дно", "Нижняя Тарелка", "пересечение")
