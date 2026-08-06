"""
Tests de apps/dashboard/map_layers/world_outline_layer.py (WorldOutlineLayer).

Vérifie le chargement du fichier de contours embarqué (jamais un accès
réseau), le repli propre sur un fichier absent/corrompu (jamais un
crash), et que paint() ne lève jamais, quelle que soit la projection
utilisée -- ne vérifie jamais le rendu pixel par pixel.
"""

import pytest
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import QRect

from apps.dashboard.map_layers.world_outline_layer import WorldOutlineLayer, _DATA_PATH
from libraries.geo.projection import AzimuthalEquidistantProjection


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _paint_layer(layer, projection):
    pixmap = QPixmap(300, 200)
    painter = QPainter(pixmap)
    try:
        layer.paint(painter, projection, QRect(0, 0, 300, 200), {})
    finally:
        painter.end()


def test_bundled_world_outline_file_exists():
    assert _DATA_PATH.exists()


def test_layer_loads_the_bundled_file_without_raising(qapp):
    layer = WorldOutlineLayer()

    layer._ensure_loaded()

    assert layer._polygons is not None
    assert len(layer._polygons) > 0


def test_layer_falls_back_to_empty_on_missing_file(qapp, tmp_path):
    layer = WorldOutlineLayer(data_path=tmp_path / "does_not_exist.json")

    layer._ensure_loaded()

    assert layer._polygons == []


def test_layer_falls_back_to_empty_on_corrupted_file(qapp, tmp_path):
    bad_file = tmp_path / "corrupted.json"
    bad_file.write_text("{not valid json", encoding="utf-8")

    layer = WorldOutlineLayer(data_path=bad_file)
    layer._ensure_loaded()

    assert layer._polygons == []


def test_paint_never_raises_with_the_real_bundled_data(qapp):
    layer = WorldOutlineLayer()
    projection = AzimuthalEquidistantProjection(50.85, 4.35)

    _paint_layer(layer, projection)  # ne doit lever aucune exception


def test_paint_never_raises_with_an_empty_dataset(qapp, tmp_path):
    layer = WorldOutlineLayer(data_path=tmp_path / "does_not_exist.json")
    projection = AzimuthalEquidistantProjection(0.0, 0.0)

    _paint_layer(layer, projection)  # ne doit lever aucune exception, même sans aucun polygone


def test_paint_never_raises_with_projection_centered_at_the_antipode_of_a_point(qapp):
    """Cas dégénéré connu de la projection (voir libraries/geo/projection.py) -- ne doit jamais faire planter la couche."""

    layer = WorldOutlineLayer()
    projection = AzimuthalEquidistantProjection(0.0, 0.0)

    _paint_layer(layer, projection)
