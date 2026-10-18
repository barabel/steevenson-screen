import subprocess
import unittest
from pathlib import Path

import FreeCAD

ROOT = Path(__file__).resolve().parent.parent
FCSTD = ROOT / "dist" / "shield.FCStd"


class ProgonTest(unittest.TestCase):
    """Прогон целиком: build.cmd как подпроцесс."""

    def test_progon_saves_fcstd_with_stub(self):
        FCSTD.unlink(missing_ok=True)

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


if __name__ == "__main__":
    unittest.main()
