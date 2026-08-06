"""
Tests de CATEngine.set_data_mode() (libraries/cat/cat_engine.py).

Vérifie que set_data_mode() transacte exactement la trame construite
par DataModeManager (commande CI-V 1A 06), pour l'activation et la
désactivation -- jamais un vrai port série, transact() est remplacé
par un double qui enregistre la trame reçue, même méthode que
tests/test_cat_engine_smeter.py.

Vérifie également, suite au chantier "Correction DATA Mode IC-7300"
(2026-08-05), que la valeur de retour reflète fidèlement la réponse
CI-V réelle (ACK -> True, NG -> False) : avant cette correction,
set_data_mode() ne retournait rien et un NG de la radio n'était jamais
détecté par l'appelant.
"""

import pytest

from libraries.cat.cat_engine import CATEngine
from libraries.cat.data_mode import DataModeManager

_ACK_RESPONSE = bytes((0xFE, 0xFE, 0xE0, 0x94, 0xFB, 0xFD))
_NG_RESPONSE = bytes((0xFE, 0xFE, 0xE0, 0x94, 0xFA, 0xFD))


@pytest.fixture
def engine():
    return CATEngine(port="COM_TEST")


def test_set_data_mode_transacts_the_exact_frame_when_enabling(engine):
    recorded = []
    engine.transact = lambda frame: recorded.append(frame) or _ACK_RESPONSE

    engine.set_data_mode(True)

    assert recorded == [DataModeManager().build_set_command(True)]


def test_set_data_mode_transacts_the_exact_frame_when_disabling(engine):
    recorded = []
    engine.transact = lambda frame: recorded.append(frame) or _ACK_RESPONSE

    engine.set_data_mode(False)

    assert recorded == [DataModeManager().build_set_command(False)]


# ------------------------------------------------------------------
# Valeur de retour -- reflète la vraie réponse CI-V (ACK/NG), plus
# jamais None (voir docstring du module de test et de CATEngine)
# ------------------------------------------------------------------

def test_set_data_mode_returns_true_on_ack(engine):
    engine.transact = lambda frame: _ACK_RESPONSE

    assert engine.set_data_mode(True) is True


def test_set_data_mode_returns_false_on_ng(engine):
    """Le cas réellement observé sur le terrain : la radio rejette la commande (filtre invalide, etc.)."""

    engine.transact = lambda frame: _NG_RESPONSE

    assert engine.set_data_mode(True) is False


def test_set_data_mode_returns_false_on_empty_response():
    """Timeout / absence de réponse : jamais traité comme un succès non plus."""

    engine = CATEngine(port="COM_TEST")
    engine.transact = lambda frame: b""

    assert engine.set_data_mode(True) is False


# ------------------------------------------------------------------
# Non-régression : CATEngine construit toujours son manager DATA mode
# ------------------------------------------------------------------

def test_engine_exposes_data_mode_manager():
    e = CATEngine(port="COM_TEST")

    assert e.data_mode is not None
    assert isinstance(e.data_mode, DataModeManager)
