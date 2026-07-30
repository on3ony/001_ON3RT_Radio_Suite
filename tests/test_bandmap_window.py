"""
Tests de apps/bandmap/window.py.

Vérifie : suivi automatique de la bande active, filtrage des spots à
la bande courante, mise à jour temps réel, accord par double-clic
(même mécanisme que DXClusterWindow.send_to_radio), et absence de tout
nouveau service.
"""

import pytest
from PySide6.QtCore import QObject, Signal

import apps.bandmap.window as window_module


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def no_blocking_dialogs(monkeypatch):
    """QMessageBox.information ouvrirait une vraie boîte de dialogue modale : neutralisée pour les tests."""

    monkeypatch.setattr(window_module.QMessageBox, "information", lambda *args, **kwargs: None)


class FakeRadioService(QObject):
    updated = Signal()
    connectionChanged = Signal(bool)

    def __init__(self):
        super().__init__()
        self.connected = False
        self.frequency = 0
        self.set_frequency_calls = []
        self.set_frequency_result = True

    def set_frequency(self, frequency_hz):
        self.set_frequency_calls.append(frequency_hz)
        if self.set_frequency_result:
            self.frequency = frequency_hz
        return self.set_frequency_result


class FakeDXClusterService(QObject):
    spot_received = Signal(dict)
    connectionChanged = Signal(bool)

    def __init__(self):
        super().__init__()
        self.connected = False
        self._spots: list[dict] = []

    def set_recent_spots(self, spots):
        self._spots = list(spots)

    def recent_spots(self, limit=100):
        return list(self._spots)[-limit:] if limit else list(self._spots)


def _spot(frequency_khz, band, dx_callsign="F4XYZ"):
    return {
        "frequency_khz": frequency_khz,
        "band": band,
        "dx_callsign": dx_callsign,
        "spotter": "ON3RT",
        "comment": "",
        "time_utc": "12:00",
        "mode": None,
    }


# ------------------------------------------------------------------
# Construction / états honnêtes
# ------------------------------------------------------------------

def test_window_builds_with_no_services(qapp):
    from apps.bandmap.window import BandMapWindow

    window = BandMapWindow(radio_service=None, dxcluster_service=None)

    assert window.band_map_widget._band_name is None
    assert window.dxcluster_status_label.text() == "DX Cluster : déconnecté"

    window.close()


