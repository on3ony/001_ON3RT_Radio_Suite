"""
Tests de RadioService.send_cw_message()/stop_cw_message()/set_keying_speed()
(apps/cat_server/radio_service.py) -- étape 2 du backend CI-V texte.

Même structure et même double de contrôleur que
tests/test_radio_service_ptt.py::_FakeController -- ces trois nouvelles
méthodes suivent exactement le même contrat que set_ptt()/set_mode()/
set_frequency() : rien si non connectée, exception capturée -> False +
status.last_error + signal error, jamais de mise à jour optimiste de
status (poll() reste l'unique source de vérité).
"""

import pytest

from apps.cat_server.radio_service import RadioService


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeController:
    def __init__(self, connected=True, raise_exc=None):
        self.connected = connected
        self.calls = []
        self._raise_exc = raise_exc

    def send_cw_message(self, text):
        self.calls.append(("send_cw_message", text))
        if self._raise_exc is not None:
            raise self._raise_exc

    def stop_cw_message(self):
        self.calls.append(("stop_cw_message",))
        if self._raise_exc is not None:
            raise self._raise_exc

    def set_keying_speed(self, wpm):
        self.calls.append(("set_keying_speed", wpm))
        if self._raise_exc is not None:
            raise self._raise_exc

    def disconnect(self):
        pass


@pytest.fixture
def service(qapp):
    return RadioService(port="COM_TEST")


# ------------------------------------------------------------------
# send_cw_message()
# ------------------------------------------------------------------

def test_send_cw_message_does_nothing_when_not_connected(service):
    service.controller = _FakeController(connected=False)

    result = service.send_cw_message("CQ ON3RT")

    assert result is False
    assert service.controller.calls == []


def test_send_cw_message_calls_controller_and_returns_true(service):
    service.controller = _FakeController(connected=True)

    result = service.send_cw_message("CQ ON3RT")

    assert result is True
    assert service.controller.calls == [("send_cw_message", "CQ ON3RT")]


def test_send_cw_message_catches_controller_exception_and_returns_false(service):
    service.controller = _FakeController(connected=True, raise_exc=RuntimeError("port perdu"))

    result = service.send_cw_message("CQ ON3RT")

    assert result is False
    assert service.status.last_error == "port perdu"


def test_send_cw_message_emits_error_signal_on_failure(service):
    service.controller = _FakeController(connected=True, raise_exc=RuntimeError("port perdu"))

    received = []
    service.error.connect(lambda msg: received.append(msg))

    service.send_cw_message("CQ ON3RT")

    assert received == ["port perdu"]


# ------------------------------------------------------------------
# stop_cw_message()
# ------------------------------------------------------------------

def test_stop_cw_message_does_nothing_when_not_connected(service):
    service.controller = _FakeController(connected=False)

    result = service.stop_cw_message()

    assert result is False
    assert service.controller.calls == []


def test_stop_cw_message_calls_controller_and_returns_true(service):
    service.controller = _FakeController(connected=True)

    result = service.stop_cw_message()

    assert result is True
    assert service.controller.calls == [("stop_cw_message",)]


def test_stop_cw_message_catches_controller_exception_and_returns_false(service):
    service.controller = _FakeController(connected=True, raise_exc=RuntimeError("port perdu"))

    result = service.stop_cw_message()

    assert result is False
    assert service.status.last_error == "port perdu"


# ------------------------------------------------------------------
# set_keying_speed()
# ------------------------------------------------------------------

def test_set_keying_speed_does_nothing_when_not_connected(service):
    service.controller = _FakeController(connected=False)

    result = service.set_keying_speed(25)

    assert result is False
    assert service.controller.calls == []


def test_set_keying_speed_calls_controller_and_returns_true(service):
    service.controller = _FakeController(connected=True)

    result = service.set_keying_speed(25)

    assert result is True
    assert service.controller.calls == [("set_keying_speed", 25)]


def test_set_keying_speed_catches_controller_exception_and_returns_false(service):
    service.controller = _FakeController(connected=True, raise_exc=RuntimeError("port perdu"))

    result = service.set_keying_speed(25)

    assert result is False
    assert service.status.last_error == "port perdu"


def test_set_keying_speed_emits_error_signal_on_failure(service):
    service.controller = _FakeController(connected=True, raise_exc=RuntimeError("port perdu"))

    received = []
    service.error.connect(lambda msg: received.append(msg))

    service.set_keying_speed(25)

    assert received == ["port perdu"]
