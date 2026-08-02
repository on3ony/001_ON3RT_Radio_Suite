"""
Tests de libraries/cw/cw_service.py.

Utilise ElementDriver(NullKeyerBackend()) (libraries/cw/element_driver.py,
libraries/cw/keyer_backend.py) comme driver de test -- jamais un vrai
PTTGuard, jamais de matériel réel. Depuis la refonte "driver injecté"
(voir libraries/cw/ARCHITECTURE.md), CWService ne connaît plus ni
MorseEncoder ni TimingEngine ni un backend direct -- ces tests
n'exercent donc plus que le comportement PUBLIC de CWService
(état/request_id/signaux/concurrence/stop()), le pilotage élément par
élément étant déjà couvert séparément par tests/test_element_driver.py.
CWService enchaîne toujours ses callbacks via le driver, qui utilise
lui-même QTimer.singleShot() en interne (voir docstring du module) :
_wait_for_signal() pompe la boucle d'événements Qt jusqu'à réception du
signal attendu, avec un délai de sécurité borné pour ne jamais bloquer
indéfiniment un test en cas de régression.
"""

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from libraries.cw.cw_service import CWService, CWState
from libraries.cw.element_driver import ElementDriver
from libraries.cw.keyer_backend import NullKeyerBackend, NullTextKeyerBackend
from libraries.cw.text_driver import TextDriver


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FailingKeyDownBackend:
    """Double de test : key_down() échoue toujours -- jamais de vrai matériel."""

    name = "failing"

    def __init__(self, fail_key_up: bool = False):
        self.key_up_calls = 0
        self._fail_key_up = fail_key_up

    def is_available(self) -> bool:
        return True

    def key_down(self, owner=None):
        raise RuntimeError("radio déconnectée")

    def key_up(self):
        self.key_up_calls += 1
        if self._fail_key_up:
            raise RuntimeError("échec matériel au relâchement")


def _wait_for_signal(signal, timeout_ms=3000):
    loop = QEventLoop()
    captured = {}

    def _capture(*args):
        captured["args"] = args
        loop.quit()

    signal.connect(_capture)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    signal.disconnect(_capture)

    return captured.get("args")


@pytest.fixture
def backend():
    return NullKeyerBackend()


@pytest.fixture
def driver(qapp, backend):
    return ElementDriver(backend)


@pytest.fixture
def service(driver):
    # WPM eleve : messages courts, tests rapides.
    return CWService(driver=driver, wpm=60)


# ------------------------------------------------------------------
# État initial
# ------------------------------------------------------------------

def test_initial_state_is_idle(service):
    assert service.state is CWState.IDLE


# ------------------------------------------------------------------
# Cycle nominal
# ------------------------------------------------------------------

def test_send_returns_a_request_id_and_transitions_to_sending(service):
    request_id = service.send("A", owner="test")
    assert isinstance(request_id, str)
    assert len(request_id) > 0
    assert service.state is CWState.SENDING


def test_cw_started_is_emitted_with_the_request_id(service):
    request_id = service.send("A", owner="test")
    args = _wait_for_signal(service.cw_started)
    assert args == (request_id,)


def test_cw_finished_is_emitted_and_state_returns_to_idle(service):
    request_id = service.send("A", owner="test")
    args = _wait_for_signal(service.cw_finished)
    assert args == (request_id,)
    assert service.state is CWState.IDLE


def test_backend_is_keyed_down_and_up_and_released_at_the_end(service, backend):
    service.send("A", owner="test")  # A = .- -> 2 key_down, 1 key_up (gap intra) + 1 key_up final
    _wait_for_signal(service.cw_finished)

    assert backend.key_down_calls == 2
    assert backend.key_up_calls == 2
    assert backend.is_keyed is False


def test_owner_is_forwarded_to_key_down(service, backend):
    service.send("A", owner="mon_proprietaire")
    _wait_for_signal(service.cw_finished)
    assert backend.last_owner == "mon_proprietaire"


# ------------------------------------------------------------------
# Progression (une fois par caractere, pas par element Morse)
# ------------------------------------------------------------------

def test_progress_is_emitted_once_per_character(service):
    request_id = service.send("SOS", owner="test")

    progress_events = []
    service.cw_progress.connect(lambda rid, idx, total: progress_events.append((rid, idx, total)))

    _wait_for_signal(service.cw_finished)

    assert progress_events == [
        (request_id, 0, 3),
        (request_id, 1, 3),
        (request_id, 2, 3),
    ]


def test_progress_total_matches_the_source_text_length(service):
    request_id = service.send("CQ DX", owner="test")

    progress_events = []
    service.cw_progress.connect(lambda rid, idx, total: progress_events.append(total))

    _wait_for_signal(service.cw_finished)

    assert all(total == len("CQ DX") for total in progress_events)


# ------------------------------------------------------------------
# Une seule emission active a la fois -- refus explicite
# ------------------------------------------------------------------

