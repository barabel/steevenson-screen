"""Резьба Стыка Дно↔Нижняя Тарелка: профиль зуба из Скелета, Ø и длина — аргументы.

Однозаходная, правая. Ось — Z, витки от z = 0 до z = length; обе резьбы
идут по одной спирали, поэтому наружная, поставленная в тот же z, стоит
зубом посередине впадины внутренней.

Зуб — трапеция в осевом сечении: боковые стороны под THREAD_FLANK_SLOPE,
глубина THREAD_DEPTH, ширина на половине глубины — шаг/2. Зазор целиком
на наружной резьбе: её зуб и сердечник сжаты по нормали к контуру.

Спираль — makeLongHelix(..., 0) + MakePipeShell в режиме binormal: путь
без тихих сбоев на сетке ресёрча (research/freecad-thread). Фаска захода
заложена в тело вращения до спирали: снятая после, она ломает тело.
"""
import math

import FreeCAD
import Part

from skeleton import params, revolved

V = FreeCAD.Vector
Z = V(0, 0, 1)

JOIN_INTERSECTION = 2  # makeOffset2D: углы контура острые, без скруглений


def flank_tan():
    """Сдвиг боковой стороны по оси на 1 мм глубины."""
    return math.tan(math.radians(params.THREAD_FLANK_SLOPE))


def overlap():
    """Насколько зуб уходит внутрь сердечника, по радиусу.

    Вершины зуба не лежат на сердечнике, а основание с перекрытием строго
    уже шага: соседние витки не касаются, sweep не пересекает сам себя.
    Берём четверть ширины вершины, пересчитанную в радиус.
    """
    crest = params.THREAD_PITCH / 2 - params.THREAD_DEPTH * flank_tan()
    return crest / 4 / flank_tan()


def tooth(major, inner):
    """Зуб номинальной наружной резьбы: вершина на радиусе major, низ — на inner.

    Грань в плоскости XZ, по оси — посередине на z = 0. Боковые стороны
    продолжены внутрь до inner, ниже впадины.
    """
    middle = major - params.THREAD_DEPTH / 2
    quarter = params.THREAD_PITCH / 4
    tan = flank_tan()
    points = []
    for r, side in ((inner, -1), (major, -1), (major, 1), (inner, 1)):
        points.append(V(r, 0, side * (quarter + (middle - r) * tan)))
    return Part.Face(Part.makePolygon(points + points[:1]))


def sweep(profile, inner, length):
    """Виток профиля по спирали радиуса inner, с запасом в шаг за оба торца."""
    pitch = params.THREAD_PITCH
    helix = Part.makeLongHelix(pitch, length + 2 * pitch, inner, 0)
    helix.translate(V(0, 0, -pitch))
    shell = Part.BRepOffsetAPI.MakePipeShell(helix)
    shell.setBiNormalMode(Z)
    shell.add(profile.translated(V(0, 0, -pitch)).OuterWire)
    shell.build()
    shell.makeSolid()
    return shell.shape()


def external(diameter, length, clearance):
    """Наружная резьба: сплошной стержень с витками, вход с фаской сверху.

    diameter — Ø по вершинам без зазора. Зуб и сердечник сжаты на clearance
    по нормали к профилю: щель до номинальной внутренней одинакова на
    вершине, впадине и боковых сторонах.
    """
    pitch = params.THREAD_PITCH
    chamfer = params.THREAD_CHAMFER
    major = diameter / 2
    minor = major - params.THREAD_DEPTH
    core = minor - clearance
    inner = core - overlap()
    # стороны продолжены ниже inner: после сжатия низ зуба всё ещё под ним
    profile = tooth(major, inner - 2 * abs(clearance) - overlap())
    if clearance:
        profile = profile.makeOffset2D(-clearance, JOIN_INTERSECTION)
    keep = Part.Face(Part.makePolygon([
        V(inner, 0, -pitch),
        V(major + 1, 0, -pitch),
        V(major + 1, 0, pitch),
        V(inner, 0, pitch),
        V(inner, 0, -pitch),
    ]))
    profile = profile.common(keep).Faces[0]
    rod = Part.makeCylinder(core, length + 2 * pitch, V(0, 0, -pitch), Z)
    rod = rod.fuse(sweep(profile, inner, length))
    # оболочка шире вершин: её стенка не совпадает с вершиной витка
    wide = major + 1
    crest = major - clearance
    envelope = revolved([
        (0, 0),
        (wide, 0),
        (wide, length - chamfer - (wide - crest)),
        (crest - chamfer, length),
        (0, length),
    ])
    return envelope.common(rod)


def internal(diameter, length):
    """Инструмент внутренней резьбы номинального размера: вычесть из детали.

    diameter — Ø по впадинам, он же Ø по вершинам наружной без зазора.
    Вход с фаской снизу, на z = 0. Выходит за оба торца на шаг: деталь
    с витками от 0 до length режется насквозь.
    """
    pitch = params.THREAD_PITCH
    chamfer = params.THREAD_CHAMFER
    major = diameter / 2
    minor = major - params.THREAD_DEPTH
    inner = minor - overlap()
    bore = Part.makeCylinder(minor, length + 2 * pitch, V(0, 0, -pitch), Z)
    # конус фаски проходит сквозь стенку отверстия, а не касается её
    entry = Part.makeCone(
        minor + chamfer + pitch,
        minor - pitch,
        chamfer + 2 * pitch,
        V(0, 0, -pitch),
        Z,
    )
    return bore.fuse([entry, sweep(tooth(major, inner), inner, length)])
