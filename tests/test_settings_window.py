"""
Tests de apps/settings/window.py.

Vérifie que SettingsWindow se contente d'assembler les quatre
panneaux dans un QTabWidget (aucune logique métier propre), que
chaque onglet reçoit le bon service, et qu'elle s'intègre au socle
BaseWindow comme les autres modules de la suite.

QSettings("ON3RT","CATServer") (utilisée en interne par RadioPanel)
est isolée vers un fichier .ini temporaire : jamais le vrai registre.
"""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QTabWidget

from apps.settings.panels import radio_panel as radio_panel_module
from apps.settings.settings_service import SettingsService
from libraries.station.station_service import StationService
from libraries.ui.base_window import BaseWindow


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_qsettings(tmp_path, monkeypatch):
    ini_path = tmp_path / "catserver_test.ini"

    def fake_qsettings(*args, **kwargs):
        return QSettings(str(ini_path), QSettings.Format.IniFormat)

    monkeypatch.setattr(radio_panel_module, "QSettings", fake_qsettings)
    yield ini_path


@pytest.fixture(autouse=True)
def fake_ports(monkeypatch):
    class FakePortInfo:
        def __init__(self, device):
            self.device = device

    monkeypatch.setattr(radio_panel_module.list_ports, "comports", lambda: [])


@pytest.fixture
def station_service(tmp_path):
    return StationService(config_path=tmp_path / "station.json")


@pytest.fixture
def settings_service(tmp_path):
    return SettingsService(config_path=tmp_path / "settings.json")


@pytest.fixture
def window(qapp, station_service, settings_service):
    from apps.settings.window import SettingsWindow
    w = SettingsWindow(station_service=station_service, settings_service=settings_service)
    yield w
    w.close()


def test_window_builds_and_is_a_base_window(window):
    assert isinstance(window, BaseWindow)
    assert window.windowTitle() == "ON3RT Radio Suite - Settings"


def test_window_has_exactly_four_tabs_in_order(window):
    tabs = window.tabs
    assert isinstance(tabs, QTabWidget)
    assert tabs.count() == 4
    assert [tabs.tabText(i) for i in range(4)] == ["Station", "Radio", "Réseau", "Services"]


def test_each_tab_holds_the_expected_panel_type(window):
    from apps.settings.panels.station_panel import StationPanel
    from apps.settings.panels.radio_panel import RadioPanel
    from apps.settings.panels.network_panel import NetworkPanel
    from apps.settings.panels.services_panel import ServicesPanel

    assert isinstance(window.tabs.widget(0), StationPanel)
    assert isinstance(window.tabs.widget(1), RadioPanel)
    assert isinstance(window.tabs.widget(2), NetworkPanel)
    assert isinstance(window.tabs.widget(3), ServicesPanel)


def test_each_panel_receives_the_service_injected_into_the_window(window, station_service, settings_service):
    assert window.station_panel.station_service is station_service
    assert window.network_panel.settings_service is settings_service
    assert window.services_panel.settings_service is settings_service


def test_radio_service_defaults_to_none_and_is_passed_through(qapp, station_service, settings_service):
    from apps.settings.window import SettingsWindow

    w = SettingsWindow(station_service=station_service, settings_service=settings_service)

    assert w.radio_service is None
    assert w.radio_panel.radio_service is None

    w.close()


def test_saving_the_station_panel_does_not_affect_settings_service(window, settings_service):
    """
    Non-régression : la fenêtre ne partage aucun état entre panneaux
    au-delà des services qu'elle leur injecte — sauvegarder Station ne
    doit rien changer côté SettingsService.
    """
    original_network = dict(settings_service.network)
    original_services = dict(settings_service.services)

    window.station_panel.edit_callsign.setText("F4XYZ")
    window.station_panel.btn_save.click()

    assert settings_service.network == original_network
    assert settings_service.services == original_services