def test_window_shows_no_band_when_radio_disconnected(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    radio.connected = False
    radio.frequency = 14_074_000

    window = BandMapWindow(radio_service=radio)

    assert window.band_map_widget._band_name is None

    window.close()


def test_window_shows_the_bands_matching_the_radios_current_frequency(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    radio.connected = True
    radio.frequency = 14_074_000  # 20 m

    window = BandMapWindow(radio_service=radio)

    assert window.band_map_widget._band_name == "20m"
    assert window.band_map_widget._lower_hz == 14_000_000
    assert window.band_map_widget._upper_hz == 14_350_000
    assert window.band_map_widget._frequency_hz == 14_074_000

    window.close()


def test_window_loads_only_spots_matching_the_initial_band(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    radio.connected = True
    radio.frequency = 14_074_000  # 20 m

    dxcluster = FakeDXClusterService()
    dxcluster.set_recent_spots(
        [
            _spot(14_200.0, "20m", "IN_BAND"),
            _spot(7_074.0, "40m", "OTHER_BAND"),
        ]
    )

    window = BandMapWindow(radio_service=radio, dxcluster_service=dxcluster)

    callsigns = [s["dx_callsign"] for s in window.band_map_widget._spots]
    assert callsigns == ["IN_BAND"]

    window.close()


# ------------------------------------------------------------------
# Mise à jour en temps réel
# ------------------------------------------------------------------

def test_frequency_update_within_the_same_band_only_moves_the_marker(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    radio.connected = True
    radio.frequency = 14_074_000

    window = BandMapWindow(radio_service=radio)
    assert window._current_band_name == "20m"

    radio.frequency = 14_200_000
    radio.updated.emit()

    assert window._current_band_name == "20m"  # bande inchangée
    assert window.band_map_widget._frequency_hz == 14_200_000

    window.close()


def test_frequency_update_crossing_a_band_boundary_switches_the_band_and_reloads_spots(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    radio.connected = True
    radio.frequency = 14_074_000  # 20 m

    dxcluster = FakeDXClusterService()
    dxcluster.set_recent_spots([_spot(7_074.0, "40m", "ON_40M")])

    window = BandMapWindow(radio_service=radio, dxcluster_service=dxcluster)
    assert window._current_band_name == "20m"

    radio.frequency = 7_074_000  # 40 m
    radio.updated.emit()

    assert window._current_band_name == "40m"
    assert window.band_map_widget._band_name == "40m"
    assert [s["dx_callsign"] for s in window.band_map_widget._spots] == ["ON_40M"]

    window.close()


def test_radio_disconnecting_clears_the_active_band(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    radio.connected = True
    radio.frequency = 14_074_000

    window = BandMapWindow(radio_service=radio)
    assert window._current_band_name == "20m"

    radio.connected = False
    radio.connectionChanged.emit(False)

    assert window._current_band_name is None
    assert window.band_map_widget._band_name is None

    window.close()


def test_new_spot_in_the_current_band_is_added_live(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    radio.connected = True
    radio.frequency = 14_074_000

    dxcluster = FakeDXClusterService()

    window = BandMapWindow(radio_service=radio, dxcluster_service=dxcluster)

    dxcluster.spot_received.emit(_spot(14_100.0, "20m", "LIVE_SPOT"))

    assert [s["dx_callsign"] for s in window.band_map_widget._spots] == ["LIVE_SPOT"]

    window.close()


def test_new_spot_outside_the_current_band_is_ignored(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    radio.connected = True
    radio.frequency = 14_074_000

    dxcluster = FakeDXClusterService()

    window = BandMapWindow(radio_service=radio, dxcluster_service=dxcluster)

    dxcluster.spot_received.emit(_spot(7_074.0, "40m", "OTHER_BAND"))

    assert window.band_map_widget._spots == []

    window.close()


def test_dxcluster_connection_status_label_updates(qapp):
    from apps.bandmap.window import BandMapWindow

    dxcluster = FakeDXClusterService()
    window = BandMapWindow(dxcluster_service=dxcluster)

    assert window.dxcluster_status_label.text() == "DX Cluster : déconnecté"

    dxcluster.connectionChanged.emit(True)
    assert window.dxcluster_status_label.text() == "DX Cluster : connecté"

    window.close()


# ------------------------------------------------------------------
# Accord par double-clic (même mécanisme que DXClusterWindow.send_to_radio)
# ------------------------------------------------------------------

def test_double_click_tunes_the_radio_to_the_spot_frequency(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    radio.connected = True
    radio.frequency = 14_074_000

    window = BandMapWindow(radio_service=radio)

    window.band_map_widget.spot_double_clicked.emit(_spot(14_200.0, "20m"))

    assert radio.set_frequency_calls == [14_200_000]

    window.close()


def test_double_click_without_radio_service_does_not_crash(qapp):
    from apps.bandmap.window import BandMapWindow

    window = BandMapWindow(radio_service=None)

    window.band_map_widget.spot_double_clicked.emit(_spot(14_200.0, "20m"))  # ne doit pas lever d'exception

    window.close()


def test_double_click_with_radio_disconnected_does_not_send_frequency(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    radio.connected = False

    window = BandMapWindow(radio_service=radio)

    window.band_map_widget.spot_double_clicked.emit(_spot(14_200.0, "20m"))

    assert radio.set_frequency_calls == []

    window.close()


# ------------------------------------------------------------------
# Non-régression : aucun nouveau service introduit
# ------------------------------------------------------------------

def test_window_module_does_not_define_a_new_service_class():
    import inspect

    classes = [
        obj for _name, obj in vars(window_module).items()
        if inspect.isclass(obj) and obj.__module__ == window_module.__name__
    ]
    assert classes == [window_module.BandMapWindow]


def test_close_disconnects_signals_without_error(qapp):
    from apps.bandmap.window import BandMapWindow

    radio = FakeRadioService()
    dxcluster = FakeDXClusterService()

    window = BandMapWindow(radio_service=radio, dxcluster_service=dxcluster)
    window.close()  # ne doit lever aucune exception (signaux bien connectés puis déconnectés une fois)
