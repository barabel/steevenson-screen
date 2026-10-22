"""Сцена Щита: объекты из пакетов деталей.

Имя объекта — его Label. Объекты двух видов:
- тела — твёрдые, идут в проверки и на виды;
- референсы — меши, идут в FCStd и на виды, в проверки не идут.

Пакет детали — папка в src/ с build(doc) → (тела, референсы) и CHECKS.
Фазы добавляют свои пакеты в PARTS, каркас Прогона не меняется.
"""
import floor
import sensor
import skeleton
import stack

PARTS = [stack, floor, skeleton, sensor]


def build(doc):
    """Добавляет объекты деталей в doc, возвращает (тела, референсы)."""
    bodies = []
    references = []
    for part in PARTS:
        part_bodies, part_references = part.build(doc)
        bodies += part_bodies
        references += part_references
    return bodies, references


def checks():
    """Проверки пакетов деталей: bodies → список ошибок."""
    result = []
    for part in PARTS:
        result += part.CHECKS
    return result
