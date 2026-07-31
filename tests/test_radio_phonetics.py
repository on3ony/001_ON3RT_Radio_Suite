"""
Tests de libraries/voice/radio_phonetics.py.

Aucune dépendance vers pyttsx3/Piper/VoiceService ici, ni dans le
module lui-même (vérifié statiquement, pas seulement par l'absence
accidentelle dans sys.modules) : radio_phonetics.py est une
transformation de texte pure, testée entièrement isolée, comme le veut
sa conception.
"""

import ast
import inspect
import string

import libraries.voice.radio_phonetics as radio_phonetics_module
from libraries.voice.radio_phonetics import (
    _DIGITS_EN,
    _DIGITS_FR,
    _LETTERS_EN,
    _LETTERS_FR,
    _SUFFIX_WORDS_EN,
    _SUFFIX_WORDS_FR,
    to_phonetic_spelling,
)


# ------------------------------------------------------------------
# Alphabet complet A-Z
# ------------------------------------------------------------------

def test_full_alphabet_french():
    assert to_phonetic_spelling("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "FR") == (
        "Alpha Bravo Charlie Delta Echo Foxtrot Golf Hôtel India Juliette "
        "Kilo Lima Mike Novembre Oscar Papa Québec Roméo Sierra Tango "
        "Uniform Victor Whisky X-ray Yankee Zoulou"
    )


def test_full_alphabet_english():
    assert to_phonetic_spelling("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "EN") == (
        "Alpha Bravo Charlie Delta Echo Foxtrot Golf Hotel India Juliet "
        "Kilo Lima Mike November Oscar Papa Quebec Romeo Sierra Tango "
        "Uniform Victor Whiskey X-ray Yankee Zulu"
    )


def test_letter_tables_have_all_26_letters():
    assert set(_LETTERS_FR.keys()) == set(string.ascii_uppercase)
    assert set(_LETTERS_EN.keys()) == set(string.ascii_uppercase)


# ------------------------------------------------------------------
# Chiffres 0-9
# ------------------------------------------------------------------

def test_all_digits_french():
    assert to_phonetic_spelling("0123456789", "FR") == "Zéro Un Deux Trois Quatre Cinq Six Sept Huit Neuf"


def test_all_digits_english():
    assert to_phonetic_spelling("0123456789", "EN") == "Zero One Two Three Four Five Six Seven Eight Nine"


def test_digit_tables_have_all_10_digits():
    assert set(_DIGITS_FR.keys()) == set("0123456789")
    assert set(_DIGITS_EN.keys()) == set("0123456789")


# ------------------------------------------------------------------
# Casse (majuscules / minuscules)
# ------------------------------------------------------------------

def test_lowercase_input_produces_the_same_result_as_uppercase():
    assert to_phonetic_spelling("on3rt", "FR") == to_phonetic_spelling("ON3RT", "FR")


def test_mixed_case_input_produces_the_same_result_as_uppercase():
    assert to_phonetic_spelling("On3Rt", "FR") == to_phonetic_spelling("ON3RT", "FR")


def test_language_code_is_case_insensitive():
    assert to_phonetic_spelling("ON3RT", "fr") == to_phonetic_spelling("ON3RT", "FR")
    assert to_phonetic_spelling("ON3RT", "en") == to_phonetic_spelling("ON3RT", "EN")


# ------------------------------------------------------------------
# Indicatifs mixtes réels
# ------------------------------------------------------------------

def test_on3rt_french():
    assert to_phonetic_spelling("ON3RT", "FR") == "Oscar Novembre Trois Roméo Tango"


def test_letter_n_uses_novembre_in_french_to_avoid_the_et_artifact():
    """
    _LETTERS_FR["N"] = "Novembre", jamais "November" (contrairement à
    _LETTERS_EN) -- diagnostic empirique : espeak-ng, lisant "November"
    comme du français, applique la règle "finale -er se prononce /e/"
    et avale le "r" final, ce qui produit une voyelle accentuée isolée
    juste avant la pause suivante -- perçue à l'oreille comme le mot
    "et" intercalé. "Novembre" se termine par un phonème consonne (le
    "r" français), ce qui supprime l'artefact -- confirmé par écoute
    comparative réelle. Voir docstring du module.
    """
    assert _LETTERS_FR["N"] == "Novembre"
    assert _LETTERS_EN["N"] == "November"  # l'anglais n'a pas cette regle, aucun artefact constate


def test_on3rt_english():
    assert to_phonetic_spelling("ON3RT", "EN") == "Oscar November Three Romeo Tango"


def test_f4abc_french():
    assert to_phonetic_spelling("F4ABC", "FR") == "Foxtrot Quatre Alpha Bravo Charlie"


def test_dl1xyz_french():
    assert to_phonetic_spelling("DL1XYZ", "FR") == "Delta Lima Un X-ray Yankee Zoulou"


def test_dl1xyz_english():
    assert to_phonetic_spelling("DL1XYZ", "EN") == "Delta Lima One X-ray Yankee Zulu"


