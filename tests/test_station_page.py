"""
Tests de core/station_page.py.

Vérifie le câblage de la carte "Paramètres" vers le module Settings et
la construction de SECTION_TITLES (dérivée de _SECTIONS, jamais un
second libellé codé en dur).
"""

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from core.station_page import _SECTIONS, SECTION_TITLES, StationPage


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_parametres_section_now_points_to_the_settings_module():
    matching = [s for s in _SECTIONS if s[1] == "Paramètres"]
    assert len(matching) == 1
    assert matching[0][3] == "settings"


def test_other_sections_are_unchanged():
    """Non-régression : les 4 autres sections restent des espaces réservés (module_key=None)."""

    still_reserved = {"Radio", "Ports COM", "Informations système", "Diagnostics"}
    for _icon, title, _desc, module_key in _SECTIONS:
        if title in still_reserved:
            assert module_key is None


def test_section_titles_maps_only_sections_with_a_real_module_key():
    assert SECTION_TITLES == {
        "cat_server": "CAT",
        "settings": "Paramètres",
    }


def test_parametres_card_is_now_clickable_and_emits_settings(qapp):
    page = StationPage()

    received = []
    page.opened.connect(received.append)

    # Recherche de la carte "Paramètres" par son titre affiché.
    from core.station_page import _SectionCard

    cards = page.findChildren(_SectionCard)
    parametres_card = next(c for c in cards if "Paramètres" in _titles(c))

    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    parametres_card.mousePressEvent(event)

    assert received == ["settings"]


def _titles(card):
    """Concatène le texte de tous les QLabel d'une carte, pour l'identifier par son titre affiché."""
    from PySide6.QtWidgets import QLabel
    return " ".join(lbl.text() for lbl in card.findChildren(QLabel))
