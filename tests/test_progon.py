import contextlib
import io
import shutil
import subprocess
import unittest
from unittest import mock

import FreeCAD
import Part

import build
from build import FCSTD, ROOT, VIEWS

VIEW_NAMES = ["front.png", "left.png", "section.png"]
MESH_LABELS = ["Корпус, нижняя половина", "Корпус, верхняя половина", "Вешалка"]
DRAFT_LABELS = ["Крышка", "Тарелка 1", "Нижняя Тарелка", "Кронштейн"]


class ProgonTest(unittest.TestCase):
    """Прогон целиком: build.cmd как подпроцесс."""

    def test_progon_saves_fcstd_with_drafts_plug_meshes_and_three_views(self):
        FCSTD.unlink(missing_ok=True)
        shutil.rmtree(VIEWS, ignore_errors=True)

        result = subprocess.run(
            ["cmd", "/d", "/c", str(ROOT / "build.cmd")],
            capture_output=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"вылет Кронштейна: \d+(\.\d+)? мм")
        doc = FreeCAD.openDocument(str(FCSTD))
        try:
            labels = [obj.Label for obj in doc.Objects]
            self.assertIn("Заглушка", labels)
            for label in DRAFT_LABELS:
                self.assertIn(label, labels)
            meshes = []
            for obj in doc.Objects:
                if obj.isDerivedFrom("Mesh::Feature"):
                    meshes.append(obj.Label)
            self.assertCountEqual(meshes, MESH_LABELS)
        finally:
            FreeCAD.closeDocument(doc.Name)
        for name in VIEW_NAMES:
            png = VIEWS / name
            self.assertTrue(png.is_file(), f"нет {png}")
            self.assertGreater(png.stat().st_size, 0, f"пустой {png}")


def scene_of(shapes):
    """Подмена scene.build: тела с готовыми Shape по Label, без референсов."""

    def build_scene(doc):
        objects = []
        for label, shape in shapes.items():
            obj = doc.addObject("Part::Feature", "Body")
            obj.Label = label
            obj.Shape = shape
            objects.append(obj)
        return objects, []

    return build_scene


class BrokenSceneTest(unittest.TestCase):
    """Прогон на битой сцене: не падает до проверок, сохраняет что может."""

    def setUp(self):
        FCSTD.unlink(missing_ok=True)
        shutil.rmtree(VIEWS, ignore_errors=True)

    def tearDown(self):
        for name in list(FreeCAD.listDocuments()):
            FreeCAD.closeDocument(name)

    def run_progon(self, shapes):
        out = io.StringIO()
        with mock.patch("scene.build", scene_of(shapes)):
            with contextlib.redirect_stdout(out):
                code = build.run()
        return code, out.getvalue()

    def test_broken_bodies_beside_good_one_still_give_views_and_errors(self):
        code, out = self.run_progon({
            "Целое": Part.makeBox(10, 10, 10),
            "Пустое": Part.makeCompound([]),
            "Нулевое": Part.Shape(),
        })

        self.assertEqual(code, 1, out)
        self.assertTrue(FCSTD.is_file(), out)
        for name in VIEW_NAMES:
            self.assertTrue((VIEWS / name).is_file(), f"нет {name}: {out}")
        self.assertIn("Пустое: объём", out)
        self.assertIn("Нулевое: isValid", out)

    def test_failed_render_still_runs_checks(self):
        code, out = self.run_progon({
            "Пустое": Part.makeCompound([]),
            "Нулевое": Part.Shape(),
        })

        self.assertEqual(code, 1, out)
        self.assertTrue(FCSTD.is_file(), out)
        self.assertIn("рендер", out)
        self.assertIn("Пустое: объём", out)
        self.assertIn("Нулевое: isValid", out)
