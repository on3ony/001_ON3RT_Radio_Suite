"""
Tests de RadioService.set_data_mode() (apps/cat_server/radio_service.py).

CATController est un double de test minimal (jamais le vrai port
série), même méthode que tests/test_radio_service_ptt.py. Contrairement
à set_frequency()/set_mode()/set_ptt(), status.data_mode EST mis à
jour ici -- ces tests vérifient précisément que cette mise à jour
n'intervient QUE lorsque la transaction CI-V a réellement réussi,
jamais avant l'appel ni en cas d'échec.

Deux formes d'échec distinctes depuis le chantier "Correction DATA
Mode IC-7300" (2026-08-05) : une exception (port perdu, etc., déjà
couvert avant ce chantier) ET un rejet NG de la radio SANS exception
(controller.set_data_mode() retourne False -- le cas réellement
observé sur le terrain, qui était auparavant traité à tort comme un
succès). Les deux doivent laisser status.data_mode inchangé et
retourner False.
"""

import pytest

from apps.cat_server.radio_service import RadioService


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeController:
    def __init__(self, connected=True, raise_on_set_data_mode=None, set_data_mode_result=True):
        self.connected = connected
        self.calls = []
        self._raise_on_set_data_mode = raise_on_set_data_mode
        self._set_data_mode_result = set_data_mode_result

    def set_data_mode(self, enabled):
        self.calls.append(enabled)
        if self._raise_on_set_data_mode is not None:
            raise self._raise_on_set_data_mode
        return self._set_data_mode_result


@pytest.fixture
def service(qapp):
    return RadioService(port="COM_TEST")


# ------------------------------------------------------------------
# RadioStatus.data_mode -- valeur par défaut et reset()
# ------------------------------------------------------------------

def test_data_mode_defaults_to_false(service):
    assert service.status.data_mode is False
    assert service.data_mode is False


def test_reset_sets_data_mode_back_to_false(service):
    service.status.data_mode = True

    service.status.reset()

    assert service.status.data_mode is False


# ------------------------------------------------------------------
# Radio non connectée -- aucun appel, aucune modification de status
# ------------------------------------------------------------------

def test_set_data_mode_does_nothing_when_not_connected(service):
    service.controller = _FakeController(connected=False)
    before = service.status.data_mode

    result = service.set_data_mode(True)

    assert result is False
    assert service.controller.calls == []
    assert service.status.data_mode == before


# ------------------------------------------------------------------
# Succès -- status.data_mode mis à jour seulement APRÈS la transaction
# ------------------------------------------------------------------

def test_set_data_mode_true_calls_controller_and_returns_true(service):
    service.controller = _FakeController(connected=True)

    result = service.set_data_mode(True)

    assert result is True
    assert service.controller.calls == [True]
    assert service.status.data_mode is True
    assert service.data_mode is True


def test_set_data_mode_false_calls_controller_and_returns_true(service):
    service.status.data_mode = True
    service.controller = _FakeController(connected=True)

    result = service.set_data_mode(False)

    assert result is True
    assert service.controller.calls == [False]
    assert service.status.data_mode is False


# ------------------------------------------------------------------
# Échec (exception du contrôleur) -- status.data_mode JAMAIS modifié
# ------------------------------------------------------------------

def test_set_data_mode_catches_controller_exception_and_returns_false(service):
    service.controller = _FakeController(connected=True, raise_on_set_data_mode=RuntimeError("port perdu"))

    result = service.set_data_mode(True)

    assert result is False
    assert service.status.last_error == "port perdu"


def test_set_data_mode_does_not_change_status_on_exception(service):
    """Point explicitement demandé : en cas d'échec de la transaction, status.data_mode ne doit pas être modifié."""

    service.status.data_mode = False
    service.controller = _FakeController(connected=True, raise_on_set_data_mode=RuntimeError("port perdu"))

    service.set_data_mode(True)

    assert service.status.data_mode is False


def test_set_data_mode_does_not_reset_an_existing_true_status_on_exception(service):
    """Même vérification en partant d'un état déjà True : l'échec ne doit pas non plus le repasser à False."""

    service.status.data_mode = True
    service.controller = _FakeController(connected=True, raise_on_set_data_mode=RuntimeError("port perdu"))

    service.set_data_mode(False)

    assert service.status.data_mode is True


def test_set_data_mode_emits_error_signal_on_failure(service):
    service.controller = _FakeController(connected=True, raise_on_set_data_mode=RuntimeError("port perdu"))

    received = []
    service.error.connect(lambda msg: received.append(msg))

    service.set_data_mode(True)

    assert received == ["port perdu"]


# ------------------------------------------------------------------
# Échec (NG de la radio, SANS exception) -- le cas réellement observé
# sur le terrain (chantier "Correction DATA Mode IC-7300", 2026-08-05) :
# le contrôleur ne lève rien, il retourne False. Avant cette correction,
# ce cas était traité comme un succès (status.data_mode mis à jour,
# True renvoyé) -- exactement le bug qui laissait WSJT-X croire le mode
# DATA actif alors que la radio l'avait rejeté.
# ------------------------------------------------------------------

def test_set_data_mode_returns_false_when_controller_reports_ng_without_exception(service):
    service.controller = _FakeController(connected=True, set_data_mode_result=False)

    result = service.set_data_mode(True)

    assert result is False


def test_set_data_mode_does_not_change_status_on_ng_without_exception(service):
    service.status.data_mode = False
    service.controller = _FakeController(connected=True, set_data_mode_result=False)

    service.set_data_mode(True)

    assert service.status.data_mode is False


def test_set_data_mode_does_not_reset_an_existing_true_status_on_ng_without_exception(service):
    service.status.data_mode = True
    service.controller = _FakeController(connected=True, set_data_mode_result=False)

    service.set_data_mode(False)

    assert service.status.data_mode is True


def test_set_data_mode_sets_last_error_on_ng_without_exception(service):
    service.controller = _FakeController(connected=True, set_data_mode_result=False)

    service.set_data_mode(True)

    assert "rejeté" in service.status.last_error


def test_set_data_mode_emits_error_signal_on_ng_without_exception(service):
    service.controller = _FakeController(connected=True, set_data_mode_result=False)

    received = []
    service.error.connect(lambda msg: received.append(msg))

    service.set_data_mode(True)

    assert len(received) == 1
    assert "rejeté" in received[0]
