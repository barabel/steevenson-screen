"""PNG-виды сцены без окна FreeCAD.

Coin SoOffscreenRenderer внутри freecadcmd, геометрия — через Shape.writeInventor().
Вверх — +Z. Главный вид смотрит вдоль +Y, вид слева — вдоль +X.
Фронтальный разрез — плоскость XZ (y = 0) через ось Щита: тела обрезаны
булевым срезом, ближняя к зрителю половина (y < 0) снята, срез закрашен.
Камера ортографическая и одна на все виды: масштаб и центр одинаковы.
"""
import FreeCAD
import FreeCADGui
import Part
from PIL import Image

FreeCADGui.setupWithoutGUI()
from pivy import coin  # noqa: E402 — после setupWithoutGUI

SIZE = 800
BODY_COLOR = (0.8, 0.8, 0.8)
CUT_COLOR = (0.95, 0.55, 0.25)
FRONT = FreeCAD.Vector(0, 1, 0)
LEFT = FreeCAD.Vector(1, 0, 0)


def render(bodies, out_dir):
    """Пишет front.png, left.png, section.png в out_dir, возвращает пути."""
    shapes = list(bodies.values())
    box = shapes[0].BoundBox
    for shape in shapes[1:]:
        box.add(shape.BoundBox)
    cut, cut_faces = section(shapes, box)
    jobs = [
        ("front.png", FRONT, shapes, []),
        ("left.png", LEFT, shapes, []),
        ("section.png", FRONT, cut, cut_faces),
    ]
    paths = []
    for name, direction, solid_shapes, cut_shapes in jobs:
        path = out_dir / name
        root = scene_graph(box, direction, solid_shapes, cut_shapes)
        write_png(root, path)
        paths.append(path)
    return paths


def section(shapes, box):
    """Срез полупространством y >= 0: обрезанные тела и грани на плоскости среза."""
    half = Part.makeBox(
        box.XLength + 2,
        max(box.YMax, 0) + 1,
        box.ZLength + 2,
        FreeCAD.Vector(box.XMin - 1, 0, box.ZMin - 1),
    )
    cut = []
    cut_faces = []
    for shape in shapes:
        kept = shape.common(half)
        cut.append(kept)
        for face in kept.Faces:
            face_box = face.BoundBox
            if face_box.YLength < 1e-6 and abs(face_box.YMin) < 1e-6:
                cut_faces.append(face)
    return cut, cut_faces


def scene_graph(box, direction, solid_shapes, cut_shapes):
    root = coin.SoSeparator()

    size = box.DiagonalLength
    center = box.Center
    camera = coin.SoOrthographicCamera()
    camera.position.setValue(coin.SbVec3f(*(center - direction * size)))
    camera.pointAt(coin.SbVec3f(*center), coin.SbVec3f(0, 0, 1))
    camera.height = size * 1.1
    camera.nearDistance = size * 0.4
    camera.farDistance = size * 1.6
    root.addChild(camera)

    light = coin.SoDirectionalLight()
    light.direction.setValue(coin.SbVec3f(*direction))
    root.addChild(light)

    # тела чуть отодвинуты по глубине: рёбра и закрашенный срез рисуются поверх
    bodies_node = coin.SoSeparator()
    offset = coin.SoPolygonOffset()
    offset.factor = 1
    offset.units = 1
    bodies_node.addChild(offset)
    add_shapes(bodies_node, solid_shapes, BODY_COLOR)
    root.addChild(bodies_node)

    cut_node = coin.SoSeparator()
    add_shapes(cut_node, cut_shapes, CUT_COLOR)
    root.addChild(cut_node)

    return root


def add_shapes(parent, shapes, color):
    material = coin.SoMaterial()
    material.diffuseColor.setValue(coin.SbColor(*color))
    parent.addChild(material)
    for shape in shapes:
        node_input = coin.SoInput()
        node_input.setBuffer(shape.writeInventor())
        node = coin.SoDB.readAll(node_input)
        if node is None:
            raise RuntimeError("Coin не прочитал writeInventor() тела")
        parent.addChild(node)


def write_png(root, path):
    renderer = coin.SoOffscreenRenderer(coin.SbViewportRegion(SIZE, SIZE))
    renderer.setComponents(coin.SoOffscreenRenderer.RGB)
    renderer.setBackgroundColor(coin.SbColor(1, 1, 1))
    if not renderer.render(root):
        raise RuntimeError(f"{path.name}: offscreen OpenGL не отрисовал (драйвер?)")
    image = Image.frombytes("RGB", (SIZE, SIZE), renderer.getBuffer())
    image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(path)
