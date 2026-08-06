"""
Tests de libraries/cat/data_mode.py.

Vérifie DataModeManager (commande CI-V 1A 06, "DATA mode") : structure
de trame pour DATA ON et DATA OFF, et le numéro de filtre distinct
selon l'état -- 0x00 pour OFF, 0x01 pour ON, valeurs confirmées par
validation matérielle réelle sur IC-7300 le 2026-08-05 (chantier
"Correction DATA Mode IC-7300" : la radio rejetait NG l'ancien 0x00
pour le cas ON, voir docstring du module), et absence de toute
commande de lecture (écriture seule, choix d'architecture documenté).
"""

import pytest

from libraries.cat.data_mode import DataModeManager


@pytest.fixture
def manager():
    return DataModeManager()


# ------------------------------------------------------------------
# Structure de trame (mêmes constantes d'adresse que ptt.py/mode.py/smeter.py)
# ------------------------------------------------------------------

def test_set_command_frame_structure_when_enabling_data_mode(manager):
    frame = manager.build_set_command(True)

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x1A, 0x06, 0x01, 0x01, 0xFD))


def test_set_command_frame_structure_when_disabling_data_mode(manager):
    frame = manager.build_set_command(False)

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x1A, 0x06, 0x00, 0x00, 0xFD))


# ------------------------------------------------------------------
# Numéro de filtre -- distinct selon l'état demandé (validation
# matérielle réelle 2026-08-05 : 0x00 rejeté par la radio pour DATA=ON)
# ------------------------------------------------------------------

def test_filter_byte_is_one_when_enabling_data_mode(manager):
    """0x01 : valeur confirmée acceptée (ACK) par l'IC-7300 réel pour DATA=ON -- 0x00 était rejeté (NG)."""

    enabled_frame = manager.build_set_command(True)

    # Avant-dernier octet de la trame (juste avant CIV_EOM) : le filtre.
    assert enabled_frame[-2] == 0x01


def test_filter_byte_is_zero_when_disabling_data_mode(manager):
    """0x00 : conforme au comportement Hamlib pour DATA=OFF, confirmé accepté (ACK) par l'IC-7300 réel."""

    disabled_frame = manager.build_set_command(False)

    assert disabled_frame[-2] == 0x00


# ------------------------------------------------------------------
# Écriture seule -- non-régression architecturale
# ------------------------------------------------------------------

def test_manager_never_exposes_a_read_command():
    """
    Non-régression architecturale : ce module doit rester écriture
    seule (voir docstring -- aucun cycle de sondage périodique ne relit
    l'état DATA dans l'architecture actuelle de cette Suite).
    """

    assert not hasattr(DataModeManager, "build_read_command")
    assert not hasattr(DataModeManager, "READ_COMMAND")
