"""
Tests de l'intégration de LiveService dans core/application.py.

Construit une vraie instance d'Application (mêmes effets de bord
réseau/série neutralisés que pour Settings/BandMap) pour vérifier que
LiveService est désormais construit une seule fois par Application, à
partir des mêmes instances déjà partagées de dxcluster_service/
weather_service/propagation_service — jamais dupliquées, ce qui
sonderait le réseau en double — et que son état initial respecte le
contrat de chaque fournisseur.
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


def test_application_builds_a_real_live_service(application):
    from apps.dashboard.live_service import LiveService

    assert isinstance(application.live_service, LiveService)


def test_live_service_initial_state_covers_every_source_contract(application):
    state = application.live_service.state()

    # CAT (base.py DEFAULT_STATE) + Logbook.
    for key in ("connected", "frequency", "mode", "band", "ptt", "vfo", "logbook"):
        assert key in state

    # DX Cluster / météo / propagation : jamais connectés dans ce test
    # (effets réseau neutralisés) -> état honnêtement "déconnecté".
    assert state["dxcluster_connected"] is False
    assert state["dxcluster_spots"] == []
    assert state["weather_connected"] is False
    assert state["weather_data"] is None
    assert state["propagation_connected"] is False
    assert state["propagation_data"] is None

    # Activité par bande (chantier dédié, 2026-08-05) : recalculée dès
    # la construction à partir de recent_spots() (vide ici, DX Cluster
    # jamais connecté) -> toutes les bandes présentes à 0 spot.
    assert "bands" in state
    assert state["bands"]["20m"]["count"] == 0


def test_live_service_reuses_the_same_shared_service_instances(application):
    """
    Non-duplication : chaque fournisseur réseau du LiveService de
    l'Application doit s'appuyer sur exactement l'instance de service
    déjà partagée (dxcluster_service/weather_service/
    propagation_service), jamais une seconde instance qui sonderait le
    réseau en double.
    """
    from apps.dashboard.data_sources.band_activity_source import BandActivityLiveDataSource
    from apps.dashboard.data_sources.dxcluster_source import DXClusterLiveDataSource
    from apps.dashboard.data_sources.propagation_source import PropagationLiveDataSource
    from apps.dashboard.data_sources.weather_source import WeatherLiveDataSource

    sources_by_type = {type(source): source for source in application.live_service._sources}

    assert sources_by_type[DXClusterLiveDataSource]._service is application.dxcluster_service
    assert sources_by_type[WeatherLiveDataSource]._service is application.weather_service
    assert sources_by_type[PropagationLiveDataSource]._service is application.propagation_service

    # BandActivityLiveDataSource doit réutiliser cette MÊME instance de
    # dxcluster_service, jamais une seconde connexion DX Cluster.
    assert sources_by_type[BandActivityLiveDataSource]._service is application.dxcluster_service


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
