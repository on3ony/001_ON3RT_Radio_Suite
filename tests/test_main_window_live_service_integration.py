"""
Tests de l'intégration de LiveService (Application -> DashboardPage)
dans core/main_window.py.

Construit une vraie instance d'Application puis une vraie MainWindow
(mêmes effets de bord réseau/série neutralisés que pour les étapes
précédentes) pour vérifier que DashboardPage utilise désormais
exactement l'instance de LiveService construite par Application,
au lieu d'en construire une elle-même.
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


def test_dashboard_page_uses_the_application_live_service_instance(main_window, application):
    """
    Non-duplication : DashboardPage ne doit plus construire son propre
    LiveService (comportement d'avant cette étape) mais recevoir
    exactement celui d'Application, pour qu'un futur LiveServer puisse
    s'abonner au même état sans sondages dupliqués.
    """

    assert main_window.dashboard_page.live_service is application.live_service


def test_header_still_reflects_the_shared_live_service_state(main_window, application):
    """
    Non-régression : le bandeau s'abonne toujours à l'état CAT réel
    (voir core/main_window.py::_on_live_state) même après le passage à
    un LiveService partagé au niveau Application — la pastille "cat"
    passe au vert lorsque state_changed signale une connexion.
    """
    from libraries.ui import colors

    application.live_service._handle_source_update(
        {"connected": True, "model": "IC-7300"}
    )

    cat_dot_style = main_window.header._pills["cat"]._dot.styleSheet()
    assert colors.STATE_GREEN in cat_dot_style


def test_other_implemented_modules_still_build_correctly(main_window):
    """Non-régression : les autres modules déjà implémentés s'ouvrent toujours."""

    from apps.settings.window import SettingsWindow

    window = main_window._create_module_window("settings")
    try:
        assert isinstance(window, SettingsWindow)
    finally:
        window.close()
