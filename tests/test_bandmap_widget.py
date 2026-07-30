"""
Tests de apps/bandmap/band_map_widget.py.

Vérifie que BandMapWidget est un composant de rendu pur : aucun accès
à un service, géométrie fréquence<->position correcte, détection de
survol/double-clic sur un spot, et absence de plantage au rendu dans
tous les états (aucune bande, bande avec spots).
"""

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from apps.bandmap.band_map_widget import BandMapWidget


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def widget(qapp):
    w = BandMapWidget()
    w.resize(400, 200)
    yield w
    w.close()


def _double_click_event(pos: QPointF) -> QMouseEvent:
    return QMouseEvent(
        QEvent.Type.MouseButtonDblClick,
        pos,
        pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


# ------------------------------------------------------------------
# Aucun accès direct aux services
# ------------------------------------------------------------------

def test_widget_module_does_not_import_any_service():
    import apps.bandmap.band_map_widget as module

    forbidden_names = ("RadioService", "DXClusterService", "BandManager", "FrequencyService")
    for name in forbidden_names:
        assert not hasattr(module, name), f"{name} ne doit pas être importé dans ce widget"


# ------------------------------------------------------------------
# État de base
# ------------------------------------------------------------------

def test_widget_starts_with_no_active_band(widget):
    assert not widget._has_band()
    assert widget._frequency_hz is None
    assert widget._spots == []


def test_set_band_stores_state_without_touching_spots(widget):
    widget.set_spots([{"frequency_khz": 14074.0, "dx_callsign": "F4XYZ"}])

    widget.set_band("20m", 14_000_000, 14_350_000)

    assert widget._has_band()
    assert widget._band_name == "20m"
    assert widget._lower_hz == 14_000_000
    assert widget._upper_hz == 14_350_000
    # set_band() ne doit jamais toucher aux spots : responsabilité de l'appelant.
    assert len(widget._spots) == 1


def test_clear_band_resets_everything(widget):
    widget.set_band("20m", 14_000_000, 14_350_000)
    widget.set_frequency(14_074_000)
    widget.set_spots([{"frequency_khz": 14074.0, "dx_callsign": "F4XYZ"}])

    widget.clear_band()

    assert not widget._has_band()
    assert widget._frequency_hz is None
    assert widget._spots == []


def test_set_frequency_stores_value(widget):
    widget.set_frequency(14_074_000)
    assert widget._frequency_hz == 14_074_000

    widget.set_frequency(None)
    assert widget._frequency_hz is None


def test_set_spots_replaces_the_list(widget):
    widget.set_spots([{"frequency_khz": 14074.0, "dx_callsign": "A"}])
    widget.set_spots([{"frequency_khz": 14200.0, "dx_callsign": "B"}])

    assert len(widget._spots) == 1
    assert widget._spots[0]["dx_callsign"] == "B"


def test_add_spot_appends(widget):
    widget.set_spots([{"frequency_khz": 14074.0, "dx_callsign": "A"}])
    widget.add_spot({"frequency_khz": 14200.0, "dx_callsign": "B"})

    assert [s["dx_callsign"] for s in widget._spots] == ["A", "B"]


# ------------------------------------------------------------------
# Géométrie fréquence <-> position
# ------------------------------------------------------------------

def test_x_for_frequency_returns_none_without_active_band(widget):
    assert widget._x_for_frequency(14_074_000) is None


def test_x_for_frequency_maps_bounds_to_axis_edges(widget):
    widget.set_band("20m", 14_000_000, 14_350_000)
    rect = widget._axis_rect()

    assert widget._x_for_frequency(14_000_000) == pytest.approx(rect.left())
    assert widget._x_for_frequency(14_350_000) == pytest.approx(rect.right())
    assert widget._x_for_frequency(14_175_000) == pytest.approx(rect.left() + rect.width() / 2, abs=1.0)


def test_x_for_frequency_clamps_out_of_range_values(widget):
    widget.set_band("20m", 14_000_000, 14_350_000)
    rect = widget._axis_rect()

    assert widget._x_for_frequency(13_000_000) == pytest.approx(rect.left())
    assert widget._x_for_frequency(15_000_000) == pytest.approx(rect.right())


# ------------------------------------------------------------------
# Spots positionnables (jamais de donnée inventée)
# ------------------------------------------------------------------

def test_spot_positions_skips_spots_without_a_numeric_frequency(widget):
    widget.set_band("20m", 14_000_000, 14_350_000)
    widget.set_spots(
        [
            {"frequency_khz": 14074.0, "dx_callsign": "OK"},
            {"dx_callsign": "MISSING_FREQ"},
            {"frequency_khz": "not-a-number", "dx_callsign": "BAD_TYPE"},
        ]
    )

    positioned = [spot["dx_callsign"] for _x, spot in widget._spot_positions()]
    assert positioned == ["OK"]


# ------------------------------------------------------------------
# Détection de spot au clic
# ------------------------------------------------------------------

def test_spot_at_finds_the_spot_under_the_cursor(widget):
    widget.set_band("20m", 14_000_000, 14_350_000)
    spot = {"frequency_khz": 14074.0, "dx_callsign": "F4XYZ"}
    widget.set_spots([spot])

    x = widget._x_for_frequency(14_074_000)
    axis_y = widget._axis_y()

    found = widget._spot_at(QPointF(x, axis_y))
    assert found == spot


def test_spot_at_returns_none_far_from_any_spot(widget):
    widget.set_band("20m", 14_000_000, 14_350_000)
    widget.set_spots([{"frequency_khz": 14074.0, "dx_callsign": "F4XYZ"}])

    far_point = QPointF(widget._axis_rect().right(), widget._axis_y())
    assert widget._spot_at(far_point) is None


# ------------------------------------------------------------------
# Double-clic -> signal
# ------------------------------------------------------------------

def test_double_click_on_a_spot_emits_spot_double_clicked(widget):
    widget.set_band("20m", 14_000_000, 14_350_000)
    spot = {"frequency_khz": 14074.0, "dx_callsign": "F4XYZ"}
    widget.set_spots([spot])

    received = []
    widget.spot_double_clicked.connect(received.append)

    x = widget._x_for_frequency(14_074_000)
    axis_y = widget._axis_y()
    widget.mouseDoubleClickEvent(_double_click_event(QPointF(x, axis_y)))

    assert received == [spot]


def test_double_click_away_from_any_spot_emits_nothing(widget):
    widget.set_band("20m", 14_000_000, 14_350_000)
    widget.set_spots([{"frequency_khz": 14074.0, "dx_callsign": "F4XYZ"}])

    received = []
    widget.spot_double_clicked.connect(received.append)

    far_point = QPointF(widget._axis_rect().right(), widget._axis_y())
    widget.mouseDoubleClickEvent(_double_click_event(far_point))

    assert received == []


def test_double_click_with_no_active_band_emits_nothing(widget):
    received = []
    widget.spot_double_clicked.connect(received.append)

    widget.mouseDoubleClickEvent(_double_click_event(QPointF(50, 50)))

    assert received == []


# ------------------------------------------------------------------
# Rendu : ne doit jamais planter, dans aucun état
# ------------------------------------------------------------------

def test_paint_does_not_crash_with_no_band(widget):
    widget.grab()  # force un paintEvent réel, hors écran


def test_paint_does_not_crash_with_band_frequency_and_spots(widget):
    widget.set_band("20m", 14_000_000, 14_350_000)
    widget.set_frequency(14_074_000)
    widget.set_spots(
        [
            {"frequency_khz": 14074.0, "dx_callsign": "F4XYZ", "spotter": "ON3RT", "time_utc": "12:34", "comment": "599"},
            {"frequency_khz": 14200.0, "dx_callsign": "G0ABC"},
        ]
    )

    widget.grab()
