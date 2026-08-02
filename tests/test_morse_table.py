"""
Tests de libraries/cw/morse_table.py.

MORSE_TABLE est une donnée pure : les tests comparent contre une
référence écrite indépendamment (pas dérivée de la table elle-même),
pour se protéger contre une modification accidentelle et silencieuse
d'une entrée -- même principe que test_radio_phonetics.py pour
l'alphabet radio international.
"""

from libraries.cw.morse_table import MORSE_TABLE

_EXPECTED_LETTERS = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..",
}

_EXPECTED_DIGITS = {
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
}

_EXPECTED_PUNCTUATION = {
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.",
    "!": "-.-.--", "/": "-..-.", "(": "-.--.", ")": "-.--.-",
    "&": ".-...", ":": "---...", ";": "-.-.-.", "=": "-...-",
    "+": ".-.-.", "-": "-....-", "_": "..--.-", '"': ".-..-.",
    "$": "...-..-", "@": ".--.-.",
}


def test_all_letters_match_the_expected_reference():
    for letter, code in _EXPECTED_LETTERS.items():
        assert MORSE_TABLE[letter] == code


def test_all_digits_match_the_expected_reference():
    for digit, code in _EXPECTED_DIGITS.items():
        assert MORSE_TABLE[digit] == code


def test_all_punctuation_matches_the_expected_reference():
    for char, code in _EXPECTED_PUNCTUATION.items():
        assert MORSE_TABLE[char] == code


def test_table_contains_exactly_the_expected_entries_no_more_no_less():
    expected_keys = set(_EXPECTED_LETTERS) | set(_EXPECTED_DIGITS) | set(_EXPECTED_PUNCTUATION)
    assert set(MORSE_TABLE.keys()) == expected_keys


def test_table_has_26_letters_10_digits_and_18_punctuation_entries():
    assert len(_EXPECTED_LETTERS) == 26
    assert len(_EXPECTED_DIGITS) == 10
    assert len(_EXPECTED_PUNCTUATION) == 18
    assert len(MORSE_TABLE) == 54


def test_all_values_contain_only_dots_and_dashes():
    for code in MORSE_TABLE.values():
        assert set(code) <= {".", "-"}
        assert len(code) > 0


def test_all_letter_and_digit_keys_are_single_uppercase_characters():
    for key in list(_EXPECTED_LETTERS) + list(_EXPECTED_DIGITS):
        assert len(key) == 1
        assert key == key.upper()


def test_no_prosigns_are_included_yet():
    """Extension future documentée dans la docstring du module -- pas encore implémentée."""
    prosign_like_keys = {"BT", "AR", "SK", "KN", "AS"}
    assert not (prosign_like_keys & set(MORSE_TABLE.keys()))
