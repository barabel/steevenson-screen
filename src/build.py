"""Прогон: сцена → dist/shield.FCStd → виды → проверки → код выхода.

Затем Пробник: dist/coupon.FCStd, STL колец в dist/coupon, проверки. Ошибки
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

import coupon
import scene
from checks import check

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FCSTD = DIST / "shield.FCStd"
VIEWS = DIST / "views"
COUPON_FCSTD = DIST / "coupon.FCStd"
COUPON_STL = DIST / "coupon"
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
    errors += run_coupon()

    for error in errors:
        log(f"ОШИБКА: {error}")
    return 1 if errors else 0


def export_coupon_stl(bodies, names):
    """STL каждого тела Пробника в COUPON_STL, имя файла — names[метка].

    Папка очищается: на флешку не попадёт STL кольца, которого больше нет.
    """
    shutil.rmtree(COUPON_STL, ignore_errors=True)
    COUPON_STL.mkdir(parents=True)
    for label, shape in bodies.items():
        mesh = MeshPart.meshFromShape(
            Shape=shape,
            LinearDeflection=STL_DEFLECTION,
            Relative=False,
        )
        path = COUPON_STL / f"{names[label]}.stl"
        mesh.write(str(path))
        log(f"STL: {path}")


def run_coupon():
    """Пробник в свой документ: FCStd, STL колец, проверки → список ошибок."""
    doc = FreeCAD.newDocument("coupon")
    bodies = coupon.bodies_in(doc)

    save(doc, COUPON_FCSTD)
    export_coupon_stl(bodies, coupon.stl_names())
    return coupon.errors(bodies)


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
