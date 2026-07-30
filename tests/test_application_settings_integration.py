"""
Tests de l'intégration de SettingsService dans core/application.py.

Construit une vraie instance d'Application, en neutralisant les seuls
effets de bord réseau/série de son constructeur (connexion DX Cluster,
démarrage des sondages météo/propagation) pour ne jamais toucher au
matériel ou au réseau pendant les tests — même principe que les
isolations déjà utilisées aux étapes précédentes (QSettings, qrz.json).

_start_radio_service() lit QSettings("ON3RT","CATServer") : isolée ici
aussi, pour ne jamais dépendre d'un port CAT réellement configuré sur
la machine qui exécute les tests (et donc ne jamais tenter une vraie
connexion série).
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
    """
    Neutralise les effets de bord réseau du constructeur d'Application
    (connexion DX Cluster, démarrage des sondages météo/propagation) :
    hors périmètre de cette étape, et ces tests ne doivent jamais
    toucher au réseau.
    """
    monkeypatch.setattr(application_module.DXClusterService, "connect", lambda self: None)
    monkeypatch.setattr(application_module.WeatherService, "start", lambda self: None)
    monkeypatch.setattr(application_module.PropagationService, "start", lambda self: None)


@pytest.fixture
def application(qapp):
    from core.application import Application
    app = Application()
    yield app
    app.close_all()


def test_application_builds_a_real_settings_service(application):
    from apps.settings.settings_service import SettingsService

    assert isinstance(application.settings_service, SettingsService)


def test_settings_service_uses_its_own_default_config_path(application):
    """
    Non-invention : Application ne passe aucun config_path personnalisé
    -> SettingsService utilise exactement le même config/settings.json
    par défaut que s'il était instancié seul.
    """
    from apps.settings.settings_service import DEFAULT_CONFIG_PATH

    assert application.settings_service._path == DEFAULT_CONFIG_PATH


def test_settings_service_has_its_expected_default_sections(application):
    assert application.settings_service.network["hamqth_username"] == ""
    assert application.settings_service.services["dxcluster_host"] == "dxfun.com"
    assert application.settings_service.services["dxcluster_port"] == 8000


def test_existing_services_are_still_constructed(application):
    """Non-régression : tous les services déjà présents avant cette étape existent toujours."""

    from apps.cat_server.radio_service import RadioService
    from apps.frequency_bank.frequency_service import FrequencyService
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


def test_module_manager_and_info_are_unaffected(application):
    """Non-régression : le reste de l'API publique d'Application est inchangé."""

    info = application.info()

    assert info["name"] == "ON3RT Radio Suite"
    assert info["version"] == "3.0.0"
    assert info["modules"] == 0
