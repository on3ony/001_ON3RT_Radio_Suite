"""
Tests de l'intégration du module Contest Assistant dans core/main_window.py.

Construit une vraie instance d'Application (mêmes effets de bord
réseau/série neutralisés que pour Settings/BandMap, y compris
l'isolation de ContestMessageService) puis une vraie MainWindow, pour
vérifier que "contest_assistant" est bien ouvrable et correctement
câblé, sans rien casser des modules déjà implémentés.
"""

import pytest
from PySide6.QtCore import QSettings

import core.application as application_module
from apps.contest_assistant.message_service import ContestMessageService


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


def test_contest_assistant_is_registered_as_implemented(main_window):
    from core.main_window import _IMPLEMENTED

    assert "contest_assistant" in _IMPLEMENTED


def test_modules_tuple_lists_contest_assistant_exactly_once(main_window):
    from core.main_window import _MODULES

    keys = [key for (_icon, _title, _desc, key) in _MODULES]
    assert keys.count("contest_assistant") == 1


def test_create_module_window_returns_a_contest_assistant_window_with_injected_services(main_window, application):
    from apps.contest_assistant.window import ContestAssistantWindow

    window = main_window._create_module_window("contest_assistant")

    try:
        assert isinstance(window, ContestAssistantWindow)
        assert window.message_service is application.contest_message_service
        assert window.station_service is application.station_service
    finally:
        window.close()


def test_other_implemented_modules_still_build_correctly(main_window):
    """Non-régression : les autres modules déjà implémentés s'ouvrent toujours."""

    from apps.bandmap.window import BandMapWindow
    from apps.settings.window import SettingsWindow

    bandmap_window = main_window._create_module_window("bandmap")
    settings_window = main_window._create_module_window("settings")
    try:
        assert isinstance(bandmap_window, BandMapWindow)
        assert isinstance(settings_window, SettingsWindow)
    finally:
        bandmap_window.close()
        settings_window.close()


def test_unknown_module_key_still_raises(main_window):
    """Non-régression : le comportement pour une clé inconnue est inchangé."""

    with pytest.raises(ValueError):
        main_window._create_module_window("does_not_exist")
