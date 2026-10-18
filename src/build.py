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


def render(bodies, references):
    """PNG-виды в dist/views: главный, слева, фронтальный разрез. Без окна.

    Сбой не роняет Прогон: возвращает текст ошибки, проверки идут дальше.
    """
    VIEWS.mkdir(parents=True, exist_ok=True)
    try:
        import views  # тянет FreeCADGui и pivy — только когда рендерим

        paths = views.render(bodies, references, VIEWS)
    except Exception as error:
        traceback.print_exc()
        sys.stderr.flush()
        return f"рендер видов не удался: {error}"
    for path in paths:
        log(f"вид: {path}")
    return None


def run():
    doc = FreeCAD.newDocument("shield")
    body_objects, reference_objects = scene.build(doc)
    doc.recompute()
    bodies = {}
    for obj in body_objects:
        bodies[obj.Label] = obj.Shape
    references = {}
    for obj in reference_objects:
        references[obj.Label] = obj.Mesh

    save(doc)
    errors = []
    render_error = render(bodies, references)
    if render_error:
        errors.append(render_error)
    errors += check(bodies)
    for check_fn in scene.checks():
        errors += check_fn(bodies)

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
