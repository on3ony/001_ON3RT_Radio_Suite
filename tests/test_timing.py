"""
Tests de libraries/cw/timing.py.

TimingEngine n'a aucune dépendance à Qt, au matériel ni à un backend
de keying -- pur calcul, testé entièrement isolé. Les valeurs de
référence (constantes PARIS 31/19) sont vérifiées contre le vrai
MorseEncoder, jamais devinées -- voir historique de conception.
"""

import dataclasses

import pytest

from libraries.cw.morse_encoder import MorseElement, MorseElementKind, MorseEncoder
from libraries.cw.timing import TimedElement, TimingEngine

DIT = MorseElementKind.DIT
DAH = MorseElementKind.DAH
GAP_SYMBOL = MorseElementKind.GAP_SYMBOL
GAP_LETTER = MorseElementKind.GAP_LETTER
GAP_WORD = MorseElementKind.GAP_WORD


# ------------------------------------------------------------------
# Durées standard (sans Farnsworth)
# ------------------------------------------------------------------

def test_dit_duration_matches_the_paris_reference_unit():
    engine = TimingEngine(wpm=20)
    elements = [MorseElement(kind=DIT, char_index=0)]
    timed = engine.apply(elements)
    assert timed[0].duration_s == pytest.approx(1.2 / 20)


def test_dah_is_three_times_a_dit():
    engine = TimingEngine(wpm=20)
    dit = engine.apply([MorseElement(kind=DIT, char_index=0)])[0]
    dah = engine.apply([MorseElement(kind=DAH, char_index=0)])[0]
    assert dah.duration_s == pytest.approx(dit.duration_s * 3)


def test_gap_symbol_equals_a_dit_duration():
    engine = TimingEngine(wpm=20)
    dit = engine.apply([MorseElement(kind=DIT, char_index=0)])[0]
    gap = engine.apply([MorseElement(kind=GAP_SYMBOL, char_index=0)])[0]
    assert gap.duration_s == pytest.approx(dit.duration_s)


def test_gap_letter_is_three_dits_without_farnsworth():
    engine = TimingEngine(wpm=20)
    dit = engine.apply([MorseElement(kind=DIT, char_index=0)])[0]
    gap = engine.apply([MorseElement(kind=GAP_LETTER, char_index=0)])[0]
    assert gap.duration_s == pytest.approx(dit.duration_s * 3)


def test_gap_word_is_seven_dits_without_farnsworth():
    engine = TimingEngine(wpm=20)
    dit = engine.apply([MorseElement(kind=DIT, char_index=0)])[0]
    gap = engine.apply([MorseElement(kind=GAP_WORD, char_index=0)])[0]
    assert gap.duration_s == pytest.approx(dit.duration_s * 7)


# ------------------------------------------------------------------
# Référence internationale "PARIS " = 50 unités = 60/wpm secondes
# ------------------------------------------------------------------

@pytest.mark.parametrize("wpm", [5, 13, 20, 40, 60])
def test_paris_word_takes_exactly_sixty_over_wpm_seconds(wpm):
    """
    Vérifié empiriquement (voir historique) avec le vrai MorseEncoder :
    "PARIS" + l'espace de mot qui suit totalise 50 unités (31 de
    contenu + 19 d'espacement) -- la définition internationale du WPM.
    """

    encoder = MorseEncoder()
    elements = encoder.encode("PARIS PARIS")
    gap_word_index = next(i for i, e in enumerate(elements) if e.kind is GAP_WORD)
    first_word_elements = elements[: gap_word_index + 1]

    engine = TimingEngine(wpm=wpm)
    timed = engine.apply(first_word_elements)
    total_duration_s = sum(e.duration_s for e in timed)

    assert total_duration_s == pytest.approx(60.0 / wpm)


# ------------------------------------------------------------------
# Farnsworth
# ------------------------------------------------------------------

def test_farnsworth_keeps_character_speed_elements_unchanged():
    """DIT/DAH/GAP_SYMBOL restent a la vitesse "caractere" (wpm), jamais etires par Farnsworth."""

    without_farnsworth = TimingEngine(wpm=20)
    with_farnsworth = TimingEngine(wpm=20, farnsworth_wpm=5)

    for kind in (DIT, DAH, GAP_SYMBOL):
        element = [MorseElement(kind=kind, char_index=0)]
        a = without_farnsworth.apply(element)[0].duration_s
        b = with_farnsworth.apply(element)[0].duration_s
        assert a == pytest.approx(b)


