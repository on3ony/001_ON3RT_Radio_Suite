"""
Tests de libraries/cat/keying_speed.py.

Vérifie KeyingSpeedManager (commande CI-V 14 0C, "Sets or reads the
keying speed") contre les valeurs exactes du guide de référence CI-V
officiel Icom (IC-7300MK2), sans aucun matériel réel : structure de
trame, encodage BCD 2 octets, plage documentée 6-48 WPM <-> 0-255,
et le round-trip encodage/décodage.
"""

import pytest

from libraries.cat.keying_speed import MAX_WPM, MIN_WPM, KeyingSpeedManager


@pytest.fixture
def manager():
    return KeyingSpeedManager()


# ------------------------------------------------------------------
# Structure de trame (mêmes constantes d'adresse que ptt.py/mode.py)
# ------------------------------------------------------------------

def test_read_command_frame_structure(manager):
    frame = manager.build_read_command()

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x14, 0x0C, 0xFD))


# ------------------------------------------------------------------
# Bornes documentées : 6 WPM = niveau 0 (00 00), 48 WPM = niveau 255 (02 55)
# ------------------------------------------------------------------

def test_set_command_at_minimum_wpm_is_level_zero(manager):
    frame = manager.build_set_command(MIN_WPM)

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x14, 0x0C, 0x00, 0x00, 0xFD))


def test_set_command_at_maximum_wpm_is_level_255(manager):
    frame = manager.build_set_command(MAX_WPM)

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x14, 0x0C, 0x02, 0x55, 0xFD))


def test_set_command_at_midpoint_wpm_matches_hand_computed_bcd(manager):
    # (27-6)/(48-6) = 0.5 -> niveau 127.5 -> round() = 128 -> BCD "01 28"
    frame = manager.build_set_command(27)

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x14, 0x0C, 0x01, 0x28, 0xFD))


def test_set_command_at_twenty_wpm(manager):
    # (20-6)/(48-6) = 14/42 = 0.3333... -> niveau round(85.0) = 85 -> BCD "00 85"
    frame = manager.build_set_command(20)

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x14, 0x0C, 0x00, 0x85, 0xFD))


# ------------------------------------------------------------------
# Plage protocolaire 6-48 WPM (documentée, pas une politique
# applicative -- voir docstring du module)
# ------------------------------------------------------------------

@pytest.mark.parametrize("wpm", [MIN_WPM - 1, 0, -5, MAX_WPM + 1, 100])
def test_set_command_rejects_wpm_outside_documented_range(manager, wpm):
    with pytest.raises(ValueError):
        manager.build_set_command(wpm)


# ------------------------------------------------------------------
# Décodage (WPM <-> octets, dans les deux sens -- voir docstring du module)
# ------------------------------------------------------------------

def test_decode_wpm_at_minimum_level(manager):
    assert manager.decode_wpm(bytes((0x00, 0x00))) == MIN_WPM


def test_decode_wpm_at_maximum_level(manager):
    assert manager.decode_wpm(bytes((0x02, 0x55))) == MAX_WPM


def test_decode_wpm_rejects_incomplete_data(manager):
    with pytest.raises(ValueError):
        manager.decode_wpm(bytes((0x01,)))


@pytest.mark.parametrize("wpm", list(range(MIN_WPM, MAX_WPM + 1)))
def test_encode_then_decode_round_trips_within_one_wpm(manager, wpm):
    """
    Le double arrondi (WPM -> niveau -> WPM) peut ne pas retomber
    exactement sur la valeur d'origine pour chaque WPM -- la plage
    documentée [6, 48] WPM ne s'aligne pas parfaitement sur les 256
    niveaux disponibles. On vérifie donc une tolérance de ±1 WPM,
    jamais une dérive plus large.
    """

    frame = manager.build_set_command(wpm)
    data = frame[6:8]  # les 2 octets de donnée, entre la commande 14 0C et FD

    decoded = manager.decode_wpm(data)

    assert abs(decoded - wpm) <= 1
