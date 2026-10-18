"""Прогон: сцена → dist/shield.FCStd → виды → проверки → код выхода.

Запуск — build.cmd. Модуль импортируется и вызывается main(): при импорте
ничего не выполняется.
"""
import sys
import traceback
from pathlib import Path

import FreeCAD

import scene
from checks import check

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FCSTD = DIST / "shield.FCStd"
VIEWS = DIST / "views"


def log(message):
    print(message, flush=True)


def save(doc):
    DIST.mkdir(exist_ok=True)
    FCSTD.unlink(missing_ok=True)  # иначе saveAs оставляет рядом *.FCBak
    doc.saveAs(str(FCSTD))
    log(f"сохранено: {FCSTD}")


def render(bodies):
    """PNG-виды в dist/views: главный, слева, фронтальный разрез. Без окна."""
    VIEWS.mkdir(parents=True, exist_ok=True)
    try:
        import views  # тянет FreeCADGui и pivy — только когда рендерим

        paths = views.render(bodies, VIEWS)
    except Exception as error:
        raise RuntimeError(f"рендер видов не удался: {error}") from error
    for path in paths:
        log(f"вид: {path}")


def run():
    doc = FreeCAD.newDocument("shield")
    objects = scene.build(doc)
    doc.recompute()
    bodies = {}
    for obj in objects:
        bodies[obj.Label] = obj.Shape

    save(doc)
    render(bodies)
    errors = check(bodies)

    for error in errors:
        log(f"ОШИБКА: {error}")
    return 1 if errors else 0


def main():
    """Точка входа. Сама ловит исключения: freecadcmd на них может выйти с 0."""
    try:
        code = run()
    except Exception:
        traceback.print_exc()
        sys.stderr.flush()
        log("Прогон упал")
        sys.exit(1)
    log("Прогон: ок" if code == 0 else "Прогон: проверки не прошли")
    sys.exit(code)
