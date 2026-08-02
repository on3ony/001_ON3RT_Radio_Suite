"""
Tests de libraries/cw/element_driver.py.

ElementDriver implémente le contrat CWDriver (libraries/cw/cw_driver.py)
-- ces tests l'exercent directement, sans CWService, avec de simples
callbacks Python (pas de signaux Qt) et NullKeyerBackend
(libraries/cw/keyer_backend.py) comme double de test -- jamais un vrai
PTTGuard, jamais de matériel réel.

ElementDriver enchaîne ses éléments via de vraies instances QTimer :
_pump_until() fait tourner la boucle d'événements Qt jusqu'à ce qu'une
condition soit vraie, avec un délai de sécurité borné pour ne jamais
bloquer indéfiniment un test en cas de régression.
"""

import ast
import inspect

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from libraries.cw.element_driver import ElementDriver
from libraries.cw.keyer_backend import NullKeyerBackend


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


class _CallbackRecorder:
    """Double de test pour les callbacks du contrat CWDriver -- jamais de signal Qt."""

    def __init__(self):
        self.started_calls = 0
        self.progress_calls: list[int] = []
        self.finished_calls = 0
        self.error_calls: list[str] = []

    def on_started(self):
        self.started_calls += 1

    def on_progress(self, char_index):
        self.progress_calls.append(char_index)

    def on_finished(self):
        self.finished_calls += 1

    def on_error(self, message):
        self.error_calls.append(message)


def _pump_until(condition, timeout_ms=3000):
    """Fait tourner la boucle d'événements Qt jusqu'à condition() vrai ou expiration du délai."""

    loop = QEventLoop()

    check_timer = QTimer()
    check_timer.timeout.connect(lambda: loop.quit() if condition() else None)
    check_timer.start(5)

    timeout_timer = QTimer()
    timeout_timer.setSingleShot(True)
    timeout_timer.timeout.connect(loop.quit)
    timeout_timer.start(timeout_ms)

    loop.exec()

    check_timer.stop()
    timeout_timer.stop()


def _wait_ms(duration_ms):
    loop = QEventLoop()
    QTimer.singleShot(duration_ms, loop.quit)
    loop.exec()


@pytest.fixture
def backend():
    return NullKeyerBackend()


@pytest.fixture
def recorder():
    return _CallbackRecorder()


@pytest.fixture
def driver(qapp, backend):
    return ElementDriver(backend)


def _start(driver, recorder, text, wpm=60, farnsworth_wpm=None, owner="test"):
    driver.start(
        text, wpm, farnsworth_wpm, owner,
        recorder.on_started, recorder.on_progress, recorder.on_finished, recorder.on_error,
    )


# ------------------------------------------------------------------
# Contrat CWDriver -- forme minimale
# ------------------------------------------------------------------

def test_driver_exposes_start_and_stop():
    assert hasattr(ElementDriver, "start")
    assert hasattr(ElementDriver, "stop")


# ------------------------------------------------------------------
# Cycle nominal
# ------------------------------------------------------------------

def test_on_started_is_called(driver, recorder):
    _start(driver, recorder, "A")
    _pump_until(lambda: recorder.started_calls > 0)
    assert recorder.started_calls == 1


def test_on_finished_is_called_and_backend_is_released(driver, recorder, backend):
    _start(driver, recorder, "A")  # A = .- -> 2 key_down, 2 key_up (1 intra + 1 final)
    _pump_until(lambda: recorder.finished_calls > 0)

    assert recorder.finished_calls == 1
    assert backend.key_down_calls == 2
    assert backend.key_up_calls == 2
    assert backend.is_keyed is False


def test_owner_is_forwarded_to_key_down(driver, recorder, backend):
    _start(driver, recorder, "A", owner="mon_proprietaire")
    _pump_until(lambda: recorder.finished_calls > 0)
    assert backend.last_owner == "mon_proprietaire"


def test_on_progress_is_called_once_per_character(driver, recorder):
    _start(driver, recorder, "SOS")
    _pump_until(lambda: recorder.finished_calls > 0)

    assert recorder.progress_calls == [0, 1, 2]


def test_empty_text_finishes_without_any_key_down_call(driver, recorder, backend):
    _start(driver, recorder, "")
    _pump_until(lambda: recorder.finished_calls > 0)

    assert backend.key_down_calls == 0
    # key_up() de securite final tente systematiquement, meme sans
    # aucun key_down() prealable -- voir _finish_successfully().
    assert backend.key_up_calls == 1


