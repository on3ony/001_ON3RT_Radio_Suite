"""
Tests de apps/cat_server/cw_civ_text_backend.py.

Doubles de test pour RadioService et PTTGuard (jamais le vrai matériel,
jamais une vraie radio) -- même principe que tests/test_cw_ptt_backend.py.
Une vérification statique du code source confirme aussi que
CIVTextKeyerBackend n'importe ni le Morse/TimingEngine/CWService, ni
aucun module de libraries/cw/* -- seul le contrat TextBackend est
consommé par le driver, jamais l'inverse.
"""

import ast
import inspect

import pytest

import apps.cat_server.cw_civ_text_backend as cw_civ_text_backend_module
from apps.cat_server.cw_civ_text_backend import CIVTextKeyerBackend
from libraries.cat.cw_message import MAX_MESSAGE_CHARS


class _FakePTTGuard:
    def __init__(self, raise_on_key: Exception | None = None):
        self.key_calls: list[str | None] = []
        self.release_calls = 0
        self._raise_on_key = raise_on_key

    def key(self, owner: str | None = None) -> None:
        if self._raise_on_key is not None:
            raise self._raise_on_key
        self.key_calls.append(owner)

    def release(self) -> None:
        self.release_calls += 1


class _FakeRadioService:
    def __init__(self, keying_speed_result: bool = True, send_message_result: bool = True):
        self.set_keying_speed_calls: list[int] = []
        self.send_cw_message_calls: list[str] = []
        self.stop_cw_message_calls = 0
        self._keying_speed_result = keying_speed_result
        self._send_message_result = send_message_result

    def set_keying_speed(self, wpm: int) -> bool:
        self.set_keying_speed_calls.append(wpm)
        return self._keying_speed_result

    def send_cw_message(self, text: str) -> bool:
        self.send_cw_message_calls.append(text)
        return self._send_message_result

    def stop_cw_message(self) -> bool:
        self.stop_cw_message_calls += 1
        return True


@pytest.fixture
def ptt_guard():
    return _FakePTTGuard()


@pytest.fixture
def radio_service():
    return _FakeRadioService()


@pytest.fixture
def backend(radio_service, ptt_guard):
    return CIVTextKeyerBackend(radio_service=radio_service, ptt_guard=ptt_guard)


# ------------------------------------------------------------------
# Contrat TextBackend
# ------------------------------------------------------------------

def test_name_is_civ_text(backend):
    assert CIVTextKeyerBackend.name == "civ_text"


def test_is_available_is_always_true(backend):
    assert backend.is_available() is True


def test_max_chunk_chars_reuses_the_protocol_limit_from_cw_message_module():
    assert CIVTextKeyerBackend.max_chunk_chars == MAX_MESSAGE_CHARS == 30


def test_backend_never_creates_its_own_dependencies(radio_service, ptt_guard):
    """Injection uniquement -- jamais une seconde instance de RadioService/PTTGuard."""

    backend = CIVTextKeyerBackend(radio_service=radio_service, ptt_guard=ptt_guard)

    assert backend._radio_service is radio_service
    assert backend._ptt_guard is ptt_guard


# ------------------------------------------------------------------
# send_text() -- chemin normal : PTT d'abord, puis vitesse, puis message
# ------------------------------------------------------------------

def test_send_text_keys_ptt_before_anything_else(backend, radio_service, ptt_guard):
    backend.send_text("CQ ON3RT", wpm=25, owner="cw_service")

    assert ptt_guard.key_calls == ["cw_service"]
    assert radio_service.set_keying_speed_calls == [25]
    assert radio_service.send_cw_message_calls == ["CQ ON3RT"]


def test_send_text_without_owner_defaults_to_none(backend, ptt_guard):
    backend.send_text("E", wpm=20)

    assert ptt_guard.key_calls == [None]


def test_send_text_ignores_farnsworth_wpm_entirely(backend, radio_service):
    """
    Décision validée (aucune commande CI-V documentée pour un
    espacement Farnsworth séparé sur l'IC-7300) : farnsworth_wpm est
    accepté par le contrat mais jamais transmis à la radio.
    """

    backend.send_text("PARIS", wpm=20, farnsworth_wpm=8)

    assert radio_service.set_keying_speed_calls == [20]


