"""PNG-виды сцены без окна FreeCAD.

Coin SoOffscreenRenderer внутри freecadcmd, геометрия — через Shape.writeInventor().
Вверх — +Z. Главный вид смотрит вдоль +Y, вид слева — вдоль +X.
Фронтальный разрез — плоскость XZ (y = 0) через ось Щита: тела обрезаны
булевым срезом, ближняя к зрителю половина (y < 0) снята, срез закрашен.
Референсы (меши) — полупрозрачные, своим цветом; в разрезе обрезаны той же
плоскостью отсечения OpenGL, срез меша не закрашивается — он не замкнут;
сечение меша плоскостью разреза рисуется линиями поверх среза тел.
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
REFERENCE_COLOR = (0.25, 0.5, 0.9)
REFERENCE_TRANSPARENCY = 0.5
OUTLINE_COLOR = (0.1, 0.25, 0.7)  # сечение меша в разрезе: темнее REFERENCE_COLOR
OUTLINE_WIDTH = 2
OUTLINE_SHIFT = 0.1  # мм к зрителю: линии не тонут в срезе тел
FRONT = FreeCAD.Vector(0, 1, 0)
LEFT = FreeCAD.Vector(1, 0, 0)


def render(bodies, references, out_dir):
    """Пишет front.png, left.png, section.png в out_dir, возвращает пути.

    bodies — Label → Shape, references — Label → Mesh.
    Тела без граней (null, пустые) и пустые меши пропускает: тела ловят проверки.
    """
    shapes = []
    for shape in bodies.values():
        if not shape.isNull() and shape.Faces:
            shapes.append(shape)
    meshes = []
    for mesh in references.values():
        if mesh.CountFacets:
            meshes.append(mesh)
    boxes = []
    for item in shapes + meshes:
        boxes.append(item.BoundBox)
    if not boxes:
        raise RuntimeError("нечего рисовать: ни у одного тела нет граней")
    box = boxes[0]
    for item_box in boxes[1:]:
        box.add(item_box)
    cut, cut_faces = section(shapes, box)
    references_node = meshes_node(meshes)  # один на все виды: меши тяжёлые
    jobs = [
        ("front.png", FRONT, shapes, [], False),
        ("left.png", LEFT, shapes, [], False),
        ("section.png", FRONT, cut, cut_faces, True),
    ]
    paths = []
    for name, direction, solid_shapes, cut_shapes, clip in jobs:
        path = out_dir / name
        root = scene_graph(box, direction, solid_shapes, cut_shapes)
        if clip:
            root.addChild(clipped(references_node))
            root.addChild(outlines_node(meshes))
        else:
            root.addChild(references_node)
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


def clipped(child):
    """child с отсечённой ближней половиной (y < 0), как у разреза."""
    node = coin.SoSeparator()  # отсечение не выходит за узел
    plane = coin.SoClipPlane()
    plane.plane.setValue(coin.SbPlane(coin.SbVec3f(0, 1, 0), 0))  # оставляет y >= 0
    node.addChild(plane)
    node.addChild(child)
    return node


def meshes_node(meshes):
    """Меши-референсы: полупрозрачные, цветом REFERENCE_COLOR."""
    node = coin.SoSeparator()  # материал не выходит за узел
    # освещение с двух сторон: в разрезе видна изнанка граней, без него она серая
    hints = coin.SoShapeHints()
    hints.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
    hints.shapeType = coin.SoShapeHints.UNKNOWN_SHAPE_TYPE
    node.addChild(hints)
    material = coin.SoMaterial()
    material.diffuseColor.setValue(coin.SbColor(*REFERENCE_COLOR))
    material.transparency.setValue(REFERENCE_TRANSPARENCY)
    node.addChild(material)
    for mesh in meshes:
        points, facets = mesh.Topology
        coords = coin.SoCoordinate3()
        xyz = []
        for point in points:
            xyz.append((point.x, point.y, point.z))
        coords.point.setValues(0, len(xyz), xyz)
        node.addChild(coords)
        index = []
        for a, b, c in facets:
            index += [a, b, c, -1]
        faces = coin.SoIndexedFaceSet()
        faces.coordIndex.setValues(0, len(index), index)
        node.addChild(faces)
    return node


def outlines_node(meshes):
    """Сечения мешей плоскостью разреза (y = 0) — линии поверх закрашенного
    среза тел: иначе срез тел закрывает обрезанные меши."""
    node = coin.SoSeparator()
    light_model = coin.SoLightModel()
    light_model.model = coin.SoLightModel.BASE_COLOR
    node.addChild(light_model)
    material = coin.SoMaterial()
    material.diffuseColor.setValue(coin.SbColor(*OUTLINE_COLOR))
    node.addChild(material)
    style = coin.SoDrawStyle()
    style.lineWidth = OUTLINE_WIDTH
    node.addChild(style)
    # чуть ближе к зрителю, чем срез тел
    shift = coin.SoTranslation()
    shift.translation.setValue(0, -OUTLINE_SHIFT, 0)
    node.addChild(shift)
    plane = (FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0))
    for mesh in meshes:
        for polyline in mesh.crossSections([plane])[0]:
            xyz = []
            for point in polyline:
                xyz.append((point.x, point.y, point.z))
            coords = coin.SoCoordinate3()
            coords.point.setValues(0, len(xyz), xyz)
            node.addChild(coords)
            line = coin.SoLineSet()
            line.numVertices.setValue(len(xyz))
            node.addChild(line)
    return node


def write_png(root, path):
    renderer = coin.SoOffscreenRenderer(coin.SbViewportRegion(SIZE, SIZE))
    # полупрозрачное рисуется после непрозрачного, с сортировкой по глубине
    renderer.getGLRenderAction().setTransparencyType(
        coin.SoGLRenderAction.SORTED_OBJECT_BLEND,
    )
    renderer.setComponents(coin.SoOffscreenRenderer.RGB)
    renderer.setBackgroundColor(coin.SbColor(1, 1, 1))
    if not renderer.render(root):
        raise RuntimeError(f"{path.name}: offscreen OpenGL не отрисовал (драйвер?)")
    image = Image.frombytes("RGB", (SIZE, SIZE), renderer.getBuffer())
    image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(path)