def test_farnsworth_stretches_inter_character_and_word_gaps():
    engine_no_farnsworth = TimingEngine(wpm=20)
    engine_farnsworth = TimingEngine(wpm=20, farnsworth_wpm=5)

    for kind in (GAP_LETTER, GAP_WORD):
        element = [MorseElement(kind=kind, char_index=0)]
        normal_duration = engine_no_farnsworth.apply(element)[0].duration_s
        farnsworth_duration = engine_farnsworth.apply(element)[0].duration_s
        assert farnsworth_duration > normal_duration


def test_farnsworth_preserves_the_3_to_7_ratio_between_letter_and_word_gaps():
    engine = TimingEngine(wpm=20, farnsworth_wpm=5)
    gap_letter = engine.apply([MorseElement(kind=GAP_LETTER, char_index=0)])[0]
    gap_word = engine.apply([MorseElement(kind=GAP_WORD, char_index=0)])[0]
    assert gap_word.duration_s == pytest.approx(gap_letter.duration_s * 7 / 3)


def test_farnsworth_equal_to_wpm_matches_no_farnsworth_exactly():
    without_farnsworth = TimingEngine(wpm=20)
    with_equal_farnsworth = TimingEngine(wpm=20, farnsworth_wpm=20)

    elements = MorseEncoder().encode("PARIS")
    assert without_farnsworth.apply(elements) == with_equal_farnsworth.apply(elements)


def test_farnsworth_none_matches_no_farnsworth_exactly():
    without_farnsworth = TimingEngine(wpm=20)
    with_none_farnsworth = TimingEngine(wpm=20, farnsworth_wpm=None)

    elements = MorseEncoder().encode("PARIS")
    assert without_farnsworth.apply(elements) == with_none_farnsworth.apply(elements)


def test_paris_word_takes_exactly_sixty_over_farnsworth_wpm_seconds():
    """Avec Farnsworth actif, c'est la vitesse GLOBALE (farnsworth_wpm) qui doit se retrouver dans la duree totale."""

    encoder = MorseEncoder()
    elements = encoder.encode("PARIS PARIS")
    gap_word_index = next(i for i, e in enumerate(elements) if e.kind is GAP_WORD)
    first_word_elements = elements[: gap_word_index + 1]

    engine = TimingEngine(wpm=20, farnsworth_wpm=5)
    timed = engine.apply(first_word_elements)
    total_duration_s = sum(e.duration_s for e in timed)

    assert total_duration_s == pytest.approx(60.0 / 5)


# ------------------------------------------------------------------
# Validation des paramètres
# ------------------------------------------------------------------

def test_zero_wpm_raises_value_error():
    with pytest.raises(ValueError):
        TimingEngine(wpm=0)


def test_negative_wpm_raises_value_error():
    with pytest.raises(ValueError):
        TimingEngine(wpm=-5)


def test_zero_farnsworth_wpm_raises_value_error():
    with pytest.raises(ValueError):
        TimingEngine(wpm=20, farnsworth_wpm=0)


def test_negative_farnsworth_wpm_raises_value_error():
    with pytest.raises(ValueError):
        TimingEngine(wpm=20, farnsworth_wpm=-5)


def test_farnsworth_wpm_greater_than_wpm_raises_value_error():
    """Le Farnsworth ralentit un message, jamais l'inverse -- signale l'incohérence, ne la corrige jamais silencieusement."""

    with pytest.raises(ValueError):
        TimingEngine(wpm=15, farnsworth_wpm=20)


# ------------------------------------------------------------------
# Cas limites
# ------------------------------------------------------------------

def test_empty_elements_list_returns_an_empty_result():
    engine = TimingEngine(wpm=20)
    assert engine.apply([]) == []


def test_char_index_is_preserved_from_input_to_output():
    engine = TimingEngine(wpm=20)
    elements = [MorseElement(kind=DIT, char_index=42)]
    timed = engine.apply(elements)
    assert timed[0].char_index == 42


def test_apply_does_not_mutate_its_input():
    engine = TimingEngine(wpm=20)
    elements = [MorseElement(kind=DIT, char_index=0)]
    elements_copy = list(elements)
    engine.apply(elements)
    assert elements == elements_copy


# ------------------------------------------------------------------
# Immutabilite de TimedElement
# ------------------------------------------------------------------

def test_timed_element_is_immutable():
    element = TimedElement(kind=DIT, char_index=0, duration_s=0.06)
    with pytest.raises(dataclasses.FrozenInstanceError):
        element.duration_s = 1.0
