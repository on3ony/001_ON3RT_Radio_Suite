"""
Tests de libraries/text/variable_resolver.py.

Déplacés depuis tests/test_contest_assistant_message_service.py lors
de l'extraction de resolve_variables() vers un utilitaire partagé
(étape 4a de l'architecture Voix) — comportement inchangé, mêmes cas.
"""

from libraries.text.variable_resolver import resolve_variables


def test_resolve_variables_substitutes_known_markers():
    result = resolve_variables(
        "%RST% %SERIAL% de %MYCALL% pour %CALL%",
        {"RST": "599", "SERIAL": "001", "MYCALL": "ON3RT", "CALL": "F4XYZ"},
    )
    assert result == "599 001 de ON3RT pour F4XYZ"


def test_resolve_variables_leaves_unknown_markers_untouched():
    result = resolve_variables("%RST% %UNKNOWN%", {"RST": "599"})
    assert result == "599 %UNKNOWN%"


def test_resolve_variables_handles_repeated_markers():
    result = resolve_variables("%SERIAL%-%SERIAL%", {"SERIAL": "007"})
    assert result == "007-007"


def test_resolve_variables_with_no_markers_returns_text_unchanged():
    assert resolve_variables("Merci, bonne continuation", {}) == "Merci, bonne continuation"
