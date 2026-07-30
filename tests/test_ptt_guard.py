"""
Tests de apps/cat_server/ptt_guard.py.

RadioService est un double de test minimal (jamais le vrai CAT) :
PTTGuard ne doit dépendre que de son interface publique
(set_ptt(bool) -> bool, signal aboutToDisconnect), jamais de son
implémentation CAT réelle. La validation sur matériel réel (IC-7300)
est faite manuellement par l'utilisateur, comme le reste des garanties
matérielles de la Suite.

_FakeRadioService est un QObject avec un vrai signal aboutToDisconnect
(pas un simple callable) : PTTGuard s'y connecte réellement dans son
constructeur (connexion permanente, voir docstring de ptt_guard.py) —
un double sans signal Qt réel ne pourrait pas exercer ce chemin.

"2aboutToQuit()" (préfixe numérique historique du macro SIGNAL() de
Qt) est la seule forme acceptée par QObject.receivers() dans cette
version de PySide6 — vérifié empiriquement : receivers("aboutToQuit()")
sans préfixe retourne silencieusement 0 même après connexion.
"""

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from apps.cat_server.ptt_guard import DEFAULT_PTT_SAFETY_TIMEOUT_S, PTTError, PTTGuard

_ABOUT_TO_QUIT_SIGNAL = "2aboutToQuit()"


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeRadioService(QObject):
    aboutToDisconnect = Signal()

    def __init__(self, set_ptt_result=True):
        super().__init__()
        self.calls = []
        self._result = set_ptt_result

    def set_ptt(self, state):
        self.calls.append(state)
        return self._result


@pytest.fixture
def radio(qapp):
    return _FakeRadioService()


@pytest.fixture
def guard(radio):
    return PTTGuard(radio_service=radio, safety_timeout_s=30.0)


# ------------------------------------------------------------------
# key() / release() -- cas nominal
# ------------------------------------------------------------------

def test_key_calls_set_ptt_true_and_marks_keyed(guard, radio):
    guard.key(owner="voice")

    assert radio.calls == [True]
    assert guard.is_keyed is True


def test_release_calls_set_ptt_false_and_clears_keyed(guard, radio):
    guard.key(owner="voice")
    guard.release()

    assert radio.calls == [True, False]
    assert guard.is_keyed is False


def test_release_without_prior_key_does_nothing(guard, radio):
    guard.release()

    assert radio.calls == []


def test_release_is_idempotent(guard, radio):
    guard.key(owner="voice")
    guard.release()
    guard.release()

    assert radio.calls == [True, False]  # pas de second False


def test_key_after_release_succeeds_again(guard, radio):
    guard.key(owner="voice")
    guard.release()

    guard.key(owner="voice")

    assert radio.calls == [True, False, True]


# ------------------------------------------------------------------
# Anti-superposition (ressource partagée unique)
# ------------------------------------------------------------------

def test_key_raises_when_already_keyed(guard, radio):
    guard.key(owner="voice")

    with pytest.raises(PTTError):
        guard.key(owner="contest_assistant")

    assert radio.calls == [True]  # le second appel n'a jamais atteint la radio
    assert guard.is_keyed is True  # le premier titulaire reste actif


# ------------------------------------------------------------------
# Échec de la commande CAT
# ------------------------------------------------------------------

def test_key_raises_when_radio_service_reports_failure(qapp):
    radio = _FakeRadioService(set_ptt_result=False)
    guard = PTTGuard(radio_service=radio, safety_timeout_s=30.0)

    with pytest.raises(PTTError):
        guard.key(owner="voice")

    assert guard.is_keyed is False


# ------------------------------------------------------------------
# Gestionnaire de contexte keyed() (appelants synchrones)
# ------------------------------------------------------------------

def test_keyed_context_manager_releases_on_normal_exit(guard, radio):
    with guard.keyed(owner="voice"):
        assert guard.is_keyed is True

    assert guard.is_keyed is False
    assert radio.calls == [True, False]


