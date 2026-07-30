"""
Tests de apps/settings/panels/services_panel.py.

Vérifie que ServicesPanel lit et écrit exclusivement
SettingsService.services, sans jamais créer ni importer
WeatherService/PropagationService/DXClusterService.
"""

import pytest

from apps.settings.settings_service import SettingsService


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def settings_service(tmp_path):
    return SettingsService(config_path=tmp_path / "settings.json")


@pytest.fixture
def panel(qapp, settings_service):
    from apps.settings.panels.services_panel import ServicesPanel
    p = ServicesPanel(settings_service)
    yield p
    p.close()


def test_panel_does_not_import_any_live_service_module():
    """
    Non-régression architecturale : ce panneau ne doit importer ni
    WeatherService, ni PropagationService, ni DXClusterService, ni
    aucune primitive réseau Qt — vérifié sur l'espace de noms réel du
    module importé (pas une recherche textuelle, qui serait faussée
    par ces mêmes noms mentionnés en prose dans la docstring).
    """
    import apps.settings.panels.services_panel as module

    forbidden_names = (
        "WeatherService",
        "PropagationService",
        "DXClusterService",
        "QNetworkAccessManager",
        "QTcpSocket",
    )

    for name in forbidden_names:
        assert not hasattr(module, name), f"{name} ne doit pas être importé dans ce panneau"


def test_panel_loads_default_values_from_service(panel):
    assert panel.spin_open_meteo_interval.value() == 10  # 10 * 60 * 1000 ms
    assert panel.spin_hamqsl_interval.value() == 60  # 60 * 60 * 1000 ms
    assert panel.edit_dxcluster_host.text() == "dxfun.com"
    assert panel.spin_dxcluster_port.value() == 8000


def test_panel_loads_custom_values_from_service(qapp, tmp_path):
    from apps.settings.panels.services_panel import ServicesPanel

    service = SettingsService(config_path=tmp_path / "settings.json")
    service.services["open_meteo_poll_interval_ms"] = 5 * 60 * 1000
    service.services["hamqsl_poll_interval_ms"] = 30 * 60 * 1000
    service.services["dxcluster_host"] = "cluster.example.com"
    service.services["dxcluster_port"] = 7300

    panel = ServicesPanel(service)

    assert panel.spin_open_meteo_interval.value() == 5
    assert panel.spin_hamqsl_interval.value() == 30
    assert panel.edit_dxcluster_host.text() == "cluster.example.com"
    assert panel.spin_dxcluster_port.value() == 7300

    panel.close()


def test_editing_fields_without_saving_does_not_touch_the_service(panel, settings_service):
    panel.spin_open_meteo_interval.setValue(99)
    panel.edit_dxcluster_host.setText("evil.example.com")

    assert settings_service.services["open_meteo_poll_interval_ms"] == 10 * 60 * 1000
    assert settings_service.services["dxcluster_host"] == "dxfun.com"


def test_clicking_save_writes_converted_values_back_to_the_service(panel, settings_service):
    panel.spin_open_meteo_interval.setValue(15)
    panel.spin_hamqsl_interval.setValue(45)
    panel.edit_dxcluster_host.setText("cluster.example.com")
    panel.spin_dxcluster_port.setValue(7300)

    panel.btn_save.click()

    assert settings_service.services["open_meteo_poll_interval_ms"] == 15 * 60 * 1000
    assert settings_service.services["hamqsl_poll_interval_ms"] == 45 * 60 * 1000
    assert settings_service.services["dxcluster_host"] == "cluster.example.com"
    assert settings_service.services["dxcluster_port"] == 7300


def test_clicking_save_persists_to_disk(panel, settings_service):
    panel.spin_dxcluster_port.setValue(7300)
    panel.btn_save.click()

    reloaded = SettingsService(config_path=settings_service._path)
    assert reloaded.services["dxcluster_port"] == 7300


def test_clicking_save_does_not_affect_the_network_section(panel, settings_service):
    """Non-régression : ce panneau ne touche jamais à SettingsService.network."""

    original_network = dict(settings_service.network)

    panel.btn_save.click()

    assert settings_service.network == original_network
