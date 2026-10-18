import shutil
import subprocess
import unittest
from pathlib import Path

import FreeCAD

ROOT = Path(__file__).resolve().parent.parent
FCSTD = ROOT / "dist" / "shield.FCStd"
VIEWS = ROOT / "dist" / "views"


class ProgonTest(unittest.TestCase):
    """Прогон целиком: build.cmd как подпроцесс."""

    def test_progon_saves_fcstd_with_stub_and_three_views(self):
        FCSTD.unlink(missing_ok=True)
        shutil.rmtree(VIEWS, ignore_errors=True)

        result = subprocess.run(
            ["cmd", "/d", "/c", str(ROOT / "build.cmd")],
            capture_output=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        doc = FreeCAD.openDocument(str(FCSTD))
        try:
            labels = [obj.Label for obj in doc.Objects]
            self.assertIn("Заглушка", labels)
        finally:
            FreeCAD.closeDocument(doc.Name)
        for name in ["front.png", "left.png", "section.png"]:
            png = VIEWS / name
            self.assertTrue(png.is_file(), f"нет {png}")
            self.assertGreater(png.stat().st_size, 0, f"пустой {png}")


if __name__ == "__main__":
    unittest.main()
