"""
Tests de libraries/cw/text_driver.py.

TextDriver implémente le contrat CWDriver (libraries/cw/cw_driver.py)
pour la famille "text" -- ces tests l'exercent directement, sans
CWService, avec de simples callbacks Python (pas de signaux Qt) et
NullTextKeyerBackend (libraries/cw/keyer_backend.py) comme double de
test -- jamais un vrai CI-V, jamais de matériel réel.
"""

import ast
import inspect

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from libraries.cw.keyer_backend import NullTextKeyerBackend
from libraries.cw.text_driver import TextDriver


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FailingSendTextBackend:
    """Double de test : send_text() échoue toujours -- jamais de vrai matériel."""

    name = "failing_text"
    max_chunk_chars = 30

    def __init__(self, fail_stop_sending: bool = False):
        self.stop_sending_calls = 0
        self._fail_stop_sending = fail_stop_sending

    def is_available(self) -> bool:
        return True

    def send_text(self, text, wpm, farnsworth_wpm, owner=None):
        raise RuntimeError("radio déconnectée")

    def stop_sending(self):
        self.stop_sending_calls += 1
        if self._fail_stop_sending:
            raise RuntimeError("échec matériel à l'arrêt")


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
    return NullTextKeyerBackend()


@pytest.fixture
def recorder():
    return _CallbackRecorder()


@pytest.fixture
def driver(qapp, backend):
    return TextDriver(backend)


def _start(driver, recorder, text, wpm=60, farnsworth_wpm=None, owner="test"):
    driver.start(
        text, wpm, farnsworth_wpm, owner,
        recorder.on_started, recorder.on_progress, recorder.on_finished, recorder.on_error,
    )


# ------------------------------------------------------------------
# Contrat CWDriver -- forme minimale
# ------------------------------------------------------------------

def test_driver_exposes_start_and_stop():
    assert hasattr(TextDriver, "start")
    assert hasattr(TextDriver, "stop")


# ------------------------------------------------------------------
# Cycle nominal
# ------------------------------------------------------------------

def test_on_started_is_called(driver, recorder):
    _start(driver, recorder, "CQ")
    _pump_until(lambda: recorder.started_calls > 0)
    assert recorder.started_calls == 1


def test_on_finished_is_called(driver, recorder):
    _start(driver, recorder, "CQ")
    _pump_until(lambda: recorder.finished_calls > 0)
    assert recorder.finished_calls == 1


def test_send_text_is_called_once_for_a_short_message(driver, recorder, backend):
    _start(driver, recorder, "CQ DX")
    _pump_until(lambda: recorder.finished_calls > 0)
    assert backend.sent_chunks == ["CQ DX"]


def test_send_text_receives_wpm_and_farnsworth(driver, recorder, backend):
    _start(driver, recorder, "CQ", wpm=25, farnsworth_wpm=15)
    _pump_until(lambda: recorder.finished_calls > 0)
    assert backend.last_wpm == 25
    assert backend.last_farnsworth_wpm == 15


def test_owner_is_forwarded_to_send_text(driver, recorder, backend):
    _start(driver, recorder, "CQ", owner="mon_proprietaire")
    _pump_until(lambda: recorder.finished_calls > 0)
    assert backend.last_owner == "mon_proprietaire"


def test_on_progress_is_called_once_per_character(driver, recorder):
    _start(driver, recorder, "SOS")
    _pump_until(lambda: recorder.finished_calls > 0)
    assert recorder.progress_calls == [0, 1, 2]


def test_empty_text_finishes_without_touching_the_backend(driver, recorder, backend):
    _start(driver, recorder, "")
    _pump_until(lambda: recorder.finished_calls > 0)

    assert backend.sent_chunks == []
    assert recorder.finished_calls == 1


def test_text_with_only_unsupported_characters_still_calls_send_text(driver, recorder, backend):
    """
    Différence assumée avec ElementDriver (voir docstring du module) :
    le matériel peut reconnaître des caractères que MorseEncoder ne
    reconnaît pas -- send_text() reçoit toujours le texte brut.
    """

    _start(driver, recorder, "€€€")
    _pump_until(lambda: recorder.finished_calls > 0)

    assert backend.sent_chunks == ["€€€"]


# ------------------------------------------------------------------
# Découpage -- selon backend.max_chunk_chars, jamais une valeur codée
# en dur dans TextDriver.
# ------------------------------------------------------------------

def test_text_shorter_than_max_chunk_chars_is_sent_in_one_call(qapp, recorder):
    backend = NullTextKeyerBackend(max_chunk_chars=30)
    driver = TextDriver(backend)
    _start(driver, recorder, "CQ DX")
    _pump_until(lambda: len(backend.sent_chunks) >= 1)
    assert backend.sent_chunks == ["CQ DX"]


def test_text_longer_than_max_chunk_chars_is_split_into_several_calls(qapp, recorder):
    backend = NullTextKeyerBackend(max_chunk_chars=5)
    driver = TextDriver(backend)
    _start(driver, recorder, "ABCDEFGHIJ")  # 10 caracteres, limite 5
    _pump_until(lambda: len(backend.sent_chunks) >= 2)
    assert backend.sent_chunks == ["ABCDE", "FGHIJ"]


