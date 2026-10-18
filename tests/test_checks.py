import unittest

import FreeCAD
import Part

from checks import check

V = FreeCAD.Vector


def box(x=0):
    return Part.makeBox(10, 10, 10, V(x, 0, 0))


class ChecksTest(unittest.TestCase):
    """Проверки геометрии: тела сцены → список ошибок."""

    def assertError(self, errors, *words):
        for error in errors:
            if all(word in error for word in words):
                return
        self.fail(f"нет ошибки со словами {words}: {errors}")

    def test_clean_scene_has_no_errors(self):
        errors = check({"Левый": box(0), "Правый": box(20)})

        self.assertEqual(errors, [])

    def test_broken_body(self):
        open_shell = Part.Shell(box().Faces[:5])  # без одной грани

        errors = check({"Битое": Part.Solid(open_shell)})

        self.assertError(errors, "Битое", "isValid")

    def test_body_of_two_solids(self):
        errors = check({"Куски": Part.makeCompound([box(0), box(20)])})

        self.assertError(errors, "Куски", "solid")

    def test_empty_body(self):
        errors = check({"Пустое": Part.makeCompound([])})

        self.assertError(errors, "Пустое", "объём")

    def test_flat_solid(self):
        square = Part.Face(Part.makePolygon(
            [V(0, 0, 0), V(10, 0, 0), V(10, 10, 0), V(0, 10, 0), V(0, 0, 0)],
        ))
        # один solid из двух совпавших граней: isValid проходит, объём 0
        flat = Part.Solid(Part.Shell([square, square.copy()]))

        errors = check({"Плоское": flat})

        self.assertError(errors, "Плоское", "объём")

    def test_null_body_beside_good_one(self):
        errors = check({"Целое": box(), "Нулевое": Part.Shape()})

        self.assertError(errors, "Нулевое", "isValid")

    def test_intersecting_pair(self):
        errors = check({"Левый": box(0), "Правый": box(5)})

        self.assertError(errors, "Левый", "Правый", "пересечение")
