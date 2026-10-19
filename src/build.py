"""Прогон: сцена → dist/shield.FCStd → виды → проверки → код выхода.

Затем Пробник: dist/probe.FCStd, STL колец в dist/probe, проверки. Ошибки
обеих сцен — в общий список и общий код выхода.

Запуск — build.cmd. Модуль импортируется и вызывается main(): при импорте
ничего не выполняется.
"""
import shutil
import sys
import traceback
from pathlib import Path

import FreeCAD
import MeshPart

import probe
import scene
from checks import check

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FCSTD = DIST / "shield.FCStd"
VIEWS = DIST / "views"
PROBE_FCSTD = DIST / "probe.FCStd"
PROBE_STL = DIST / "probe"
STL_DEFLECTION = 0.02  # мм, линейное отклонение граней: не съедает зазор резьбы


def log(message):
    print(message, flush=True)


def save(doc, path):
    DIST.mkdir(exist_ok=True)
    path.unlink(missing_ok=True)  # иначе saveAs оставляет рядом *.FCBak
    doc.saveAs(str(path))
    log(f"сохранено: {path}")


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

    save(doc, FCSTD)
    errors = []
    render_error = render(bodies, references)
    if render_error:
        errors.append(render_error)
    errors += check(bodies)
    for check_fn in scene.checks():
        errors += check_fn(bodies)
    errors += run_probe()

    for error in errors:
        log(f"ОШИБКА: {error}")
    return 1 if errors else 0


def export_stl(bodies, names):
    """STL каждого тела в PROBE_STL, имя файла — names[метка].

    Папка очищается: на флешку не попадёт STL кольца, которого больше нет.
    """
    shutil.rmtree(PROBE_STL, ignore_errors=True)
    PROBE_STL.mkdir(parents=True)
    for label, shape in bodies.items():
        mesh = MeshPart.meshFromShape(
            Shape=shape,
            LinearDeflection=STL_DEFLECTION,
            Relative=False,
        )
        path = PROBE_STL / f"{names[label]}.stl"
        mesh.write(str(path))
        log(f"STL: {path}")


def run_probe():
    """Пробник в свой документ: FCStd, STL колец, проверки → список ошибок."""
    doc = FreeCAD.newDocument("probe")
    objects = probe.build(doc)
    doc.recompute()
    bodies = {}
    for obj in objects:
        bodies[obj.Label] = obj.Shape

    save(doc, PROBE_FCSTD)
    export_stl(bodies, probe.stl_names())
    errors = check(bodies)
    for check_fn in probe.CHECKS:
        errors += check_fn(bodies)
    return errors


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
