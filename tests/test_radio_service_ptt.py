"""
Tests de RadioService.set_ptt() et RadioService.aboutToDisconnect
(apps/cat_server/radio_service.py).

CATController est un double de test minimal (jamais le vrai port
série) : ne vérifie que le contrat que PTTGuard exploite — appel
conditionné à controller.connected, capture des exceptions, valeur de
retour booléenne.

aboutToDisconnect corrige une cause réelle trouvée lors d'un essai sur
matériel réel : disconnect() fermait le port avant que quoi que ce
soit ait pu relâcher un PTT actif, rendant set_ptt(False) inopérant
après coup (controller.connected déjà False). Les tests ci-dessous
vérifient précisément que le signal est émis PENDANT que la liaison
existe encore.
"""

import pytest

from apps.cat_server.radio_service import RadioService


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeController:
    def __init__(self, connected=True, raise_on_set_ptt=None):
        self.connected = connected
        self.calls = []
        self._raise_on_set_ptt = raise_on_set_ptt

    def set_ptt(self, state):
        self.calls.append(state)
        if self._raise_on_set_ptt is not None:
            raise self._raise_on_set_ptt

    def disconnect(self):
        pass


@pytest.fixture
def service(qapp):
    return RadioService(port="COM_TEST")


def test_set_ptt_does_nothing_when_not_connected(service):
    service.controller = _FakeController(connected=False)

    result = service.set_ptt(True)

    assert result is False
    assert service.controller.calls == []


def test_set_ptt_true_calls_controller_and_returns_true(service):
    service.controller = _FakeController(connected=True)

    result = service.set_ptt(True)

    assert result is True
    assert service.controller.calls == [True]


def test_set_ptt_false_calls_controller_and_returns_true(service):
    service.controller = _FakeController(connected=True)

    result = service.set_ptt(False)

    assert result is True
    assert service.controller.calls == [False]


def test_set_ptt_catches_controller_exception_and_returns_false(service):
    service.controller = _FakeController(connected=True, raise_on_set_ptt=RuntimeError("port perdu"))

    result = service.set_ptt(True)

    assert result is False
    assert service.status.last_error == "port perdu"


def test_set_ptt_emits_error_signal_on_failure(service):
    service.controller = _FakeController(connected=True, raise_on_set_ptt=RuntimeError("port perdu"))

    received = []
    service.error.connect(lambda msg: received.append(msg))

    service.set_ptt(True)

    assert received == ["port perdu"]


def test_set_ptt_does_not_optimistically_update_status(service):
    """Même choix que set_frequency()/set_mode() : poll() reste l'unique source de vérité pour status.ptt."""

    service.controller = _FakeController(connected=True)
    before = service.status.ptt

    service.set_ptt(True)

    assert service.status.ptt == before


# ------------------------------------------------------------------
# aboutToDisconnect : émis pendant que la liaison existe encore
# ------------------------------------------------------------------

def test_disconnect_emits_about_to_disconnect(service):
    service.controller = _FakeController(connected=True)

    received = []
    service.aboutToDisconnect.connect(lambda: received.append(True))

    service.disconnect()

    assert received == [True]


def test_about_to_disconnect_fires_while_controller_still_reports_connected(service):
    """Le point exact du correctif : au moment du signal, controller.connected est encore True."""

    service.controller = _FakeController(connected=True)

    observed = []
    service.aboutToDisconnect.connect(lambda: observed.append(service.controller.connected))

    service.disconnect()

    assert observed == [True]


def test_set_ptt_still_succeeds_when_called_from_the_about_to_disconnect_handler(service):
    """
    Preuve directe du correctif : un release() déclenché par
    aboutToDisconnect peut encore atteindre la radio, contrairement à
    un release() appelé après un disconnect() déjà terminé.
    """

    service.controller = _FakeController(connected=True)

    results = []
    service.aboutToDisconnect.connect(lambda: results.append(service.set_ptt(False)))

    service.disconnect()

    assert results == [True]
    assert service.controller.calls == [False]
