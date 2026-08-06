"""
Tests de libraries/cat/smeter.py.

Vérifie SMeterManager (commande CI-V 15 02, "Reads the S-meter level")
contre les valeurs exactes du guide de référence CI-V officiel Icom
(IC-7300MK2), sans aucun matériel réel : structure de trame, décodage
BCD 2 octets, les 3 points d'ancrage documentés (S0/S9/S9+60dB), et
l'interpolation linéaire (non documentée par Icom, propre à ce module)
pour les valeurs intermédiaires.
"""

import pytest

from libraries.cat.smeter import SMeterManager


@pytest.fixture
def manager():
    return SMeterManager()


# ------------------------------------------------------------------
# Structure de trame (mêmes constantes d'adresse que ptt.py/mode.py)
# ------------------------------------------------------------------

def test_read_command_frame_structure(manager):
    frame = manager.build_read_command()

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x15, 0x02, 0xFD))


# ------------------------------------------------------------------
# Décodage du niveau brut (BCD 2 octets, même format que KeyingSpeedManager)
# ------------------------------------------------------------------

def test_decode_level_at_s0(manager):
    assert manager.decode_level(bytes((0x00, 0x00))) == 0


def test_decode_level_at_s9(manager):
    assert manager.decode_level(bytes((0x01, 0x20))) == 120


def test_decode_level_at_s9_plus_60db(manager):
    assert manager.decode_level(bytes((0x02, 0x41))) == 241


def test_decode_level_rejects_incomplete_data(manager):
    with pytest.raises(ValueError):
        manager.decode_level(bytes((0x01,)))


def test_decode_level_rejects_out_of_range_bcd(manager):
    # BCD "0F 0F" décode arithmétiquement en dehors de 0-255
    with pytest.raises(ValueError):
        manager.decode_level(bytes((0x0F, 0x0F)))


# ------------------------------------------------------------------
# Les 3 points d'ancrage OFFICIELLEMENT documentés -- voir docstring
# du module (aucune autre valeur n'est garantie par Icom)
# ------------------------------------------------------------------

def test_s_display_at_documented_s0_anchor(manager):
    assert manager.decode_s_display(bytes((0x00, 0x00))) == "S0"


def test_s_display_at_documented_s9_anchor(manager):
    assert manager.decode_s_display(bytes((0x01, 0x20))) == "S9"


def test_s_display_at_documented_s9_plus_60db_anchor(manager):
    assert manager.decode_s_display(bytes((0x02, 0x41))) == "S9+60dB"


# ------------------------------------------------------------------
# Interpolation linéaire entre les points d'ancrage (propre à ce
# module, PAS une valeur garantie par Icom -- voir docstring)
# ------------------------------------------------------------------

def test_s_display_below_s0_clamps_to_s0():
    assert SMeterManager.level_to_s_display(-5) == "S0"


def test_s_display_at_half_of_s9_is_roughly_s4_or_s5():
    # 60/120 * 9 = 4.5 -> round() en "banker's rounding" Python -> 4
    assert SMeterManager.level_to_s_display(60) == "S4"


def test_s_display_just_below_s9_never_reports_s9():
    assert SMeterManager.level_to_s_display(119) == "S8"


def test_s_display_at_quarter_way_between_s9_and_plus_60db():
    # (150-120)/(241-120)*60 = 14.876... -> round() = 15
    assert SMeterManager.level_to_s_display(150) == "S9+15dB"


def test_s_display_above_documented_maximum_clamps_to_plus_60db():
    assert SMeterManager.level_to_s_display(255) == "S9+60dB"


@pytest.mark.parametrize("level", list(range(0, 256, 17)))
def test_s_display_never_raises_across_full_documented_range(level):
    """Toute valeur brute 0-255 (plage documentée du niveau CI-V) doit produire un texte, jamais une exception."""

    result = SMeterManager.level_to_s_display(level)

    assert isinstance(result, str) and result.startswith("S")
