"""
Tests de CIVProtocol.is_ack()/is_ng() (libraries/cat/civ_protocol.py).

Ajoutés pour le chantier "Correction DATA Mode IC-7300" (2026-08-05) :
avant ce chantier, aucune commande d'écriture de la Suite n'inspectait
la réponse CI-V de la radio (ACK/NG), ce qui laissait un rejet (NG)
silencieusement remonter comme un succès jusqu'à WSJT-X. Ces deux
méthodes sont le point unique de classification, réutilisé par
CATEngine.set_data_mode().
"""

from libraries.cat.civ_protocol import CIVProtocol

_ACK_FRAME = bytes((0xFE, 0xFE, 0xE0, 0x94, 0xFB, 0xFD))
_NG_FRAME = bytes((0xFE, 0xFE, 0xE0, 0x94, 0xFA, 0xFD))


def test_is_ack_true_for_a_real_ack_frame():
    assert CIVProtocol.is_ack(_ACK_FRAME) is True


def test_is_ack_false_for_a_ng_frame():
    assert CIVProtocol.is_ack(_NG_FRAME) is False


def test_is_ng_true_for_a_real_ng_frame():
    assert CIVProtocol.is_ng(_NG_FRAME) is True


def test_is_ng_false_for_an_ack_frame():
    assert CIVProtocol.is_ng(_ACK_FRAME) is False


def test_is_ack_false_for_empty_response():
    """Timeout (aucune réponse) : jamais interprété comme un ACK."""

    assert CIVProtocol.is_ack(b"") is False


def test_is_ack_false_for_too_short_response():
    assert CIVProtocol.is_ack(bytes((0xFE, 0xFE))) is False


def test_is_ack_false_for_an_unrelated_frame_like_a_frequency_reply():
    """Une trame de donnée normale (pas ACK/NG) ne doit jamais être classée ACK par accident."""

    frequency_reply = bytes((0xFE, 0xFE, 0xE0, 0x94, 0x03, 0x00, 0x74, 0x40, 0x01, 0x00, 0xFD))

    assert CIVProtocol.is_ack(frequency_reply) is False
    assert CIVProtocol.is_ng(frequency_reply) is False