def test_keyed_context_manager_releases_even_on_exception(guard, radio):
    with pytest.raises(ValueError):
        with guard.keyed(owner="voice"):
            raise ValueError("boom")

    assert guard.is_keyed is False
    assert radio.calls == [True, False]


def test_keyed_context_manager_never_keys_when_key_fails(qapp):
    radio = _FakeRadioService(set_ptt_result=False)
    guard = PTTGuard(radio_service=radio, safety_timeout_s=30.0)

    with pytest.raises(PTTError):
        with guard.keyed(owner="voice"):
            raise AssertionError("le corps du bloc ne doit jamais s'exécuter")

    assert guard.is_keyed is False


# ------------------------------------------------------------------
# Minuterie de sécurité (indépendante du déroulement normal)
# ------------------------------------------------------------------

def test_default_safety_timeout_matches_the_centralized_constant(radio):
    guard = PTTGuard(radio_service=radio)
    assert guard._safety_timeout_s == DEFAULT_PTT_SAFETY_TIMEOUT_S


def test_safety_timeout_forces_release(guard, radio):
    guard.key(owner="voice")

    guard._on_safety_timeout()  # simule le déclenchement, sans attendre le vrai délai

    assert guard.is_keyed is False
    assert radio.calls == [True, False]


def test_key_starts_the_safety_timer(guard, radio):
    guard.key(owner="voice")

    assert guard._safety_timer.isActive()


def test_normal_release_stops_the_safety_timer_before_it_can_fire(guard, radio):
    guard.key(owner="voice")
    guard.release()

    assert not guard._safety_timer.isActive()


# ------------------------------------------------------------------
# Fermeture de l'application pendant une émission
# ------------------------------------------------------------------

def test_key_connects_about_to_quit_and_release_disconnects_it(guard, radio, qapp):
    before = qapp.receivers(_ABOUT_TO_QUIT_SIGNAL)

    guard.key(owner="voice")
    assert qapp.receivers(_ABOUT_TO_QUIT_SIGNAL) == before + 1

    guard.release()
    assert qapp.receivers(_ABOUT_TO_QUIT_SIGNAL) == before


def test_about_to_quit_forces_release(guard, radio, qapp):
    guard.key(owner="voice")

    qapp.aboutToQuit.emit()

    assert guard.is_keyed is False
    assert radio.calls == [True, False]

    # Nettoyage : un vrai aboutToQuit ne se déclenche qu'une fois à la
    # fermeture réelle du processus, mais ce test l'émet manuellement
    # sur l'instance QApplication partagée par toute la session de
    # tests — s'assurer qu'aucune connexion ne fuit vers les tests
    # suivants.
    assert qapp.receivers(_ABOUT_TO_QUIT_SIGNAL) == 0


# ------------------------------------------------------------------
# Fermeture de la liaison CAT pendant une émission (correction après
# essai matériel réel — voir docstring de ptt_guard.py)
# ------------------------------------------------------------------

def test_about_to_disconnect_forces_release_when_keyed(guard, radio):
    guard.key(owner="voice")

    radio.aboutToDisconnect.emit()

    assert guard.is_keyed is False
    assert radio.calls == [True, False]


def test_about_to_disconnect_is_a_no_op_when_ptt_is_not_keyed(guard, radio):
    radio.aboutToDisconnect.emit()

    assert radio.calls == []
    assert guard.is_keyed is False


def test_about_to_disconnect_subscription_is_permanent_across_multiple_key_cycles(guard, radio):
    """
    Contrairement à aboutToQuit (connecté/déconnecté à chaque key()/
    release()), la connexion à aboutToDisconnect est faite une seule
    fois au constructeur et reste active même au repos, entre deux
    émissions — une déconnexion peut survenir à tout moment, pas
    seulement pendant que ce PTTGuard tient le PTT.
    """

    guard.key(owner="voice")
    guard.release()

    guard.key(owner="voice")
    radio.aboutToDisconnect.emit()

    assert guard.is_keyed is False
    assert radio.calls == [True, False, True, False]
