"""
Tests de libraries/station/station_service.py.

Se concentre sur l'ajout du champ operator_name : valeur par défaut,
persistance, et surtout compatibilité totale avec un station.json
existant qui ne connaît pas encore ce champ (ancien format).
"""

import json

from libraries.station.station_service import StationService


def test_operator_name_defaults_to_empty_string(tmp_path):
    service = StationService(config_path=tmp_path / "station.json")

    assert service.operator_name == ""


def test_loading_an_old_format_file_without_operator_name_does_not_crash(tmp_path):
    """
    Un station.json écrit avant l'ajout de ce champ ne doit ni faire
    planter le chargement, ni affecter les autres champs déjà présents.
    """
    path = tmp_path / "station.json"
    path.write_text(
        json.dumps(
            {
                "callsign": "ON3RT",
                "locator": "JO20EU",
                "qth": "Bruxelles",
                "latitude": 50.90,
                "longitude": 4.42,
            }
        ),
        encoding="utf-8",
    )

    service = StationService(config_path=path)

    assert service.operator_name == ""
    assert service.callsign == "ON3RT"
    assert service.locator == "JO20EU"
    assert service.qth == "Bruxelles"
    assert service.latitude == 50.90
    assert service.longitude == 4.42


def test_loading_the_actual_repository_station_json_still_works():
    """
    Non-régression directe sur le vrai fichier config/station.json du
    dépôt (écrit avant ce champ) : doit toujours se charger sans erreur
    et avec les mêmes valeurs qu'avant cette étape.
    """
    service = StationService()

    assert service.operator_name == ""
    assert service.callsign == "ON3RT"
    assert service.locator == "JO20EU"
    assert service.qth == "Bruxelles"


def test_save_then_reload_round_trips_operator_name(tmp_path):
    path = tmp_path / "station.json"

    service = StationService(config_path=path)
    service.operator_name = "Jean Dupont"
    service.callsign = "ON3RT"
    service.save()

    reloaded = StationService(config_path=path)

    assert reloaded.operator_name == "Jean Dupont"
    assert reloaded.callsign == "ON3RT"


def test_info_includes_operator_name(tmp_path):
    service = StationService(config_path=tmp_path / "station.json")
    service.operator_name = "Jean Dupont"

    assert service.info()["operator_name"] == "Jean Dupont"


def test_other_fields_are_unaffected(tmp_path):
    """
    Non-régression : tous les champs existants avant cette étape se
    comportent exactement comme avant (round-trip complet).
    """
    path = tmp_path / "station.json"

    service = StationService(config_path=path)
    service.callsign = "ON3RT"
    service.locator = "JO20EU"
    service.latitude = 50.90
    service.longitude = 4.42
    service.qth = "Bruxelles"
    service.altitude = 55
    service.antennas = ["Dipole 80m"]
    service.interfaces = {"cat": "COM3"}
    service.timezone = "Europe/Brussels"
    service.save()

    reloaded = StationService(config_path=path)

    assert reloaded.callsign == "ON3RT"
    assert reloaded.locator == "JO20EU"
    assert reloaded.latitude == 50.90
    assert reloaded.longitude == 4.42
    assert reloaded.qth == "Bruxelles"
    assert reloaded.altitude == 55
    assert reloaded.antennas == ["Dipole 80m"]
    assert reloaded.interfaces == {"cat": "COM3"}
    assert reloaded.timezone == "Europe/Brussels"
