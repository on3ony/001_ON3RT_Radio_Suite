"""
Tests de l'intégration de CatSharingService/RigctldAdapter dans
core/application.py (chantier CAT Sharing / rigctld -- intégration).

Construit une vraie instance d'Application pour vérifier que
RigctldAdapter est construit, enregistré via CatSharingService.
add_adapter() et démarré seulement si
SettingsService.cat_sharing["enabled"] est vrai, avec le port
configuré -- jamais sans ce consentement explicite. Vérifie aussi que
CatSharingService reste le seul détenteur de la liste des adaptateurs
(aucune référence nommée type application.rigctld_adapter), et
qu'arrêter proprement une Application libère réellement le port pour
une instance suivante.

Mêmes effets de bord réseau/série neutralisés que pour les étapes
précédentes (connexion DX Cluster, sondages météo/propagation, port
CAT réel) : ces tests ne doivent jamais toucher au réseau ni au
matériel, à l'exception du port TCP éphémère (127.0.0.1, port=0)
ouvert par RigctldAdapter lui-même quand le partage CAT est
explicitement activé dans les réglages isolés du test.
"""

import json
import socket

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtNetwork import QHostAddress, QTcpServer

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
    from apps.contest_assistant.message_service import ContestMessageService

    config_path = tmp_path / "contest_assistant.json"
    seed_path = tmp_path / "contest_assistant_seed.json"

    monkeypatch.setattr(
        application_module,
        "ContestMessageService",
        lambda: ContestMessageService(config_path=config_path, seed_path=seed_path),
    )


def _isolate_settings_service(monkeypatch, tmp_path, cat_sharing_overrides):
    """
    Injecte une SettingsService isolée (fichier temporaire) avec la
    section "cat_sharing" pré-remplie -- jamais le vrai
    config/settings.json du dépôt, pour des tests déterministes
    indépendants de l'état réel de la station.
    """
    from apps.settings.settings_service import SettingsService

    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"cat_sharing": cat_sharing_overrides}), encoding="utf-8")

    monkeypatch.setattr(
        application_module,
        "SettingsService",
        lambda: SettingsService(config_path=path),
    )


@pytest.fixture
def application_with_cat_sharing_disabled(qapp, tmp_path, monkeypatch):
    _isolate_settings_service(monkeypatch, tmp_path, {"enabled": False})

    from core.application import Application
    app = Application()
    yield app
    app.close_all()


@pytest.fixture
def application_with_cat_sharing_enabled(qapp, tmp_path, monkeypatch):
    _isolate_settings_service(monkeypatch, tmp_path, {"enabled": True, "port": 0})

    from core.application import Application
    app = Application()
    yield app

    app.cat_sharing_service.stop_all()
    app.close_all()


def _free_tcp_port() -> int:
    """Obtient un port TCP libre attribué par l'OS (même mécanisme que RigctldAdapter avec port=0), pour le réutiliser volontairement de façon déterministe."""

    probe = QTcpServer()
    probe.listen(QHostAddress("127.0.0.1"), 0)
    port = probe.serverPort()
    probe.close()
    return port


# ------------------------------------------------------------------
# Cas 1 -- cat_sharing.enabled == False
# ------------------------------------------------------------------

def test_no_adapter_is_registered_when_the_setting_is_disabled(application_with_cat_sharing_disabled):
    app = application_with_cat_sharing_disabled

    assert app.cat_sharing_service._adapters == []


def test_default_rigctld_port_stays_free_when_the_setting_is_disabled(application_with_cat_sharing_disabled):
    """
    Aucun port réseau n'est ouvert quand le partage CAT est désactivé :
    le port rigctld par défaut (4532) reste effectivement disponible --
    vérifié en le liant réellement, pas en supposant.
    """

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", 4532))
    finally:
        probe.close()


# ------------------------------------------------------------------
# Cas 2 -- cat_sharing.enabled == True, port=0
# ------------------------------------------------------------------

def test_exactly_one_rigctld_adapter_is_registered_and_started_when_the_setting_is_enabled(
    application_with_cat_sharing_enabled,
):
    from libraries.cat.cat_adapters.rigctld_adapter import RigctldAdapter

    app = application_with_cat_sharing_enabled

    assert len(app.cat_sharing_service._adapters) == 1

    adapter = app.cat_sharing_service._adapters[0]
    assert isinstance(adapter, RigctldAdapter)
    assert adapter.actual_port != 0  # le serveur écoute réellement, port attribué par l'OS


def test_cat_sharing_service_only_receives_the_shared_radio_service(application_with_cat_sharing_enabled):
    """
    Non-régression architecturale : CatSharingService doit être
    construit avec exactement application.radio_service -- jamais un
    autre service, jamais une seconde instance de RadioService.
    """
    app = application_with_cat_sharing_enabled

    assert app.cat_sharing_service._radio_service is app.radio_service


# ------------------------------------------------------------------
# Non-régression du reste d'Application
# ------------------------------------------------------------------

def test_existing_services_are_still_constructed_when_cat_sharing_is_enabled(application_with_cat_sharing_enabled):
    """Non-régression : activer le partage CAT ne casse rien d'existant."""

    from apps.cat_server.radio_service import RadioService
    from apps.cat_server.ptt_guard import PTTGuard
    from libraries.dxcluster.dxcluster_service import DXClusterService
    from libraries.propagation.propagation_service import PropagationService
    from libraries.station.station_service import StationService
    from libraries.weather.weather_service import WeatherService

    app = application_with_cat_sharing_enabled

    assert isinstance(app.radio_service, RadioService)
    assert isinstance(app.ptt_guard, PTTGuard)
    assert isinstance(app.station_service, StationService)
    assert isinstance(app.dxcluster_service, DXClusterService)
    assert isinstance(app.weather_service, WeatherService)
    assert isinstance(app.propagation_service, PropagationService)


def test_module_manager_and_info_are_unaffected_when_cat_sharing_is_enabled(application_with_cat_sharing_enabled):
    """Non-régression : le reste de l'API publique d'Application est inchangé."""

    info = application_with_cat_sharing_enabled.info()

    assert info["name"] == "ON3RT Radio Suite"
    assert info["version"] == "3.0.0"
    assert info["modules"] == 0


# ------------------------------------------------------------------
# Réutilisation du port après arrêt propre
# ------------------------------------------------------------------

def test_stopping_the_application_releases_the_port_for_a_second_application_instance(
    qapp, tmp_path, monkeypatch
):
    """
    Une seconde construction d'Application, avec le même port fixe
    configuré, après arrêt complet de la première, ne doit jamais
    échouer par réutilisation de port -- démontre que
    cat_sharing_service.stop_all() libère réellement le port
    (contrairement à un simple abandon de référence Python).
    """

    fixed_port = _free_tcp_port()

    _isolate_settings_service(monkeypatch, tmp_path, {"enabled": True, "port": fixed_port})

    from core.application import Application

    first = Application()
    first_adapter = first.cat_sharing_service._adapters[0]
    assert first_adapter.actual_port == fixed_port

    first.cat_sharing_service.stop_all()
    first.close_all()

    second = Application()
    try:
        second_adapter = second.cat_sharing_service._adapters[0]
        assert second_adapter.actual_port == fixed_port  # même port, aucune erreur de réutilisation
    finally:
        second.cat_sharing_service.stop_all()
        second.close_all()
