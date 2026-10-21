import unittest

import Part

import thread


def bottom_crest_volume(shape):
    """Объём тела у нижнего торца (слой 0.1 мм) у вершин зуба, r 44…46."""
    tube = Part.makeCylinder(46, 0.1).cut(Part.makeCylinder(44, 0.1))
    return shape.common(tube).Volume


class ThreadTest(unittest.TestCase):
    """Модуль резьбы: фаска нижнего торца наружной резьбы — только по запросу."""

    def test_external_bottom_reaches_crest_without_bed_chamfer(self):
        # Ø90, зазор 0.4: вершины на r 44.6
        volume = bottom_crest_volume(thread.external(90, 15, 0.4))

        self.assertGreater(volume, 0.01)

    def test_external_bottom_is_chamfered_with_bed_chamfer(self):
        # фаска 1 × 45°: в слое 0.1 мм тело не дальше r 43.7
        volume = bottom_crest_volume(thread.external(90, 15, 0.4, bed_chamfer=True))

        self.assertLess(volume, 1e-6)
