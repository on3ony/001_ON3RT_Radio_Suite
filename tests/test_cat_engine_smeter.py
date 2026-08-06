"""
Tests de CATEngine.read_smeter() (libraries/cat/cat_engine.py).

Vérifie que read_smeter() retourne bien (level, display) -- level (0-255)
la donnée de RÉFÉRENCE, display (ex. "S9") une représentation dérivée,
voir docstring de la méthode et status.py -- à partir d'une trame CI-V
0x15 0x02 simulée (jamais un vrai port série, transact() est remplacé
par un double qui retourne une trame construite à la main).
"""

import pytest

from libraries.cat.cat_engine import CATEngine


@pytest.fixture
def engine():
    return CATEngine(port="COM_TEST")


def test_read_smeter_returns_level_and_display_at_s9(engine):
    engine.transact = lambda frame: bytes((0xFE, 0xFE, 0xE0, 0x94, 0x15, 0x02, 0x01, 0x20, 0xFD))

    level, display = engine.read_smeter()

    assert level == 120
    assert display == "S9"


def test_read_smeter_returns_level_and_display_at_s0(engine):
    engine.transact = lambda frame: bytes((0xFE, 0xFE, 0xE0, 0x94, 0x15, 0x02, 0x00, 0x00, 0xFD))

    level, display = engine.read_smeter()

    assert level == 0
    assert display == "S0"


def test_read_smeter_returns_none_none_on_empty_response(engine):
    engine.transact = lambda frame: b""

    assert engine.read_smeter() == (None, None)


def test_read_smeter_returns_none_none_on_a_foreign_meter_subcommand(engine):
    """Une réponse Po-mètre (15 11) ne doit jamais être interprétée comme un S-mètre."""

    engine.transact = lambda frame: bytes((0xFE, 0xFE, 0xE0, 0x94, 0x15, 0x11, 0x00, 0x50, 0xFD))

    assert engine.read_smeter() == (None, None)


def test_read_smeter_transacts_the_exact_frame_from_smeter_manager(engine):
    from libraries.cat.smeter import SMeterManager

    recorded = []
    engine.transact = lambda frame: recorded.append(frame) or bytes((0xFE, 0xFE, 0xE0, 0x94, 0x15, 0x02, 0x00, 0x00, 0xFD))

    engine.read_smeter()

    assert recorded == [SMeterManager().build_read_command()]


# ------------------------------------------------------------------
# Non-régression : CATEngine construit toujours son manager S-mètre
# ------------------------------------------------------------------

def test_engine_exposes_smeter_manager():
    e = CATEngine(port="COM_TEST")

    assert e.smeter is not None
