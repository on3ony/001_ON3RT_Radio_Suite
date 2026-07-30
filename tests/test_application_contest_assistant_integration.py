"""
Tests de l'intégration de ContestMessageService dans core/application.py.

Construit une vraie instance d'Application (mêmes effets de bord
réseau/série neutralisés que pour Settings/BandMap). ContestMessageService
écrit data/contest_assistant.json dès sa construction si le fichier
n'existe pas encore (chargement du seed) : ses chemins sont donc
systématiquement isolés vers un dossier temporaire, pour ne jamais
créer ou modifier le vrai fichier du dépôt pendant les tests.
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


def test_application_builds_a_real_contest_message_service(application):
    assert isinstance(application.contest_message_service, ContestMessageService)


def test_contest_message_service_has_its_expected_default_state(application):
    service = application.contest_message_service

    assert service.contest_name == ""
    assert service.language == "FR"
    assert service.serial == 0
    assert service.history == []
    assert service.templates == []  # aucun fichier seed dans le dossier isolé de ce test


def test_existing_services_are_still_constructed(application):
    """Non-régression : tous les services déjà présents avant cette étape existent toujours."""

    from apps.cat_server.radio_service import RadioService
    from apps.frequency_bank.frequency_service import FrequencyService
    from apps.settings.settings_service import SettingsService
    from libraries.dxcluster.dxcluster_service import DXClusterService
    from libraries.propagation.propagation_service import PropagationService
    from libraries.station.station_service import StationService
    from libraries.weather.weather_service import WeatherService

    assert isinstance(application.radio_service, RadioService)
    assert isinstance(application.station_service, StationService)
    assert isinstance(application.dxcluster_service, DXClusterService)
    assert isinstance(application.weather_service, WeatherService)
    assert isinstance(application.propagation_service, PropagationService)
    assert isinstance(application.frequency_service, FrequencyService)
    assert isinstance(application.settings_service, SettingsService)


def test_module_manager_and_info_are_unaffected(application):
    """Non-régression : le reste de l'API publique d'Application est inchangé."""

    info = application.info()

    assert info["name"] == "ON3RT Radio Suite"
    assert info["version"] == "3.0.0"
    assert info["modules"] == 0
