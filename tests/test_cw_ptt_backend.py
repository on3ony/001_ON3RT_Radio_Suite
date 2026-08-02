"""
Tests de apps/cat_server/cw_ptt_backend.py.

Double de test pour PTTGuard (jamais le vrai matériel, jamais une
vraie radio) -- même principe que les tests de PTTGuard/
TransmissionService eux-mêmes. Une vérification statique du code
source confirme aussi que PTTKeyerBackend ne connaît jamais le Morse
ni le TimingEngine (contrainte explicitement demandée).
"""

import ast
import inspect

import pytest

import apps.cat_server.cw_ptt_backend as cw_ptt_backend_module
from apps.cat_server.cw_ptt_backend import PTTKeyerBackend


class _FakePTTGuard:
    """Double de test pour PTTGuard -- jamais de vraie radio, jamais de vrai PTT."""

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


@pytest.fixture
def ptt_guard():
    return _FakePTTGuard()


@pytest.fixture
def backend(ptt_guard):
    return PTTKeyerBackend(ptt_guard=ptt_guard)


# ------------------------------------------------------------------
# Contrat KeyerBackend
# ------------------------------------------------------------------

def test_name_is_ptt(backend):
    assert PTTKeyerBackend.name == "ptt"


def test_is_available_is_always_true(backend):
    assert backend.is_available() is True


# ------------------------------------------------------------------
# key_down() / key_up() -- delegation pure vers PTTGuard
# ------------------------------------------------------------------

def test_key_down_calls_ptt_guard_key(backend, ptt_guard):
    backend.key_down(owner="cw_service")
    assert ptt_guard.key_calls == ["cw_service"]


def test_key_down_without_owner_defaults_to_none(backend, ptt_guard):
    backend.key_down()
    assert ptt_guard.key_calls == [None]


def test_key_up_calls_ptt_guard_release(backend, ptt_guard):
    backend.key_up()
    assert ptt_guard.release_calls == 1


def test_several_key_down_and_key_up_calls_are_all_forwarded_in_order(backend, ptt_guard):
    backend.key_down(owner="a")
    backend.key_up()
    backend.key_down(owner="b")
    backend.key_up()

    assert ptt_guard.key_calls == ["a", "b"]
    assert ptt_guard.release_calls == 2


def test_backend_never_creates_its_own_ptt_guard_instance(ptt_guard):
    """PTTKeyerBackend reçoit toujours PTTGuard en injection -- jamais une seconde instance."""

    backend = PTTKeyerBackend(ptt_guard=ptt_guard)
    assert backend._ptt_guard is ptt_guard


# ------------------------------------------------------------------
# Propagation des erreurs -- jamais absorbees ici
# ------------------------------------------------------------------

def test_key_down_propagates_ptt_guard_exceptions():
    class _FakePTTError(RuntimeError):
        pass

    guard = _FakePTTGuard(raise_on_key=_FakePTTError("radio non connectée"))
    backend = PTTKeyerBackend(ptt_guard=guard)

    with pytest.raises(_FakePTTError, match="radio non connectée"):
        backend.key_down(owner="cw_service")


# ------------------------------------------------------------------
# Indépendance totale vis-à-vis du Morse/TimingEngine (contrainte explicite)
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


def test_module_never_imports_morse_or_timing_related_code():
    """
    PTTKeyerBackend ne doit connaître ni le Morse ni le TimingEngine --
    seul CWService a cette intelligence (contrainte explicitement
    demandée). Vérifié statiquement (analyse du code source), pas
    seulement par l'absence dans sys.modules.
    """

    forbidden_substrings = ("morse", "timing", "cw_service")
    imported_names = _imported_module_names(cw_ptt_backend_module)

    for name in imported_names:
        lowered = name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lowered, f"import interdit trouvé dans cw_ptt_backend.py : {name}"


def test_module_only_imports_ptt_guard_beyond_the_standard_library_future_import():
    imported_names = _imported_module_names(cw_ptt_backend_module)
    assert imported_names == ["__future__", "apps.cat_server.ptt_guard"]
