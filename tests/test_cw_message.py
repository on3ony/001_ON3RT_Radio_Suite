"""
Tests de libraries/cat/cw_message.py.

Vérifie CWMessageManager (commande CI-V 0x17, "Send CW message") contre
les valeurs exactes du guide de référence CI-V officiel Icom
(IC-7300MK2), sans aucun matériel réel : structure de trame, limite de
30 caractères, encodage ASCII direct, octet d'arrêt 0xFF (pas la
chaîne "FF").
"""

import pytest

from libraries.cat.cw_message import MAX_MESSAGE_CHARS, CWMessageManager


@pytest.fixture
def manager():
    return CWMessageManager()


# ------------------------------------------------------------------
# Structure de trame (préambule FE FE, adresses IC-7300/contrôleur,
# commande 0x17, fin de trame FD -- mêmes constantes que ptt.py/mode.py)
# ------------------------------------------------------------------

def test_send_command_frame_structure(manager):
    frame = manager.build_send_command("E")

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x17, ord("E"), 0xFD))


def test_send_command_encodes_text_as_plain_ascii(manager):
    frame = manager.build_send_command("CQ ON3RT")

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x17)) + b"CQ ON3RT" + bytes((0xFD,))


def test_send_command_accepts_lowercase_and_documented_punctuation(manager):
    # Table officielle : a~z (61~7A) et une ponctuation précise sont valides,
    # au même titre que les majuscules -- aucune transformation de casse ici.
    frame = manager.build_send_command("cq/de?")

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x17)) + b"cq/de?" + bytes((0xFD,))


def test_send_command_with_empty_text_still_builds_a_valid_frame(manager):
    frame = manager.build_send_command("")

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x17, 0xFD))


# ------------------------------------------------------------------
# Limite protocolaire de 30 caractères (documentée, pas une politique
# applicative -- voir docstring du module)
# ------------------------------------------------------------------

def test_send_command_accepts_exactly_thirty_characters(manager):
    text = "A" * MAX_MESSAGE_CHARS

    frame = manager.build_send_command(text)

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x17)) + text.encode("ascii") + bytes((0xFD,))


def test_send_command_rejects_thirty_one_characters(manager):
    with pytest.raises(ValueError):
        manager.build_send_command("A" * (MAX_MESSAGE_CHARS + 1))


# ------------------------------------------------------------------
# Texte non-ASCII : échec honnête, jamais un encodage inventé
# ------------------------------------------------------------------

def test_send_command_rejects_non_ascii_text(manager):
    with pytest.raises(UnicodeEncodeError):
        manager.build_send_command("Ééàç")


# ------------------------------------------------------------------
# Arrêt : un octet 0xFF, jamais la chaîne ASCII "FF" (0x46 0x46)
# ------------------------------------------------------------------

def test_stop_command_sends_a_single_0xff_byte(manager):
    frame = manager.build_stop_command()

    assert frame == bytes((0xFE, 0xFE, 0x94, 0xE0, 0x17, 0xFF, 0xFD))
    assert frame != bytes((0xFE, 0xFE, 0x94, 0xE0, 0x17, 0x46, 0x46, 0xFD))  # pas la chaîne "FF"


# ------------------------------------------------------------------
# Pas de commande de lecture pour 0x17 (asymétrie documentée -- voir
# docstring du module : la doc officielle ne décrit qu'un envoi)
# ------------------------------------------------------------------

def test_manager_exposes_no_read_command():
    assert not hasattr(CWMessageManager, "build_read_command")
    assert not hasattr(CWMessageManager, "READ_COMMAND")