def test_chunks_reassemble_into_the_original_text(qapp, recorder):
    backend = NullTextKeyerBackend(max_chunk_chars=3)
    driver = TextDriver(backend)
    text = "CQ DX DE ON3RT"
    expected_chunk_count = -(-len(text) // 3)  # ceil(len/3)
    _start(driver, recorder, text)
    _pump_until(lambda: len(backend.sent_chunks) >= expected_chunk_count)
    assert "".join(backend.sent_chunks) == text


def test_progress_uses_global_character_positions_across_chunks(qapp, recorder):
    backend = NullTextKeyerBackend(max_chunk_chars=2)
    driver = TextDriver(backend)
    _start(driver, recorder, "ABCD")  # decoupe en "AB"/"CD"
    _pump_until(lambda: recorder.finished_calls > 0)
    assert recorder.progress_calls == [0, 1, 2, 3]


def test_backend_with_no_limit_sends_the_whole_text_in_one_call(qapp, recorder):
    backend = NullTextKeyerBackend(max_chunk_chars=None)
    driver = TextDriver(backend)
    long_text = "A" * 100
    _start(driver, recorder, long_text)
    _pump_until(lambda: len(backend.sent_chunks) >= 1)
    assert backend.sent_chunks == [long_text]
    driver.stop()  # nettoyage -- ne pas laisser une emission longue tourner en arriere-plan


# ------------------------------------------------------------------
# Erreur synchrone au demarrage (start() leve, avant tout callback)
# ------------------------------------------------------------------

def test_invalid_wpm_raises_synchronously(driver, recorder, backend):
    with pytest.raises(ValueError):
        _start(driver, recorder, "CQ", wpm=0)

    assert recorder.started_calls == 0
    assert backend.sent_chunks == []


def test_invalid_wpm_with_empty_text_still_raises_synchronously(driver, recorder):
    """Meme comportement que ElementDriver : la validation WPM est inconditionnelle."""

    with pytest.raises(ValueError):
        _start(driver, recorder, "", wpm=0)


# ------------------------------------------------------------------
# Erreur pendant l'emission (jamais une exception -- toujours on_error)
# ------------------------------------------------------------------

def test_backend_exception_during_send_text_calls_on_error(qapp, recorder):
    driver = TextDriver(_FailingSendTextBackend())
    _start(driver, recorder, "CQ")

    _pump_until(lambda: len(recorder.error_calls) > 0)

    assert recorder.error_calls == ["radio déconnectée"]
    assert recorder.finished_calls == 0


# ------------------------------------------------------------------
# stop() -- relachement immediat, y compris avant le demarrage differe
# ------------------------------------------------------------------

def test_stop_calls_stop_sending(qapp, backend):
    driver = TextDriver(backend)
    recorder = _CallbackRecorder()
    _start(driver, recorder, "CQ DX DE ON3RT", wpm=5)  # lent : le temps d'arreter en plein milieu

    _wait_ms(200)
    driver.stop()

    assert backend.stop_sending_calls == 1


def test_stop_called_before_the_deferred_start_fires_cancels_it_entirely(qapp, backend):
    driver = TextDriver(backend)
    recorder = _CallbackRecorder()

    _start(driver, recorder, "CQ DX")
    driver.stop()  # avant meme le premier tour de boucle d'evenements

    _wait_ms(200)

    assert recorder.started_calls == 0
    assert backend.sent_chunks == []


def test_stop_is_safe_to_call_without_any_start(driver):
    driver.stop()  # ne doit jamais lever


def test_calling_stop_twice_in_a_row_is_safe(qapp, backend):
    driver = TextDriver(backend)
    recorder = _CallbackRecorder()
    _start(driver, recorder, "CQ", wpm=5)

    _wait_ms(200)
    driver.stop()
    driver.stop()  # ne doit jamais lever ni rien changer de plus


def test_error_during_stop_sending_does_not_raise(qapp):
    backend = _FailingSendTextBackend(fail_stop_sending=True)
    driver = TextDriver(backend)
    driver.stop()  # ne doit jamais lever, meme si stop_sending() echoue


# ------------------------------------------------------------------
# Contrainte explicite : jamais de journalisation, jamais de
# dependance a un protocole/matériel precis -- verifie statiquement.
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
    import libraries.cw.text_driver as text_driver_module

    imported_names = _imported_module_names(text_driver_module)
    for name in imported_names:
        assert "logger" not in name.lower(), f"import interdit trouvé dans text_driver.py : {name}"


def test_module_never_imports_any_protocol_or_hardware_specific_code():
    """
    TextDriver ne doit connaître ni le CI-V, ni RadioService, ni un
    Winkeyer, ni Hamlib -- seule la propriété max_chunk_chars du
    backend est utilisée (contrainte explicitement demandée).
    """

    import libraries.cw.text_driver as text_driver_module

    imported_names = _imported_module_names(text_driver_module)
    forbidden_substrings = (
        "radio_service", "ptt_guard", "cw_service", "cat_server",
        "civ", "hamlib", "winkeyer", "cat.",
    )

    for name in imported_names:
        lowered = name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lowered, f"import interdit trouvé dans text_driver.py : {name}"