def test_send_while_already_sending_returns_none(service):
    service.send("PARIS", owner="premier")
    second_request_id = service.send("DX", owner="second")
    assert second_request_id is None
    service.stop()  # nettoyage


def test_send_while_already_sending_emits_cw_error(service):
    service.send("PARIS", owner="premier")
    service.send("DX", owner="second")  # refuse -- cw_error emis de facon differee

    args = _wait_for_signal(service.cw_error)

    assert args is not None
    _rid, message = args
    assert "premier" in message or "cours" in message
    service.stop()  # nettoyage


def test_send_while_already_sending_does_not_disturb_the_active_emission(service, backend):
    first_request_id = service.send("A", owner="premier")
    service.send("B", owner="second")  # refuse

    args = _wait_for_signal(service.cw_finished)
    assert args == (first_request_id,)
    assert backend.last_owner == "premier"  # jamais "second"


def test_send_is_accepted_again_immediately_after_a_previous_emission_finished(service):
    service.send("A", owner="premier")
    _wait_for_signal(service.cw_finished)

    second_request_id = service.send("B", owner="second")
    assert second_request_id is not None
    assert service.state is CWState.SENDING
    service.stop()


# ------------------------------------------------------------------
# Arret immediat (stop())
# ------------------------------------------------------------------

def test_stop_when_not_sending_does_nothing(service):
    assert service.state is CWState.IDLE
    service.stop()  # ne doit jamais lever
    assert service.state is CWState.IDLE


def test_stop_mid_emission_releases_the_backend_immediately(backend, qapp):
    service = CWService(driver=ElementDriver(backend), wpm=5)  # lent : le temps d'arreter en plein milieu
    service.send("PARIS PARIS", owner="test")

    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()

    service.stop()

    assert backend.is_keyed is False


def test_stop_mid_emission_sets_state_to_stopped(backend, qapp):
    service = CWService(driver=ElementDriver(backend), wpm=5)
    service.send("PARIS", owner="test")

    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()

    service.stop()
    assert service.state is CWState.STOPPED


def test_stop_mid_emission_emits_cw_stopped_with_the_request_id(backend, qapp):
    service = CWService(driver=ElementDriver(backend), wpm=5)
    request_id = service.send("PARIS", owner="test")

    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()

    service.stop()
    args = _wait_for_signal(service.cw_stopped)  # emission differee -- voir docstring du module

    assert args == (request_id,)


def test_stop_prevents_any_further_key_down_calls(backend, qapp):
    service = CWService(driver=ElementDriver(backend), wpm=5)
    service.send("PARIS PARIS PARIS", owner="test")

    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()

    service.stop()
    key_down_calls_at_stop = backend.key_down_calls

    # Laisse tourner la boucle d'evenements : si une minuterie fantome
    # subsistait, elle se declencherait ici.
    loop2 = QEventLoop()
    QTimer.singleShot(500, loop2.quit)
    loop2.exec()

    assert backend.key_down_calls == key_down_calls_at_stop


def test_stop_is_accepted_again_immediately_after_being_stopped(service):
    service.send("PARIS", owner="premier")
    service.stop()

    assert service.state is CWState.STOPPED

    second_request_id = service.send("DX", owner="second")
    assert second_request_id is not None
    assert service.state is CWState.SENDING
    service.stop()


def test_calling_stop_twice_in_a_row_is_safe(backend, qapp):
    service = CWService(driver=ElementDriver(backend), wpm=5)
    service.send("PARIS", owner="test")

    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()

    service.stop()
    service.stop()  # ne doit jamais lever ni rien changer de plus


# ------------------------------------------------------------------
# Gestion des erreurs
# ------------------------------------------------------------------

def test_backend_exception_during_key_down_sets_state_to_error(qapp):
    service = CWService(driver=ElementDriver(_FailingKeyDownBackend()), wpm=20)
    service.send("A", owner="test")
    _wait_for_signal(service.cw_error)  # emission differee -- voir docstring du module
    assert service.state is CWState.ERROR


def test_backend_exception_during_key_down_emits_cw_error_with_the_message(qapp):
    service = CWService(driver=ElementDriver(_FailingKeyDownBackend()), wpm=20)
    request_id = service.send("A", owner="test")

    args = _wait_for_signal(service.cw_error)

    assert args == (request_id, "radio déconnectée")


def test_backend_exception_during_key_down_still_attempts_key_up(qapp):
    backend = _FailingKeyDownBackend()
    service = CWService(driver=ElementDriver(backend), wpm=20)
    service.send("A", owner="test")
    _wait_for_signal(service.cw_error)
    assert backend.key_up_calls >= 1


def test_error_during_cleanup_key_up_does_not_crash(qapp):
    """_safe_key_up() (dans ElementDriver) doit absorber une exception de key_up() sans jamais planter CWService."""

    backend = _FailingKeyDownBackend(fail_key_up=True)
    service = CWService(driver=ElementDriver(backend), wpm=20)

    service.send("A", owner="test")  # ne doit lever aucune exception
    _wait_for_signal(service.cw_error)
    assert service.state is CWState.ERROR


