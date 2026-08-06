"""
Tests de libraries/cat/cat_sharing_service.py (CatSharingService).

RadioService est un double de test minimal (jamais le vrai port série) :
vérifie uniquement que CatSharingService délègue fidèlement à l'API
déjà publique de RadioService (propriétés connected/frequency/mode,
status.ptt, méthodes set_frequency()/set_mode()/set_ptt()) -- sans
jamais l'appeler autrement, en particulier jamais connect()/disconnect()
(voir test_never_touches_radio_service_connection_lifecycle ci-dessous :
CatSharingService ne doit jamais se comporter comme un second
propriétaire du port).

Les adaptateurs sont eux aussi des doubles enregistreurs (contrat
CatAdapter minimal) : vérifie que start_all()/stop_all() itèrent
fidèlement le registre, dans l'ordre d'ajout, sans jamais inspecter le
contenu d'un adaptateur -- même principe que MapPanel/MapLayer
(tests/test_map_panel.py).
"""

import pytest

from libraries.cat.cat_sharing_service import CatSharingService


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeStatus:
    def __init__(self, ptt=False):
        self.ptt = ptt


class _FakeRadioService:
    def __init__(self, connected=False, frequency=None, mode=None, ptt=False, data_mode=False):
        self.connected = connected
        self.frequency = frequency
        self.mode = mode
        self.status = _FakeStatus(ptt=ptt)
        self.data_mode = data_mode

        self.set_frequency_calls = []
        self.set_mode_calls = []
        self.set_ptt_calls = []
        self.set_data_mode_calls = []

        self.connect_calls = 0
        self.disconnect_calls = 0

        self._set_frequency_result = True
        self._set_mode_result = True
        self._set_ptt_result = True
        self._set_data_mode_result = True

    def connect(self):
        self.connect_calls += 1

    def disconnect(self):
        self.disconnect_calls += 1

    def set_frequency(self, frequency_hz):
        self.set_frequency_calls.append(frequency_hz)
        return self._set_frequency_result

    def set_mode(self, mode):
        self.set_mode_calls.append(mode)
        return self._set_mode_result

    def set_ptt(self, state):
        self.set_ptt_calls.append(state)
        return self._set_ptt_result

    def set_data_mode(self, enabled):
        self.set_data_mode_calls.append(enabled)
        return self._set_data_mode_result


class _RecordingAdapter:
    """Faux adaptateur : n'enregistre que les appels reçus, ne fait rien de réel."""

    def __init__(self, name, calls_log):
        self._name = name
        self._calls_log = calls_log

    def start(self):
        self._calls_log.append((self._name, "start"))

    def stop(self):
        self._calls_log.append((self._name, "stop"))


# ------------------------------------------------------------------
# Façade générique -- délégation fidèle à RadioService
# ------------------------------------------------------------------

def test_is_connected_delegates_to_radio_service(qapp):
    radio_service = _FakeRadioService(connected=True)
    service = CatSharingService(radio_service)

    assert service.is_connected is True

    radio_service.connected = False

    assert service.is_connected is False


def test_get_frequency_hz_delegates_to_radio_service(qapp):
    radio_service = _FakeRadioService(frequency=14195000)
    service = CatSharingService(radio_service)

    assert service.get_frequency_hz() == 14195000


def test_set_frequency_hz_delegates_and_returns_the_result(qapp):
    radio_service = _FakeRadioService()
    service = CatSharingService(radio_service)

    assert service.set_frequency_hz(7074000) is True
    assert radio_service.set_frequency_calls == [7074000]


def test_get_mode_delegates_to_radio_service(qapp):
    radio_service = _FakeRadioService(mode="USB")
    service = CatSharingService(radio_service)

    assert service.get_mode() == "USB"


def test_set_mode_delegates_and_returns_the_result(qapp):
    radio_service = _FakeRadioService()
    service = CatSharingService(radio_service)

    assert service.set_mode("CW") is True
    assert radio_service.set_mode_calls == ["CW"]


def test_get_ptt_delegates_to_radio_service_status(qapp):
    radio_service = _FakeRadioService(ptt=True)
    service = CatSharingService(radio_service)

    assert service.get_ptt() is True


def test_set_ptt_delegates_and_returns_the_result(qapp):
    radio_service = _FakeRadioService()
    service = CatSharingService(radio_service)

    assert service.set_ptt(True) is True
    assert radio_service.set_ptt_calls == [True]


def test_get_data_mode_delegates_to_radio_service(qapp):
    radio_service = _FakeRadioService(data_mode=True)
    service = CatSharingService(radio_service)

    assert service.get_data_mode() is True


def test_set_data_mode_delegates_and_returns_the_result(qapp):
    radio_service = _FakeRadioService()
    service = CatSharingService(radio_service)

    assert service.set_data_mode(True) is True
    assert radio_service.set_data_mode_calls == [True]


def test_set_data_mode_propagates_a_failure_result(qapp):
    radio_service = _FakeRadioService()
    radio_service._set_data_mode_result = False
    service = CatSharingService(radio_service)

    assert service.set_data_mode(True) is False
    assert radio_service.set_data_mode_calls == [True]


def test_never_touches_radio_service_connection_lifecycle(qapp):
    """
    CatSharingService ne doit jamais se comporter comme un second
    propriétaire du port physique -- ne doit donc jamais appeler
    connect()/disconnect() sur RadioService, quelle que soit l'opération
    effectuée ici.
    """

    radio_service = _FakeRadioService()
    service = CatSharingService(radio_service)

    service.is_connected
    service.get_frequency_hz()
    service.set_frequency_hz(14195000)
    service.get_mode()
    service.set_mode("USB")
    service.get_ptt()
    service.set_ptt(False)
    service.get_data_mode()
    service.set_data_mode(False)

    assert radio_service.connect_calls == 0
    assert radio_service.disconnect_calls == 0


# ------------------------------------------------------------------
# Registre d'adaptateurs
# ------------------------------------------------------------------

def test_add_adapter_does_not_start_it(qapp):
    radio_service = _FakeRadioService()
    service = CatSharingService(radio_service)
    calls = []

    service.add_adapter(_RecordingAdapter("a", calls))

    assert calls == []


def test_start_all_starts_every_registered_adapter_in_order(qapp):
    radio_service = _FakeRadioService()
    service = CatSharingService(radio_service)
    calls = []

    service.add_adapter(_RecordingAdapter("a", calls))
    service.add_adapter(_RecordingAdapter("b", calls))

    service.start_all()

    assert calls == [("a", "start"), ("b", "start")]


def test_stop_all_stops_every_registered_adapter_in_order(qapp):
    radio_service = _FakeRadioService()
    service = CatSharingService(radio_service)
    calls = []

    service.add_adapter(_RecordingAdapter("a", calls))
    service.add_adapter(_RecordingAdapter("b", calls))

    service.start_all()
    calls.clear()
    service.stop_all()

    assert calls == [("a", "stop"), ("b", "stop")]


def test_start_all_and_stop_all_do_nothing_without_any_registered_adapter(qapp):
    radio_service = _FakeRadioService()
    service = CatSharingService(radio_service)

    service.start_all()
    service.stop_all()
