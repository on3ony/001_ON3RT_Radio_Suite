"""
Tests de libraries/cw/morse_encoder.py.

MorseEncoder n'a aucune dépendance à un moteur de synthèse, à un
backend de keying ni à quoi que ce soit de matériel -- transformation
de texte pure, testée entièrement isolée.
"""

import dataclasses

import pytest

from libraries.cw.morse_encoder import MorseElement, MorseElementKind, MorseEncoder

DIT = MorseElementKind.DIT
DAH = MorseElementKind.DAH
GAP_SYMBOL = MorseElementKind.GAP_SYMBOL
GAP_LETTER = MorseElementKind.GAP_LETTER
GAP_WORD = MorseElementKind.GAP_WORD


@pytest.fixture
def encoder():
    return MorseEncoder()


def _kinds(elements):
    return [e.kind for e in elements]


def _indices(elements):
    return [e.char_index for e in elements]


# ------------------------------------------------------------------
# Encodage d'une seule lettre / d'un mot connu
# ------------------------------------------------------------------

def test_single_letter_a(encoder):
    elements = encoder.encode("A")
    assert _kinds(elements) == [DIT, GAP_SYMBOL, DAH]


def test_sos(encoder):
    elements = encoder.encode("SOS")
    assert _kinds(elements) == [
        DIT, GAP_SYMBOL, DIT, GAP_SYMBOL, DIT,
        GAP_LETTER,
        DAH, GAP_SYMBOL, DAH, GAP_SYMBOL, DAH,
        GAP_LETTER,
        DIT, GAP_SYMBOL, DIT, GAP_SYMBOL, DIT,
    ]


def test_two_words_use_gap_word_between_them(encoder):
    elements = encoder.encode("CQ DX")
    assert _kinds(elements) == [
        DAH, GAP_SYMBOL, DIT, GAP_SYMBOL, DAH, GAP_SYMBOL, DIT,  # C
        GAP_LETTER,
        DAH, GAP_SYMBOL, DAH, GAP_SYMBOL, DIT, GAP_SYMBOL, DAH,  # Q
        GAP_WORD,
        DAH, GAP_SYMBOL, DIT, GAP_SYMBOL, DIT,  # D
        GAP_LETTER,
        DAH, GAP_SYMBOL, DIT, GAP_SYMBOL, DIT, GAP_SYMBOL, DAH,  # X
    ]


# ------------------------------------------------------------------
# char_index -- position dans le texte SOURCE
# ------------------------------------------------------------------

def test_char_index_refers_to_the_source_text_position(encoder):
    elements = encoder.encode("CQ ON3RT")
    # "C"=0 "Q"=1 " "=2 "O"=3 "N"=4 "3"=5 "R"=6 "T"=7
    assert set(_indices(elements)) <= {0, 1, 3, 4, 5, 6, 7}
    assert 2 not in _indices(elements)  # l'espace lui-meme n'a pas d'element propre

    # Le premier element appartient toujours a "C" (index 0), le dernier a "T" (index 7)
    assert elements[0].char_index == 0
    assert elements[-1].char_index == 7


def test_gap_before_a_character_is_tagged_with_that_characters_index(encoder):
    elements = encoder.encode("AB")
    gap_elements = [e for e in elements if e.kind is GAP_LETTER]
    assert len(gap_elements) == 1
    assert gap_elements[0].char_index == 1  # index de "B", pas de "A"


# ------------------------------------------------------------------
# Normalisation des espaces
# ------------------------------------------------------------------

def test_multiple_consecutive_spaces_produce_a_single_gap_word(encoder):
    # Seul l'enchainement des TYPES doit etre identique -- les char_index
    # different legitimement puisque "A   B" et "A B" n'ont pas la meme longueur.
    assert _kinds(encoder.encode("A   B")) == _kinds(encoder.encode("A B"))


def test_leading_spaces_produce_no_orphan_gap(encoder):
    elements = encoder.encode("  A")
    assert elements[0].kind in (DIT, DAH)


def test_trailing_spaces_produce_no_orphan_gap(encoder):
    elements = encoder.encode("A  ")
    assert elements[-1].kind in (DIT, DAH)


def test_sequence_never_starts_or_ends_with_a_gap():
    encoder = MorseEncoder()
    for text in ("SOS", "CQ DX", "  CQ  ", "A", "A B C"):
        elements = encoder.encode(text)
        assert elements[0].kind in (DIT, DAH)
        assert elements[-1].kind in (DIT, DAH)


# ------------------------------------------------------------------
# Textes vides
# ------------------------------------------------------------------

def test_empty_string_returns_an_empty_sequence(encoder):
    assert encoder.encode("") == []


def test_only_spaces_returns_an_empty_sequence(encoder):
    assert encoder.encode("   ") == []


# ------------------------------------------------------------------
# Insensibilite a la casse
# ------------------------------------------------------------------

def test_lowercase_produces_the_same_result_as_uppercase(encoder):
    assert encoder.encode("cq dx") == encoder.encode("CQ DX")


def test_mixed_case_produces_the_same_result_as_uppercase(encoder):
    assert encoder.encode("CqDx") == encoder.encode("CQDX")


# ------------------------------------------------------------------
# Caracteres non supportes -- ignores silencieusement
# ------------------------------------------------------------------

def test_unsupported_character_is_silently_ignored(encoder):
    # Seul l'enchainement des TYPES doit etre identique -- les char_index
    # different legitimement puisque "Ae B" et "A B" n'ont pas la meme longueur.
    assert _kinds(encoder.encode("Aé B")) == _kinds(encoder.encode("A B"))


def test_unsupported_character_does_not_break_letter_spacing(encoder):
    """Un caractere ignore au milieu d'un mot ne doit pas empecher le GAP_LETTER normal autour de lui."""
    with_unsupported = encoder.encode("AéB")
    without_unsupported = encoder.encode("AB")
    assert _kinds(with_unsupported) == _kinds(without_unsupported)


def test_unsupported_character_alone_returns_an_empty_sequence(encoder):
    assert encoder.encode("é") == []


# ------------------------------------------------------------------
# Immutabilite de MorseElement
# ------------------------------------------------------------------

def test_morse_element_is_immutable():
    element = MorseElement(kind=MorseElementKind.DIT, char_index=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        element.char_index = 1