def test_send_is_accepted_again_immediately_after_an_error(qapp):
    service = CWService(driver=ElementDriver(_FailingKeyDownBackend()), wpm=20)
    service.send("A", owner="premier")
    _wait_for_signal(service.cw_error)
    assert service.state is CWState.ERROR

    second_request_id = service.send("B", owner="second")
    assert second_request_id is not None


def test_invalid_wpm_is_caught_and_reported_as_cw_error_not_raised(qapp):
    backend = NullKeyerBackend()
    service = CWService(driver=ElementDriver(backend), wpm=0)  # wpm invalide -- TimingEngine leve ValueError

    request_id = service.send("A", owner="test")
    args = _wait_for_signal(service.cw_error)

    assert request_id is not None
    assert args[0] == request_id
    assert backend.key_down_calls == 0  # jamais atteint le backend


# ------------------------------------------------------------------
# Cas limites
# ------------------------------------------------------------------

def test_empty_text_finishes_without_any_key_down_call(service, backend):
    request_id = service.send("", owner="test")
    assert request_id is not None

    args = _wait_for_signal(service.cw_finished)  # emission differee -- voir docstring du module

    assert args == (request_id,)
    assert service.state is CWState.IDLE
    assert backend.key_down_calls == 0
    # key_up() de securite final tente systematiquement, meme sans
    # aucun key_down() prealable -- voir ElementDriver._finish_successfully().
    assert backend.key_up_calls == 1


def test_text_with_only_unsupported_characters_finishes_without_any_backend_call(service, backend):
    request_id = service.send("€€€", owner="test")
    assert request_id is not None

    _wait_for_signal(service.cw_finished)  # emission differee -- voir docstring du module

    assert service.state is CWState.IDLE
    assert backend.key_down_calls == 0


# ------------------------------------------------------------------
# CWService avec TextDriver -- meme comportement public qu'avec
# ElementDriver, sans aucune distinction de type cote CWService
# (contrainte explicitement validee avant l'etape 5).
# ------------------------------------------------------------------

def test_send_and_finish_work_identically_with_a_text_driver(qapp):
    text_backend = NullTextKeyerBackend()
    service = CWService(driver=TextDriver(text_backend), wpm=60)

    request_id = service.send("CQ DX", owner="test")
    assert isinstance(request_id, str)
    assert service.state is CWState.SENDING

    started_args = _wait_for_signal(service.cw_started)
    assert started_args == (request_id,)

    finished_args = _wait_for_signal(service.cw_finished)
    assert finished_args == (request_id,)
    assert service.state is CWState.IDLE
    assert text_backend.sent_chunks == ["CQ DX"]


def test_progress_is_emitted_with_a_text_driver_just_like_with_an_element_driver(qapp):
    service = CWService(driver=TextDriver(NullTextKeyerBackend()), wpm=60)

    request_id = service.send("SOS", owner="test")

    progress_events = []
    service.cw_progress.connect(lambda rid, idx, total: progress_events.append((rid, idx, total)))

    _wait_for_signal(service.cw_finished)

    assert progress_events == [
        (request_id, 0, 3),
        (request_id, 1, 3),
        (request_id, 2, 3),
    ]


def test_concurrency_refusal_behaves_identically_with_a_text_driver(qapp):
    service = CWService(driver=TextDriver(NullTextKeyerBackend()), wpm=5)

    service.send("PARIS", owner="premier")
    second_request_id = service.send("DX", owner="second")

    assert second_request_id is None
    service.stop()  # nettoyage


def test_stop_releases_a_text_driver_just_like_an_element_driver(qapp):
    text_backend = NullTextKeyerBackend()
    service = CWService(driver=TextDriver(text_backend), wpm=5)

    service.send("CQ DX DE ON3RT", owner="test")

    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()

    service.stop()
    assert service.state is CWState.STOPPED
    assert text_backend.stop_sending_calls == 1


# ------------------------------------------------------------------
# Verification statique : CWService ne connait ni MorseEncoder, ni
# TimingEngine, ni un backend/driver concret, et ne fait jamais de
# test sur le type du driver injecte (isinstance/hasattr sur des noms
# de driver/backend concrets).
# ------------------------------------------------------------------

def test_module_never_imports_morse_timing_or_a_concrete_driver_or_backend():
    import ast
    import inspect

    import libraries.cw.cw_service as cw_service_module

    source = inspect.getsource(cw_service_module)
    tree = ast.parse(source)

    imported_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)

    forbidden_substrings = (
        "morse", "timing", "element_driver", "text_driver", "keyer_backend", "ptt_guard", "radio_service",
    )
    for name in imported_names:
        lowered = name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lowered, f"import interdit trouvé dans cw_service.py : {name}"


def test_module_never_uses_isinstance_to_distinguish_driver_types():
    import ast
    import inspect

    import libraries.cw.cw_service as cw_service_module

    source = inspect.getsource(cw_service_module)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in ("isinstance", "type"), (
                "CWService ne doit jamais tester le type du driver injecté"
            )
