"""
Non-régression : le tableau Messages doit rester lisible une fois le
vrai thème de la suite chargé (assets/themes/on3rt_dark.qss), exactement
comme launcher.py le charge au démarrage réel.

Pourquoi un fichier séparé : tous les autres tests de
apps/contest_assistant/window.py (test_contest_assistant_window.py) ne
chargent jamais ce thème. C'est précisément pour cette raison qu'ils
n'ont pas pu détecter le bug réel signalé : la géométrie calculée sans
thème semblait tout à fait correcte (viewport ≈ 214px, ~6 lignes
visibles), alors qu'une fois le vrai thème appliqué, les widgets
voisins (QGroupBox/QPushButton/QLineEdit/QComboBox) grossissent
nettement, et le tableau Messages — seul élément sans minimumHeight
propre — encaissait tout le déficit d'espace qui en résultait
(viewport ≈ 78px, ~2 lignes visibles). Voir le docstring de
apps/contest_assistant/window.py pour l'explication complète.
"""

from pathlib import Path

import pytest

from apps.contest_assistant.message_service import ContestMessageService
from apps.contest_assistant.window import ContestAssistantWindow
from libraries.station.station_service import StationService

THEME_PATH = Path(__file__).resolve().parents[1] / "assets" / "themes" / "on3rt_dark.qss"
SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "contest_assistant_seed.json"


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def themed_qapp(qapp):
    """
    Charge le vrai thème de la suite pour la durée du test, puis le
    retire explicitement : QApplication est un singleton partagé par
    toute la session de tests, un style laissé en place polluerait les
    autres fichiers de test exécutés ensuite.
    """
    assert THEME_PATH.exists(), f"thème introuvable : {THEME_PATH}"

    qapp.setStyleSheet(THEME_PATH.read_text(encoding="utf-8"))
    yield qapp
    qapp.setStyleSheet("")


@pytest.fixture
def message_service(tmp_path):
    """
    seed_path pointe vers le vrai data/contest_assistant_seed.json (les
    9 modèles réels) ; config_path reste isolé dans tmp_path, pour ne
    jamais toucher le vrai data/contest_assistant.json du dépôt.
    """
    return ContestMessageService(config_path=tmp_path / "contest_assistant.json", seed_path=SEED_PATH)


@pytest.fixture
def station_service(tmp_path):
    service = StationService(config_path=tmp_path / "station.json")
    service.callsign = "ON3RT"
    return service


def test_all_default_templates_are_visible_without_scrolling_once_the_real_theme_is_applied(
    themed_qapp, message_service, station_service
):
    window = ContestAssistantWindow(message_service=message_service, station_service=station_service)
    window.show()
    themed_qapp.processEvents()
    themed_qapp.processEvents()

    try:
        row_count = window.template_model.rowCount()
        assert row_count == len(message_service.templates) == 9

        row_height = window.template_table.verticalHeader().defaultSectionSize()
        viewport_height = window.template_table.viewport().height()
        visible_rows = viewport_height // row_height

        assert visible_rows >= row_count, (
            f"seules {visible_rows} lignes visibles sur {row_count} "
            f"(viewport={viewport_height}px, ligne={row_height}px)"
        )
    finally:
        window.close()


def test_history_table_geometry_is_unaffected_by_the_real_theme(themed_qapp, message_service, station_service):
    """
    Non-régression : Historique reste correctement dimensionné une fois
    le vrai thème appliqué. Le minimum a été volontairement réduit
    (220 -> 140) pour donner la priorité d'espace à Messages sur un
    écran réel contraint — voir le docstring de
    apps/contest_assistant/window.py.
    """

    window = ContestAssistantWindow(message_service=message_service, station_service=station_service)
    window.show()
    themed_qapp.processEvents()
    themed_qapp.processEvents()

    try:
        assert window.history_table.height() >= 140
        assert window.history_table.viewport().height() > 0
    finally:
        window.close()


def test_theme_is_reset_after_this_module_to_avoid_polluting_other_tests(qapp):
    """
    Vérifie que la fixture themed_qapp nettoie bien après elle-même
    (exécuté après les tests ci-dessus grâce à l'ordre du fichier).
    """
    assert qapp.styleSheet() == ""