def test_send_text_does_not_release_ptt_on_success(backend, ptt_guard):
    backend.send_text("E", wpm=20)

    assert ptt_guard.release_calls == 0


# ------------------------------------------------------------------
# send_text() -- PTT refusé : propagation directe, rien d'autre appelé
# ------------------------------------------------------------------

def test_send_text_propagates_ptt_guard_exception_without_touching_radio_service():
    class _FakePTTError(RuntimeError):
        pass

    guard = _FakePTTGuard(raise_on_key=_FakePTTError("PTT déjà activé"))
    radio = _FakeRadioService()
    backend = CIVTextKeyerBackend(radio_service=radio, ptt_guard=guard)

    with pytest.raises(_FakePTTError, match="PTT déjà activé"):
        backend.send_text("E", wpm=20)

    assert radio.set_keying_speed_calls == []
    assert radio.send_cw_message_calls == []
    assert guard.release_calls == 0  # rien à relâcher, PTT jamais activé


# ------------------------------------------------------------------
# send_text() -- échec CI-V après un PTT réussi : PTT relâché, jamais laissé actif
# ------------------------------------------------------------------

def test_send_text_releases_ptt_when_set_keying_speed_fails():
    guard = _FakePTTGuard()
    radio = _FakeRadioService(keying_speed_result=False)
    backend = CIVTextKeyerBackend(radio_service=radio, ptt_guard=guard)

    with pytest.raises(RuntimeError, match="14 0C"):
        backend.send_text("E", wpm=20, owner="cw_service")

    assert guard.key_calls == ["cw_service"]
    assert guard.release_calls == 1
    assert radio.send_cw_message_calls == []  # jamais atteint


def test_send_text_releases_ptt_when_send_cw_message_fails():
    guard = _FakePTTGuard()
    radio = _FakeRadioService(send_message_result=False)
    backend = CIVTextKeyerBackend(radio_service=radio, ptt_guard=guard)

    with pytest.raises(RuntimeError, match="0x17"):
        backend.send_text("E", wpm=20, owner="cw_service")

    assert guard.key_calls == ["cw_service"]
    assert radio.set_keying_speed_calls == [20]
    assert guard.release_calls == 1


# ------------------------------------------------------------------
# stop_sending() -- arrêt CI-V puis relâchement PTT, toujours les deux
# ------------------------------------------------------------------

def test_stop_sending_stops_cw_message_then_releases_ptt(backend, radio_service, ptt_guard):
    backend.stop_sending()

    assert radio_service.stop_cw_message_calls == 1
    assert ptt_guard.release_calls == 1


def test_stop_sending_is_safe_to_call_even_when_nothing_was_sent(backend, radio_service, ptt_guard):
    backend.stop_sending()
    backend.stop_sending()

    assert radio_service.stop_cw_message_calls == 2
    assert ptt_guard.release_calls == 2  # release() est idempotent côté PTTGuard réel


# ------------------------------------------------------------------
# Indépendance totale vis-à-vis du Morse/TimingEngine/CWService/libraries.cw
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


def test_module_never_imports_morse_timing_cw_service_or_libraries_cw():
    """
    CIVTextKeyerBackend ne doit connaître ni le Morse ni le
    TimingEngine ni CWService ni aucun module de libraries/cw/* --
    seul TextDriver (libraries/cw/) connaît ce backend, jamais
    l'inverse. Vérifié statiquement (analyse du code source).
    """

    forbidden_substrings = ("morse", "timing", "cw_service", "libraries.cw")
    imported_names = _imported_module_names(cw_civ_text_backend_module)

    for name in imported_names:
        lowered = name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lowered, f"import interdit trouvé dans cw_civ_text_backend.py : {name}"


def test_module_only_imports_the_expected_dependencies():
    imported_names = _imported_module_names(cw_civ_text_backend_module)

    assert imported_names == [
        "__future__",
        "apps.cat_server.ptt_guard",
        "apps.cat_server.radio_service",
        "libraries.cat.cw_message",
    ]
