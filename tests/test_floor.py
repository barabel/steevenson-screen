import math
import unittest
from unittest import mock

import FreeCAD
import Part

import floor
import stack
from checks import MAX_OVERLAP
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

    def test_m4_screws_go_through_disk_and_heel(self):
        shapes = floor.shapes()
        disk_bottom = params.floor_top() - params.FLOOR_DISK_THICKNESS
        heel_top = params.floor_top() + params.HEEL_THICKNESS
        for hole in floor.screw_holes():
            center = hole.BoundBox.Center
            with self.subTest(x=round(center.x, 2), y=round(center.y, 2)):
                # винт M4 — стержень Ø4 от низа Диска до верха Пятки
                screw = Part.makeCylinder(
                    2,
                    heel_top - disk_bottom,
                    V(center.x, center.y, disk_bottom),
                )
                # вокруг отверстия с зазором, Ø5–7 (гайка M4 под ключ), — пластик:
                # в Диске и в Пятке
                bore = Part.makeCylinder(
                    2.5,
                    heel_top - disk_bottom,
                    V(center.x, center.y, disk_bottom),
                )
                disk_wall = Part.makeCylinder(
                    3.5,
                    params.FLOOR_DISK_THICKNESS,
                    V(center.x, center.y, disk_bottom),
                ).cut(bore)
                heel_wall = Part.makeCylinder(
                    3.5,
                    params.HEEL_THICKNESS,
                    V(center.x, center.y, params.floor_top()),
                ).cut(bore)

                self.assertLess(shapes["Дно"].common(screw).Volume, MAX_OVERLAP)
                self.assertLess(shapes["Держатель"].common(screw).Volume, MAX_OVERLAP)
                self.assertAlmostEqual(
                    shapes["Дно"].common(disk_wall).Volume,
                    disk_wall.Volume,
                    places=2,
                )
                self.assertAlmostEqual(
                    shapes["Держатель"].common(heel_wall).Volume,
                    heel_wall.Volume,
                    places=2,
                )

    def test_drains_go_through_disk_clear_of_ledge_heel_and_washers(self):
        bodies = floor.shapes()
        bodies["Нижняя Тарелка"] = stack.bottom_dish()
        heel_top = params.floor_top() + params.HEEL_THICKNESS
        for index, hole in enumerate(floor.screw_holes()):
            center = hole.BoundBox.Center
            # шайба M4 Ø9 на Пятке
            bodies[f"шайба {index}"] = Part.makeCylinder(
                4.5,
                1,
                V(center.x, center.y, heel_top),
            )
        disk_bottom = params.floor_top() - params.FLOOR_DISK_THICKNESS
        top = params.floor_top() + params.NOSE_TO_FLOOR_GAP  # низ Носика
        for i in range(params.FLOOR_DRAIN_COUNT):
            angle = math.radians(i * 360 / params.FLOOR_DRAIN_COUNT)
            with self.subTest(drain=i):
                # путь воды: чуть уже отверстия, от низа Носика сквозь Диск
                path = Part.makeCylinder(
                    params.FLOOR_DRAIN_DIAMETER / 2 - 0.1,
                    top - disk_bottom + 2,
                    V(
                        params.FLOOR_DRAIN_RADIUS * math.cos(angle),
                        params.FLOOR_DRAIN_RADIUS * math.sin(angle),
                        disk_bottom - 1,
                    ),
                )
                for name, shape in bodies.items():
                    self.assertLess(shape.common(path).Volume, MAX_OVERLAP, name)
