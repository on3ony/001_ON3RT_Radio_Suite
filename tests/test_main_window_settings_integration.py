"""
Tests de l'intégration du module Settings dans core/main_window.py.

Construit une vraie instance d'Application (mêmes effets de bord
réseau/série neutralisés qu'à l'étape 11) puis une vraie MainWindow,
pour vérifier que "settings" est bien ouvrable et correctement câblé,
sans rien casser des modules déjà implémentés.
"""

import pytest
from PySide6.QtCore import QSettings

import core.application as application_module


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_cat_settings(tmp_path, monkeypatch):
    ini_path = tmp_path / "catserver_test.ini"

    def fake_qsettings(*args, **kwargs):
        return QSettings(str(ini_path), QSettings.Format.IniFormat)

    monkeypatch.setattr(application_module, "QSettings", fake_qsettings)


@pytest.fixture(autouse=True)
def no_network_side_effects(monkeypatch):
    monkeypatch.setattr(application_module.DXClusterService, "connect", lambda self: None)
    monkeypatch.setattr(application_module.WeatherService, "start", lambda self: None)
    monkeypatch.setattr(application_module.PropagationService, "start", lambda self: None)


@pytest.fixture(autouse=True)
def isolated_contest_assistant_paths(tmp_path, monkeypatch):
    """
    ContestMessageService.__init__() sauvegarde immédiatement si son
    fichier de configuration n'existe pas encore (chargement du seed) :
    jamais le vrai data/contest_assistant.json du dépôt pendant les tests.
    """
    from apps.contest_assistant.message_service import ContestMessageService

    config_path = tmp_path / "contest_assistant.json"
    seed_path = tmp_path / "contest_assistant_seed.json"

    monkeypatch.setattr(
        application_module,
        "ContestMessageService",
        lambda: ContestMessageService(config_path=config_path, seed_path=seed_path),
    )


@pytest.fixture
def application(qapp):
    from core.application import Application
    app = Application()
    yield app
    app.close_all()


@pytest.fixture
def main_window(qapp, application):
    from core.main_window import MainWindow
    window = MainWindow(application)
    yield window
    window.close()


def test_settings_is_registered_as_implemented(main_window):
    from core.main_window import _IMPLEMENTED

    assert "settings" in _IMPLEMENTED


def test_create_module_window_returns_a_settings_window_with_injected_services(main_window, application):
    from apps.settings.window import SettingsWindow

    window = main_window._create_module_window("settings")

    try:
        assert isinstance(window, SettingsWindow)
        assert window.station_service is application.station_service
        assert window.settings_service is application.settings_service
        assert window.radio_service is application.radio_service
    finally:
        window.close()


def test_modules_tuple_still_lists_settings_as_before(main_window):
    """
    Non-régression : _MODULES (la grille Applications) n'a pas été
    modifiée par cette étape — l'entrée "settings" y figurait déjà.
    """
    from core.main_window import _MODULES

    keys = [key for (_icon, _title, _desc, key) in _MODULES]
    assert keys.count("settings") == 1


def test_other_implemented_modules_still_build_correctly(main_window):
    """Non-régression : les autres modules déjà implémentés s'ouvrent toujours."""

    from apps.dxcluster.window import DXClusterWindow

    window = main_window._create_module_window("dxcluster")
    try:
        assert isinstance(window, DXClusterWindow)
    finally:
        window.close()


def test_unknown_module_key_still_raises(main_window):
    """Non-régression : le comportement pour une clé inconnue est inchangé."""

    with pytest.raises(ValueError):
        main_window._create_module_window("does_not_exist")


# ----------------------------------------------------------------------
# Étape 13 : câblage de la carte "Paramètres" de la page Station
# ----------------------------------------------------------------------

def test_station_page_settings_card_opens_a_real_settings_window(main_window, application):
    """
    Bout en bout : émettre "settings" depuis station_page.opened (ce
    que fait la carte "Paramètres" une fois cliquée) doit ouvrir une
    vraie SettingsWindow, exactement comme depuis la grille
    Applications.
    """
    from apps.settings.window import SettingsWindow

    main_window.station_page.opened.emit("settings")

    window = application.module_manager.get("settings")
    try:
        assert isinstance(window, SettingsWindow)
        assert window.windowTitle() == "ON3RT Radio Suite - Settings"
    finally:
        application.close_module("settings")


def test_station_page_opened_uses_section_titles_not_a_hardcoded_string(main_window, monkeypatch):
    """
    Corrige le titre codé en dur ("CAT Server" pour toute carte
    Station, quelle qu'elle soit) : le message affiché pour un module
    non implémenté doit utiliser le titre réel de la carte cliquée
    (SECTION_TITLES), pas une chaîne fixe. Vérifié en désimplémentant
    temporairement "cat_server" pour forcer la branche "bientôt
    disponible" et lire le message affiché.
    """
    import core.main_window as main_window_module

    monkeypatch.setattr(main_window_module, "_IMPLEMENTED", frozenset())

    main_window.station_page.opened.emit("cat_server")

    assert main_window.statusBar().currentMessage() == "CAT — module bientôt disponible"


def test_other_station_page_cards_still_have_no_module_key(main_window):
    """Non-régression : les 4 autres cartes de la page Station restent des espaces réservés."""

    from core.station_page import _SECTIONS

    still_reserved = {"Radio", "Ports COM", "Informations système", "Diagnostics"}
    for _icon, title, _desc, module_key in _SECTIONS:
        if title in still_reserved:
            assert module_key is None
