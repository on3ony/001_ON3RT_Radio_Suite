"""
Tests de CATEngine.send_cw_message()/stop_cw_message()/set_keying_speed()
(libraries/cat/cat_engine.py) -- étape 2 du backend CI-V texte.

Vérifie uniquement que ces trois nouvelles méthodes construisent la
trame attendue (via CWMessageManager/KeyingSpeedManager, déjà testés
unitairement) et la transmettent telle quelle à transact() -- jamais
de vrai port série ici, transact() est remplacé par un double qui
enregistre les trames reçues sur l'instance elle-même (pas d'état
partagé entre tests).

Non-régression : les méthodes déjà existantes (read_frequency,
set_ptt, etc.) ne sont pas modifiées par cette étape -- pas retestées
ici, déjà couvertes ailleurs (tests/test_radio_service_ptt.py, et la
non-régression de la suite complète).
"""

import pytest

from libraries.cat.cat_engine import CATEngine
from libraries.cat.cw_message import CWMessageManager
from libraries.cat.keying_speed import KeyingSpeedManager


@pytest.fixture
def engine():
    e = CATEngine(port="COM_TEST")
    e.recorded_frames = []
    e.transact = lambda frame: e.recorded_frames.append(frame) or b""
    return e


def test_send_cw_message_transacts_the_exact_frame_from_cw_message_manager(engine):
    engine.send_cw_message("CQ ON3RT")

    expected = CWMessageManager().build_send_command("CQ ON3RT")

    assert engine.recorded_frames == [expected]


def test_stop_cw_message_transacts_the_exact_stop_frame(engine):
    engine.stop_cw_message()

    expected = CWMessageManager().build_stop_command()

    assert engine.recorded_frames == [expected]


def test_set_keying_speed_transacts_the_exact_frame_from_keying_speed_manager(engine):
    engine.set_keying_speed(25)

    expected = KeyingSpeedManager().build_set_command(25)

    assert engine.recorded_frames == [expected]


def test_send_cw_message_propagates_value_error_for_oversized_text(engine):
    with pytest.raises(ValueError):
        engine.send_cw_message("A" * 31)

    assert engine.recorded_frames == []


def test_set_keying_speed_propagates_value_error_for_out_of_range_wpm(engine):
    with pytest.raises(ValueError):
        engine.set_keying_speed(100)

    assert engine.recorded_frames == []


# ------------------------------------------------------------------
# Non-régression : CATEngine construit toujours ses managers existants
# ------------------------------------------------------------------

def test_engine_still_exposes_all_pre_existing_managers():
    e = CATEngine(port="COM_TEST")

    assert e.frequency is not None
    assert e.mode is not None
    assert e.ptt is not None
    assert e.vfo is not None
    assert e.cw_message is not None
    assert e.keying_speed is not None
