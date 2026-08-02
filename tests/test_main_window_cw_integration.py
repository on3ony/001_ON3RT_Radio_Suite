"""
Tests de l'intégration du module CW dans core/main_window.py.

Construit une vraie instance d'Application (mêmes effets de bord
réseau/série neutralisés que pour BandMap/Settings) puis une vraie
MainWindow, pour vérifier que "cw" est bien ouvrable et correctement
câblé sur application.cw_service (étape 2a), sans rien casser des
modules déjà implémentés.
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


def test_cw_is_registered_as_implemented(main_window):
    from core.main_window import _IMPLEMENTED

    assert "cw" in _IMPLEMENTED


def test_modules_tuple_lists_cw_exactly_once(main_window):
    from core.main_window import _MODULES

    keys = [key for (_icon, _title, _desc, key) in _MODULES]
    assert keys.count("cw") == 1


def test_create_module_window_returns_a_cw_window_with_injected_service(main_window, application):
    from apps.cw.window import CWWindow

    window = main_window._create_module_window("cw")

    try:
        assert isinstance(window, CWWindow)
        assert window.cw_service is application.cw_service
        assert window.settings_service is application.settings_service
    finally:
        window.close()


def test_other_implemented_modules_still_build_correctly(main_window):
    """Non-régression : les autres modules déjà implémentés s'ouvrent toujours."""

    from apps.settings.window import SettingsWindow

    window = main_window._create_module_window("settings")
    try:
        assert isinstance(window, SettingsWindow)
    finally:
        window.close()


def test_unknown_module_key_still_raises(main_window):
    """Non-régression : le comportement pour une clé inconnue est inchangé."""

    with pytest.raises(ValueError):
        main_window._create_module_window("does_not_exist")
