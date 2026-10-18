"""Датчик POK005L: тела и референсы сцены, проверки Датчика."""
from . import meshes

CHECKS = []  # bodies → список ошибок, как в checks.py


def build(doc):
    """Добавляет объекты Датчика в doc, возвращает (тела, референсы)."""
    stub = doc.addObject("Part::Cylinder", "Stub")
    stub.Label = "Заглушка"  # цилиндр фазы 0, заменится формой Датчика
    stub.Radius = 30
    stub.Height = 60
    return [stub], meshes.load(doc)
