"""
Tests du câblage S-mètre dans RadioService.poll() (apps/cat_server/radio_service.py).

CATController est un double de test minimal (jamais le vrai port
série), mirroring tests/test_radio_service_ptt.py -- ne vérifie que le
contrat exploité par poll() : read_frequency()/read_mode()/read_ptt()/
read_smeter(), status.smeter_level/status.smeter mis à jour uniquement
sur changement, et les deux présents dans info() (donc dans
data/live.json, donc dans l'état partagé du Dashboard).

smeter_level (entier brut 0-255) est la donnée de RÉFÉRENCE, destinée
aux futurs widgets graphiques/animés (voir CATEngine.read_smeter()) ;
smeter (texte, ex. "S9") n'en est qu'une représentation dérivée pour
l'interface actuelle. Les deux évoluent toujours ensemble (display est
une fonction pure de level) -- read_smeter() retourne donc un couple
(level, display), jamais (None, display) ni (level, None).
"""

import pytest

from apps.cat_server.radio_service import RadioService


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeController:
    def __init__(
        self, connected=True, frequency=14074000, mode="USB", ptt=False,
        smeter_level=120, smeter_display="S9",
    ):
        self.connected = connected
        self._frequency = frequency
        self._mode = mode
        self._ptt = ptt
        self._smeter_level = smeter_level
        self._smeter_display = smeter_display

    def read_frequency(self):
        return self._frequency

    def read_mode(self):
        return self._mode

    def read_ptt(self):
        return {"ptt": self._ptt}

    def read_smeter(self):
        return self._smeter_level, self._smeter_display

    def disconnect(self):
        pass


@pytest.fixture
def service(qapp):
    return RadioService(port="COM_TEST")


def test_poll_updates_status_smeter_level_and_display_from_controller(service):
    service.controller = _FakeController(smeter_level=68, smeter_display="S5")

    service.poll()

    assert service.status.smeter_level == 68
    assert service.status.smeter == "S5"
    assert service.smeter_level == 68
    assert service.smeter == "S5"


def test_poll_ignores_none_smeter_reading(service):
    """Une lecture absente/malformée ((None, None), voir CATEngine.read_smeter()) ne doit jamais écraser une valeur connue."""

    service.controller = _FakeController(smeter_level=120, smeter_display="S9")
    service.poll()
    assert service.status.smeter_level == 120
    assert service.status.smeter == "S9"

    service.controller = _FakeController(smeter_level=None, smeter_display=None)
    service.poll()

    assert service.status.smeter_level == 120
    assert service.status.smeter == "S9"


def test_poll_emits_updated_signal_even_when_smeter_unchanged(service):
    service.controller = _FakeController(smeter_level=85, smeter_display="S6")
    service.poll()

    received = []
    service.updated.connect(lambda: received.append(True))

    service.poll()

    assert received == [True]


def test_poll_does_nothing_when_not_connected(service):
    service.controller = _FakeController(connected=False, smeter_level=120, smeter_display="S9")

    service.poll()

    assert service.status.smeter_level is None
    assert service.status.smeter is None


def test_info_includes_smeter_level_and_display(service):
    service.controller = _FakeController(smeter_level=241, smeter_display="S9+60dB")

    service.poll()
    info = service.info()

    assert info["smeter_level"] == 241
    assert info["smeter"] == "S9+60dB"


def test_smeter_defaults_to_none_before_any_poll(service):
    assert service.status.smeter_level is None
    assert service.status.smeter is None
    assert service.smeter_level is None
    assert service.smeter is None
