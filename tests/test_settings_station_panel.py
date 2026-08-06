"""
Tests de apps/settings/panels/station_panel.py.

Vérifie que StationPanel lit et écrit exclusivement via StationService
(reçu en injection, jamais créé par le panneau), et que les champs
hors périmètre (antennas/interfaces/timezone) survivent intacts à un
enregistrement.
"""

import pytest

from libraries.station.station_service import StationService


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def station_service(tmp_path):
    service = StationService(config_path=tmp_path / "station.json")
    service.callsign = "ON3RT"
    service.operator_name = "Jean Dupont"
    service.locator = "JO20EU"
    service.qth = "Bruxelles"
    service.latitude = 50.90
    service.longitude = 4.42
    service.altitude = 55
    service.antennas = ["Dipole 80m"]
    service.interfaces = {"cat": "COM3"}
    service.timezone = "Europe/Brussels"
    service.license_class = "ON3"
    return service


@pytest.fixture
def panel(qapp, station_service):
    from apps.settings.panels.station_panel import StationPanel
    p = StationPanel(station_service)
    yield p
    p.close()


def test_panel_builds_and_loads_fields_from_service(panel, station_service):
    assert panel.edit_callsign.text() == "ON3RT"
    assert panel.edit_operator_name.text() == "Jean Dupont"
    assert panel.edit_locator.text() == "JO20EU"
    assert panel.edit_qth.text() == "Bruxelles"
    assert panel.spin_latitude.value() == pytest.approx(50.90)
    assert panel.spin_longitude.value() == pytest.approx(4.42)
    assert panel.spin_altitude.value() == 55
    assert panel.combo_license.currentData() == "ON3"


def test_panel_handles_unconfigured_station_without_crashing(qapp, tmp_path):
    from apps.settings.panels.station_panel import StationPanel

    empty_service = StationService(config_path=tmp_path / "station.json")
    panel = StationPanel(empty_service)

    assert panel.edit_callsign.text() == ""
    assert panel.spin_latitude.value() == pytest.approx(0.0)
    assert panel.spin_longitude.value() == pytest.approx(0.0)
    assert panel.spin_altitude.value() == 0
    assert panel.combo_license.currentData() is not None  # une classe par défaut est sélectionnée, jamais rien

    panel.close()


def test_editing_fields_without_saving_does_not_touch_the_service(panel, station_service):
    panel.edit_callsign.setText("F4XYZ")
    panel.spin_altitude.setValue(999)
    panel.combo_license.setCurrentIndex(0)

    assert station_service.callsign == "ON3RT"
    assert station_service.altitude == 55
    assert station_service.license_class == "ON3"


def test_clicking_save_writes_edited_values_back_to_the_service(panel, station_service):
    panel.edit_callsign.setText("F4XYZ")
    panel.edit_operator_name.setText("Marie Curie")
    panel.edit_locator.setText("JN18DU")
    panel.edit_qth.setText("Paris")
    panel.spin_latitude.setValue(48.85)
    panel.spin_longitude.setValue(2.35)
    panel.spin_altitude.setValue(35)
    panel.combo_license.setCurrentIndex(0)  # HAREC (premier de la liste, différent du "ON3" initial)

    panel.btn_save.click()

    assert station_service.callsign == "F4XYZ"
    assert station_service.operator_name == "Marie Curie"
    assert station_service.locator == "JN18DU"
    assert station_service.qth == "Paris"
    assert station_service.latitude == pytest.approx(48.85)
    assert station_service.longitude == pytest.approx(2.35)
    assert station_service.altitude == 35
    assert station_service.license_class == "HAREC"


def test_clicking_save_persists_to_disk(panel, station_service):
    panel.edit_callsign.setText("F4XYZ")
    panel.btn_save.click()

    reloaded = StationService(config_path=station_service._path)
    assert reloaded.callsign == "F4XYZ"


def test_clicking_save_persists_license_class_to_disk(panel, station_service):
    panel.combo_license.setCurrentIndex(0)  # HAREC
    panel.btn_save.click()

    reloaded = StationService(config_path=station_service._path)
    assert reloaded.license_class == "HAREC"


def test_combo_license_is_populated_from_the_registry_not_hardcoded(panel):
    """
    Non-régression architecturale : la liste déroulante doit refléter
    exactement license_privileges.available_license_classes(), jamais
    une liste dupliquée en dur dans le panneau.
    """
    from libraries.radio.license_privileges import available_license_classes

    expected_ids = [class_id for class_id, _label in available_license_classes()]
    actual_ids = [panel.combo_license.itemData(i) for i in range(panel.combo_license.count())]

    assert actual_ids == expected_ids


def test_panel_module_never_imports_privilege_logic():
    """
    Non-régression demandée explicitement : ce panneau ne doit
    connaître aucune règle de privilège (quelles bandes une classe
    autorise) -- seulement la liste des classes disponibles.
    """
    import inspect

    import apps.settings.panels.station_panel as module

    source = inspect.getsource(module)

    assert "allowed_bands" not in source
    assert "LICENSE_CLASSES" not in source


def test_clicking_save_does_not_affect_fields_outside_this_panels_scope(panel, station_service):
    """
    Non-régression : antennas/interfaces/timezone n'appartiennent pas
    au périmètre de ce panneau et doivent survivre intacts.
    """
    panel.edit_callsign.setText("F4XYZ")
    panel.btn_save.click()

    assert station_service.antennas == ["Dipole 80m"]
    assert station_service.interfaces == {"cat": "COM3"}
    assert station_service.timezone == "Europe/Brussels"
