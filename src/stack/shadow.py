"""Проверка тени: прямое солнце не попадает ни в одну точку Заглушки.

От точек Заглушки — лучи к солнцу: высота 0–90°, направление по всему кругу.
Луч, не задевший ни одного тела, кроме самой Заглушки, уходит за габарит
сцены — точка на солнце. Сама Заглушка лучи не загораживает: проверка
строже, чем реальность.

Тела — треугольники триангуляции. Она вписана в тело, щели в ней не уже
настоящих: проверка не пропустит щель, а не выдумает тень.
"""
import math

import MeshPart
import numpy

from sensor import PLUG

ELEVATION_STEP = 5  # градусы, высота солнца 0, 5, …, 90
AZIMUTH_STEP = 15  # градусы, направление 0, 15, …, 345 от +X к +Y
BODY_DEFLECTION = 0.5  # мм, триангуляция тел, загораживающих солнце
PLUG_DEFLECTION = 2  # мм, триангуляция Заглушки: её вершины — точки проверки
PLUG_ANGLE = 0.5  # рад, угловой допуск той же триангуляции
EPSILON = 1e-6  # мм: луч из точки не задевает тело на самой точке
# доля стороны треугольника: луч точно по ребру между двумя треугольниками
# (шов тела вращения) не проскальзывает между ними от шума float
EDGE = 1e-9
PARALLEL = 1e-12  # |det| меньше — луч параллелен треугольнику


def body_triangles(bodies):
    """Треугольники всех тел, кроме Заглушки: массив T×3×3."""
    result = [numpy.zeros((0, 3, 3))]
    for name, shape in bodies.items():
        if name == PLUG or shape.isNull():
            continue
        points, facets = shape.tessellate(BODY_DEFLECTION)
        vertices = numpy.array([[p.x, p.y, p.z] for p in points])
        result.append(vertices[numpy.array(facets, dtype=int).reshape(-1, 3)])
    return numpy.concatenate(result)


def plug_points(shape):
    """Точки проверки: вершины грубой триангуляции Заглушки, массив P×3."""
    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=PLUG_DEFLECTION,
        AngularDeflection=PLUG_ANGLE,
    )
    return numpy.array([[p.x, p.y, p.z] for p in mesh.Points])


def ray_triangle_coordinate(points, origin, vector, det):
    """Одна из u, v, t Möller–Trumbore для всех пар точка × треугольник: массив P×T.

    (точка − вершина треугольника)·vector / det.
    """
    offset = numpy.einsum("ij,ij->i", origin, vector)
    return (points @ vector.T - offset) / det


def candidates(points, triangles, direction):
    """Треугольники, которые луч из какой-то точки по direction может задеть.

    Луч входит в замкнутое тело через грань, смотрящую ему навстречу; грань
    должна быть впереди точек по лучу и перекрывать их в проекции вдоль луча.
    """
    normal = numpy.cross(
        triangles[:, 1] - triangles[:, 0],
        triangles[:, 2] - triangles[:, 0],
    )
    toward = normal @ direction < 0
    ahead = (triangles @ direction).max(axis=1) > (points @ direction).min()
    helper = [1, 0, 0] if abs(direction[2]) > 0.9 else [0, 0, 1]
    side = numpy.cross(direction, helper)
    side /= numpy.linalg.norm(side)
    plane = numpy.stack([side, numpy.cross(direction, side)], axis=1)
    flat = triangles @ plane
    flat_points = points @ plane
    overlap = (
        (flat.max(axis=1) >= flat_points.min(axis=0)).all(axis=1)
        & (flat.min(axis=1) <= flat_points.max(axis=0)).all(axis=1)
    )
    return triangles[toward & ahead & overlap]


def lit(points, triangles, direction):
    """Маска точек, луч из которых по direction не задевает ни одного треугольника.

    Möller–Trumbore для всех точек и треугольников разом: u, v, t линейны
    по началу луча, поэтому считаются умножением матриц P×3 на 3×T.
    """
    triangles = candidates(points, triangles, direction)
    origin = triangles[:, 0]
    edge1 = triangles[:, 1] - origin
    edge2 = triangles[:, 2] - origin
    pvec = numpy.cross(direction, edge2)
    det = numpy.einsum("ij,ij->i", edge1, pvec)
    facing = numpy.abs(det) > PARALLEL
    det = numpy.where(facing, det, 1)
    u = ray_triangle_coordinate(points, origin, pvec, det)
    v = ray_triangle_coordinate(points, origin, numpy.cross(edge1, direction), det)
    t = ray_triangle_coordinate(points, origin, numpy.cross(edge1, edge2), det)
    hit = (
        facing
        & (u >= -EDGE)
        & (v >= -EDGE)
        & (u + v <= 1 + EDGE)
        & (t > EPSILON)
    )
    return ~hit.any(axis=1)


def shadow(bodies):
    """Заглушка в тени при любой высоте солнца 0–90° и с любого направления.

    Ошибка — первый луч на солнце: высота, направление и точка Заглушки.
    Нет Заглушки или она null — молчит.
    """
    shape = bodies.get(PLUG)
    if shape is None or shape.isNull():
        return []
    points = plug_points(shape)
    triangles = body_triangles(bodies)
    for elevation in range(0, 91, ELEVATION_STEP):
        for azimuth in range(0, 360, AZIMUTH_STEP):
            up = math.radians(elevation)
            around = math.radians(azimuth)
            direction = numpy.array([
                math.cos(up) * math.cos(around),
                math.cos(up) * math.sin(around),
                math.sin(up),
            ])
            mask = lit(points, triangles, direction)
            if mask.any():
                x, y, z = points[mask.argmax()]
                return [
                    f"{PLUG}: тень — солнце на высоте {elevation}°,"
                    f" направление {azimuth}° от +X к +Y,"
                    f" светит в точку ({x:.1f}, {y:.1f}, {z:.1f})",
                ]
    return []
