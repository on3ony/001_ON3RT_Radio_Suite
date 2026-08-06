"""
Tests de apps/dashboard/map_layers/station_layer.py (StationLayer).

Vérifie que la couche n'affiche RIEN tant que la station n'est pas
configurée (latitude/longitude à None -- aucune position inventée),
et que paint() ne lève jamais, avec ou sans indicatif renseigné.
StationService est un double minimal (jamais une vraie instance liée à
config/station.json).
"""

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter, QPixmap

from apps.dashboard.map_layers.station_layer import StationLayer
from libraries.geo.projection import AzimuthalEquidistantProjection


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeStationService:
    def __init__(self, latitude=None, longitude=None, callsign=""):
        self.latitude = latitude
        self.longitude = longitude
        self.callsign = callsign


def _paint_layer(layer, projection):
    pixmap = QPixmap(300, 200)
    painter = QPainter(pixmap)
    try:
        layer.paint(painter, projection, QRect(0, 0, 300, 200), {})
    finally:
        painter.end()


def test_paint_does_nothing_when_station_not_configured(qapp):
    layer = StationLayer(_FakeStationService(latitude=None, longitude=None))
    projection = AzimuthalEquidistantProjection(0.0, 0.0)

    _paint_layer(layer, projection)  # ne doit lever aucune exception, ni tenter de dessiner


def test_paint_does_nothing_when_only_latitude_is_missing(qapp):
    layer = StationLayer(_FakeStationService(latitude=None, longitude=4.35))
    projection = AzimuthalEquidistantProjection(0.0, 0.0)

    _paint_layer(layer, projection)


def test_paint_does_nothing_when_only_longitude_is_missing(qapp):
    layer = StationLayer(_FakeStationService(latitude=50.85, longitude=None))
    projection = AzimuthalEquidistantProjection(0.0, 0.0)

    _paint_layer(layer, projection)


def test_paint_succeeds_with_a_fully_configured_station(qapp):
    layer = StationLayer(_FakeStationService(latitude=50.85, longitude=4.35, callsign="ON3RT"))
    projection = AzimuthalEquidistantProjection(50.85, 4.35)

    _paint_layer(layer, projection)  # ne doit lever aucune exception


def test_paint_succeeds_without_a_callsign(qapp):
    """Un indicatif vide ne doit jamais faire échouer le dessin du marqueur lui-même."""

    layer = StationLayer(_FakeStationService(latitude=50.85, longitude=4.35, callsign=""))
    projection = AzimuthalEquidistantProjection(50.85, 4.35)

    _paint_layer(layer, projection)
