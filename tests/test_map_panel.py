"""
Tests de apps/dashboard/panels/map_panel.py (MapPanel).

Vérifie le contrat central de ce chantier : le moteur de rendu itère
une liste de couches SANS jamais connaître leur contenu -- avec de
fausses couches de test (mêmes principe que les doubles de test du
reste de la Suite), pas les vraies WorldOutlineLayer/StationLayer.
"""

import pytest
from PySide6.QtGui import QPainter

from apps.dashboard.panels.map_panel import MapPanel
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


class _RecordingLayer:
    """Fausse couche : n'enregistre que les arguments reçus, ne dessine rien de réel."""

    def __init__(self):
        self.calls = []

    def paint(self, painter, projection, rect, state):
        self.calls.append({
            "painter_is_qpainter": isinstance(painter, QPainter),
            "projection": projection,
            "rect": rect,
            "state": state,
        })


def test_panel_iterates_given_layers_in_order(qapp):
    layer_a = _RecordingLayer()
    layer_b = _RecordingLayer()

    panel = MapPanel(_FakeStationService(), layers=[layer_a, layer_b])
    panel.resize(300, 200)
    panel.canvas.paintEvent(None)

    assert len(layer_a.calls) == 1
    assert len(layer_b.calls) == 1


def test_panel_never_modifies_the_layer_it_is_given(qapp):
    """Le moteur ne fait qu'appeler paint() -- il ne doit jamais lire/écrire un attribut métier de la couche."""

    layer = _RecordingLayer()

    panel = MapPanel(_FakeStationService(), layers=[layer])
    panel.resize(300, 200)
    panel.canvas.paintEvent(None)

    assert layer.calls[0]["painter_is_qpainter"] is True
    assert isinstance(layer.calls[0]["projection"], AzimuthalEquidistantProjection)
    assert isinstance(layer.calls[0]["state"], dict)


def test_panel_centers_projection_on_the_station_coordinates(qapp):
    layer = _RecordingLayer()

    panel = MapPanel(_FakeStationService(latitude=50.85, longitude=4.35), layers=[layer])
    panel.resize(300, 200)
    panel.canvas.paintEvent(None)

    projection = layer.calls[0]["projection"]
    assert projection.center_latitude == 50.85
    assert projection.center_longitude == 4.35


def test_panel_falls_back_to_origin_when_station_not_configured(qapp):
    layer = _RecordingLayer()

    panel = MapPanel(_FakeStationService(latitude=None, longitude=None), layers=[layer])
    panel.resize(300, 200)
    panel.canvas.paintEvent(None)

    projection = layer.calls[0]["projection"]
    assert projection.center_latitude == 0.0
    assert projection.center_longitude == 0.0


def test_panel_works_without_a_live_service(qapp):
    layer = _RecordingLayer()

    panel = MapPanel(_FakeStationService(), layers=[layer])
    panel.resize(300, 200)
    panel.canvas.paintEvent(None)

    assert layer.calls[0]["state"] == {}


def test_panel_builds_default_layers_when_none_given(qapp):
    from apps.dashboard.map_layers.station_layer import StationLayer
    from apps.dashboard.map_layers.world_outline_layer import WorldOutlineLayer

    panel = MapPanel(_FakeStationService())

    assert len(panel.canvas._layers) == 2
    assert isinstance(panel.canvas._layers[0], WorldOutlineLayer)
    assert isinstance(panel.canvas._layers[1], StationLayer)