# ------------------------------------------------------------------
# Suffixes radio (/P, /M, /MM, /A...) -- comportement ACTUEL : épelés
# lettre par lettre, tables de suffixes volontairement vides (voir
# docstring du module) -- traitement complet reporté à une étape
# ultérieure.
# ------------------------------------------------------------------

def test_suffix_p_is_spelled_letter_by_letter_today():
    assert to_phonetic_spelling("ON3RT/P", "FR") == "Oscar Novembre Trois Roméo Tango Papa"


def test_suffix_m_is_spelled_letter_by_letter_today():
    assert to_phonetic_spelling("ON3RT/M", "EN") == "Oscar November Three Romeo Tango Mike"


def test_suffix_mm_is_spelled_letter_by_letter_today():
    assert to_phonetic_spelling("ON3RT/MM", "EN") == "Oscar November Three Romeo Tango Mike Mike"


def test_suffix_a_is_spelled_letter_by_letter_today():
    assert to_phonetic_spelling("ON3RT/A", "FR") == "Oscar Novembre Trois Roméo Tango Alpha"


def test_suffix_tables_are_empty_today_by_design():
    """
    Architecture prête (voir docstring du module) mais contenu
    volontairement vide -- traitement complet reporté. Ce test protège
    contre un remplissage accidentel non revu (l'ajout d'une entrée de
    suffixe doit rester une décision explicite, pas un effet de bord).
    """
    assert _SUFFIX_WORDS_FR == {}
    assert _SUFFIX_WORDS_EN == {}


def test_suffix_is_never_silently_dropped():
    """Le suffixe doit toujours apparaître dans le résultat, jamais disparaître avec le '/'."""
    result = to_phonetic_spelling("ON3RT/QRP", "FR")
    assert result.startswith("Oscar Novembre Trois Roméo Tango ")
    assert result != "Oscar Novembre Trois Roméo Tango"


def test_trailing_slash_with_no_suffix_does_not_crash():
    assert to_phonetic_spelling("ON3RT/", "FR") == "Oscar Novembre Trois Roméo Tango"


# ------------------------------------------------------------------
# Caractères non pris en charge
# ------------------------------------------------------------------

def test_spaces_are_ignored():
    assert to_phonetic_spelling("ON 3RT", "FR") == to_phonetic_spelling("ON3RT", "FR")


def test_hyphen_is_ignored():
    assert to_phonetic_spelling("ON-3RT", "FR") == to_phonetic_spelling("ON3RT", "FR")


def test_punctuation_is_ignored():
    assert to_phonetic_spelling("ON3RT!", "FR") == to_phonetic_spelling("ON3RT", "FR")


def test_unicode_symbol_is_ignored():
    assert to_phonetic_spelling("ON3RT€", "FR") == to_phonetic_spelling("ON3RT", "FR")


def test_string_with_only_unsupported_characters_returns_empty_string():
    assert to_phonetic_spelling("   ---!!!", "FR") == ""


# ------------------------------------------------------------------
# Langue inconnue -> repli anglais
# ------------------------------------------------------------------

def test_unknown_language_falls_back_to_english():
    assert to_phonetic_spelling("ON3RT", "DE") == to_phonetic_spelling("ON3RT", "EN")


def test_none_language_falls_back_to_english():
    assert to_phonetic_spelling("ON3RT", None) == to_phonetic_spelling("ON3RT", "EN")


def test_empty_language_string_falls_back_to_english():
    assert to_phonetic_spelling("ON3RT", "") == to_phonetic_spelling("ON3RT", "EN")


def test_default_language_is_french():
    assert to_phonetic_spelling("ON3RT") == to_phonetic_spelling("ON3RT", "FR")


# ------------------------------------------------------------------
# Chaîne vide
# ------------------------------------------------------------------

def test_empty_string_returns_empty_string():
    assert to_phonetic_spelling("", "FR") == ""
    assert to_phonetic_spelling("", "EN") == ""


# ------------------------------------------------------------------
# Indépendance totale vis-à-vis des moteurs de synthèse
# ------------------------------------------------------------------

def _imported_module_names(module) -> list[str]:
    """Noms des MODULES importés (jamais les symboles importés depuis eux) -- 'from __future__ import annotations' ne compte que '__future__'."""

    source = inspect.getsource(module)
    tree = ast.parse(source)

    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)

    return names


def test_module_has_no_import_of_pyttsx3_piper_or_voice_service():
    """
    Vérification statique (analyse du code source), pas seulement
    l'absence de ces paquets dans sys.modules au moment du test --
    radio_phonetics.py ne doit jamais dépendre d'un moteur de synthèse
    ni de VoiceService, quel que soit ce qui a été importé ailleurs
    dans la suite de tests avant ce fichier.
    """

    forbidden_substrings = ("pyttsx3", "piper", "voice_service", "engines")
    imported_names = _imported_module_names(radio_phonetics_module)

    for name in imported_names:
        lowered = name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lowered, f"import interdit trouvé dans radio_phonetics.py : {name}"


def test_module_has_no_dependency_at_all_beyond_the_standard_library_future_import():
    """Module de texte pur : aucune dépendance externe, pas même indirecte."""
    assert _imported_module_names(radio_phonetics_module) == ["__future__"]