# ------------------------------------------------------------------
# Erreur synchrone au demarrage (start() leve, avant tout callback)
# ------------------------------------------------------------------

def test_invalid_wpm_raises_synchronously(driver, recorder, backend):
    with pytest.raises(ValueError):
        _start(driver, recorder, "A", wpm=0)

    assert recorder.started_calls == 0
    assert backend.key_down_calls == 0


# ------------------------------------------------------------------
# Erreur pendant l'emission (jamais une exception -- toujours on_error)
# ------------------------------------------------------------------

def test_backend_exception_during_key_down_calls_on_error(qapp, recorder):
    driver = ElementDriver(_FailingKeyDownBackend())
    _start(driver, recorder, "A")

    _pump_until(lambda: len(recorder.error_calls) > 0)

    assert recorder.error_calls == ["radio déconnectée"]
    assert recorder.finished_calls == 0


def test_backend_exception_during_key_down_still_attempts_key_up(qapp, recorder):
    backend = _FailingKeyDownBackend()
    driver = ElementDriver(backend)
    _start(driver, recorder, "A")

    _pump_until(lambda: len(recorder.error_calls) > 0)
    assert backend.key_up_calls >= 1


def test_error_during_safety_key_up_does_not_raise(qapp, recorder):
    """_safe_key_up() doit absorber une exception de key_up() sans jamais planter ElementDriver."""

    backend = _FailingKeyDownBackend(fail_key_up=True)
    driver = ElementDriver(backend)

    _start(driver, recorder, "A")  # ne doit lever aucune exception
    _pump_until(lambda: len(recorder.error_calls) > 0)

    assert recorder.error_calls == ["radio déconnectée"]


# ------------------------------------------------------------------
# stop() -- relachement immediat, y compris avant le demarrage differe
# ------------------------------------------------------------------

def test_stop_releases_the_backend_immediately_mid_emission(qapp, backend):
    driver = ElementDriver(backend)
    recorder = _CallbackRecorder()
    _start(driver, recorder, "PARIS PARIS", wpm=5)  # lent : le temps d'arreter en plein milieu

    _wait_ms(200)
    driver.stop()

    assert backend.is_keyed is False


def test_stop_called_before_the_deferred_start_fires_cancels_it_entirely(qapp, backend):
    """
    Correction d'une race pre-existante dans l'ancien CWService : stop()
    appele immediatement apres start() (avant que la minuterie differee
    ne se declenche) doit empecher tout demarrage ulterieur -- jamais de
    on_started() ni de key_down() apres un stop() aussi rapide.
    """

    driver = ElementDriver(backend)
    recorder = _CallbackRecorder()

    _start(driver, recorder, "PARIS")
    driver.stop()  # avant meme le premier tour de boucle d'evenements

    _wait_ms(200)  # laisse tourner la boucle : une minuterie fantome se declencherait ici

    assert recorder.started_calls == 0
    assert backend.key_down_calls == 0


def test_stop_is_safe_to_call_without_any_start(driver):
    driver.stop()  # ne doit jamais lever


def test_calling_stop_twice_in_a_row_is_safe(qapp, backend):
    driver = ElementDriver(backend)
    recorder = _CallbackRecorder()
    _start(driver, recorder, "PARIS", wpm=5)

    _wait_ms(200)
    driver.stop()
    driver.stop()  # ne doit jamais lever ni rien changer de plus


# ------------------------------------------------------------------
# Contrainte explicite : jamais de journalisation, jamais de Qt visible
# depuis le contrat -- verifie statiquement sur le code source reel.
# ------------------------------------------------------------------

def _imported_module_names(module) -> list[str]:
    source = inspect.getsource(module)
    tree = ast.parse(source)

    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)

    return names


def test_module_never_imports_the_logger():
    """
    Un CWDriver ne journalise jamais (contrainte explicite du contrat
    CWDriver) -- verifie que element_driver.py n'importe meme pas
    CWLogger, pas seulement qu'il ne l'appelle pas.
    """

    import libraries.cw.element_driver as element_driver_module

    imported_names = _imported_module_names(element_driver_module)
    for name in imported_names:
        assert "logger" not in name.lower(), f"import interdit trouvé dans element_driver.py : {name}"


def test_module_never_imports_radio_service_or_ptt_guard():
    import libraries.cw.element_driver as element_driver_module

    imported_names = _imported_module_names(element_driver_module)
    forbidden_substrings = ("radio_service", "ptt_guard", "cw_service", "cat_server")

    for name in imported_names:
        lowered = name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lowered, f"import interdit trouvé dans element_driver.py : {name}"
