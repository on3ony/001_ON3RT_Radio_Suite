"""
Tests de apps/settings/panels/cw_panel.py.

Vérifie que CWPanel lit et écrit exclusivement SettingsService.cw, sans
jamais créer ni importer CWService/PTTKeyerBackend/NullKeyerBackend ni
aucun module matériel réel (voir libraries/cw/).
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
    from apps.settings.panels.cw_panel import CWPanel
    p = CWPanel(settings_service)
    yield p
    p.close()


def test_panel_does_not_import_any_live_service_module():
    """
    Non-régression architecturale : ce panneau ne doit importer ni
    CWService, ni PTTKeyerBackend, ni NullKeyerBackend, ni aucun module
    matériel réel -- vérifié sur l'espace de noms réel du module
    importé (pas une recherche textuelle, qui serait faussée par ces
    mêmes noms mentionnés en prose dans la docstring).
    """
    import apps.settings.panels.cw_panel as module

    forbidden_names = (
        "CWService",
        "PTTKeyerBackend",
        "NullKeyerBackend",
        "MorseEncoder",
        "TimingEngine",
        "PTTGuard",
        "RadioService",
    )

    for name in forbidden_names:
        assert not hasattr(module, name), f"{name} ne doit pas être importé dans ce panneau"


# ------------------------------------------------------------------
# Chargement depuis SettingsService
# ------------------------------------------------------------------

def test_panel_loads_default_values_from_service(panel):
    assert panel.spin_wpm.value() == 20
    assert panel.check_farnsworth.isChecked() is False
    assert panel.spin_farnsworth_wpm.isEnabled() is False
    assert panel.spin_sidetone_hz.value() == 700


def test_panel_loads_custom_values_from_service(qapp, tmp_path):
    from apps.settings.panels.cw_panel import CWPanel

    service = SettingsService(config_path=tmp_path / "settings.json")
    service.cw["wpm"] = 30
    service.cw["farnsworth_wpm"] = 15
    service.cw["sidetone_hz"] = 600

    panel = CWPanel(service)

    assert panel.spin_wpm.value() == 30
    assert panel.check_farnsworth.isChecked() is True
    assert panel.spin_farnsworth_wpm.value() == 15
    assert panel.spin_farnsworth_wpm.isEnabled() is True
    assert panel.spin_sidetone_hz.value() == 600

    panel.close()


# ------------------------------------------------------------------
# Édition sans sauvegarde -> le service n'est pas modifié
# ------------------------------------------------------------------

def test_editing_fields_without_saving_does_not_touch_the_service(panel, settings_service):
    panel.spin_wpm.setValue(40)
    panel.check_farnsworth.setChecked(True)
    panel.spin_farnsworth_wpm.setValue(18)
    panel.spin_sidetone_hz.setValue(500)

    assert settings_service.cw["wpm"] == 20
    assert settings_service.cw["farnsworth_wpm"] is None
    assert settings_service.cw["sidetone_hz"] == 700


# ------------------------------------------------------------------
# Sauvegarde -> écriture dans le service
# ------------------------------------------------------------------

def test_clicking_save_writes_converted_values_back_to_the_service(panel, settings_service):
    panel.spin_wpm.setValue(25)
    panel.check_farnsworth.setChecked(True)
    panel.spin_farnsworth_wpm.setValue(18)
    panel.spin_sidetone_hz.setValue(500)

    panel.btn_save.click()

    assert settings_service.cw["wpm"] == 25
    assert settings_service.cw["farnsworth_wpm"] == 18
    assert settings_service.cw["sidetone_hz"] == 500


def test_clicking_save_with_farnsworth_unchecked_writes_none(panel, settings_service):
    panel.spin_wpm.setValue(25)
    panel.check_farnsworth.setChecked(True)
    panel.spin_farnsworth_wpm.setValue(18)
    panel.check_farnsworth.setChecked(False)

    panel.btn_save.click()

    assert settings_service.cw["farnsworth_wpm"] is None


def test_clicking_save_persists_to_disk(panel, settings_service):
    panel.spin_wpm.setValue(35)
    panel.btn_save.click()

    reloaded = SettingsService(config_path=settings_service._path)
    assert reloaded.cw["wpm"] == 35


def test_clicking_save_does_not_affect_other_sections(panel, settings_service):
    """Non-régression : ce panneau ne touche jamais à network/services."""

    original_network = dict(settings_service.network)
    original_services = dict(settings_service.services)

    panel.btn_save.click()

    assert settings_service.network == original_network
    assert settings_service.services == original_services


# ------------------------------------------------------------------
# Plafond dynamique : Farnsworth ne peut jamais dépasser le WPM courant
# ------------------------------------------------------------------

def test_lowering_wpm_below_current_farnsworth_value_clamps_it_down(panel):
    panel.spin_wpm.setValue(30)
    panel.check_farnsworth.setChecked(True)
    panel.spin_farnsworth_wpm.setValue(28)

    panel.spin_wpm.setValue(20)  # abaisse sous la valeur Farnsworth actuelle

    assert panel.spin_farnsworth_wpm.value() <= 20
    assert panel.spin_farnsworth_wpm.maximum() == 20


def test_farnsworth_spinbox_is_disabled_until_checkbox_is_checked(panel):
    assert panel.spin_farnsworth_wpm.isEnabled() is False
    panel.check_farnsworth.setChecked(True)
    assert panel.spin_farnsworth_wpm.isEnabled() is True
    panel.check_farnsworth.setChecked(False)
    assert panel.spin_farnsworth_wpm.isEnabled() is False
