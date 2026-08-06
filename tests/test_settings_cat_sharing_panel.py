"""
Tests de apps/settings/panels/cat_sharing_panel.py.

Vérifie que CatSharingPanel lit et écrit exclusivement
SettingsService.cat_sharing, sans jamais créer ni importer
CatSharingService ni RigctldAdapter — même raisonnement que LivePanel
pour LiveServerService.
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
    from apps.settings.panels.cat_sharing_panel import CatSharingPanel
    p = CatSharingPanel(settings_service)
    yield p
    p.close()


def test_panel_does_not_import_cat_sharing_service_or_rigctld_adapter():
    """
    Non-régression architecturale : ce panneau ne doit importer ni
    CatSharingService ni RigctldAdapter -- vérifié sur l'espace de noms
    réel du module importé (pas une recherche textuelle, qui serait
    faussée par ces mêmes noms mentionnés en prose dans la docstring).
    """
    import apps.settings.panels.cat_sharing_panel as module

    forbidden_names = (
        "CatSharingService",
        "RigctldAdapter",
        "RadioService",
    )

    for name in forbidden_names:
        assert not hasattr(module, name), f"{name} ne doit pas être importé dans ce panneau"


# ------------------------------------------------------------------
# Chargement depuis SettingsService
# ------------------------------------------------------------------

def test_panel_loads_default_values_from_service(panel):
    assert panel.check_enabled.isChecked() is False
    assert panel.spin_port.value() == 4532


def test_panel_loads_custom_values_from_service(qapp, tmp_path):
    from apps.settings.panels.cat_sharing_panel import CatSharingPanel

    service = SettingsService(config_path=tmp_path / "settings.json")
    service.cat_sharing["enabled"] = True
    service.cat_sharing["port"] = 9000

    panel = CatSharingPanel(service)

    assert panel.check_enabled.isChecked() is True
    assert panel.spin_port.value() == 9000

    panel.close()


# ------------------------------------------------------------------
# Édition sans sauvegarde -> le service n'est pas modifié
# ------------------------------------------------------------------

def test_editing_fields_without_saving_does_not_touch_the_service(panel, settings_service):
    panel.check_enabled.setChecked(True)
    panel.spin_port.setValue(9000)

    assert settings_service.cat_sharing["enabled"] is False
    assert settings_service.cat_sharing["port"] == 4532


# ------------------------------------------------------------------
# Sauvegarde -> écriture dans le service
# ------------------------------------------------------------------

def test_clicking_save_writes_values_back_to_the_service(panel, settings_service):
    panel.check_enabled.setChecked(True)
    panel.spin_port.setValue(9000)

    panel.btn_save.click()

    assert settings_service.cat_sharing["enabled"] is True
    assert settings_service.cat_sharing["port"] == 9000


def test_clicking_save_persists_to_disk(panel, settings_service):
    panel.check_enabled.setChecked(True)
    panel.btn_save.click()

    reloaded = SettingsService(config_path=settings_service._path)
    assert reloaded.cat_sharing["enabled"] is True


def test_clicking_save_does_not_affect_other_sections(panel, settings_service):
    """Non-régression : ce panneau ne touche jamais à network/services/cw/live."""

    original_network = dict(settings_service.network)
    original_services = dict(settings_service.services)
    original_cw = dict(settings_service.cw)
    original_live = dict(settings_service.live)

    panel.btn_save.click()

    assert settings_service.network == original_network
    assert settings_service.services == original_services
    assert settings_service.cw == original_cw
    assert settings_service.live == original_live
