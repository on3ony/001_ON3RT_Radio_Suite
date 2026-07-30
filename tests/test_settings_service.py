"""
Tests de apps/settings/settings_service.py.

Vérifie : valeurs par défaut, persistance atomique, et
rétrocompatibilité (clé absente d'un fichier plus ancien -> défaut
conservé ; clé/section inconnue d'un fichier plus récent -> ignorée
sans erreur, et donc supprimée au save() suivant).
"""

import json

from apps.settings.settings_service import SettingsService


def test_defaults_when_no_file_exists(tmp_path):
    service = SettingsService(config_path=tmp_path / "settings.json")

    assert service.network["hamqth_username"] == ""
    assert service.network["lotw_password"] == ""
    assert service.services["open_meteo_poll_interval_ms"] == 10 * 60 * 1000
    assert service.services["hamqsl_poll_interval_ms"] == 60 * 60 * 1000
    assert service.services["dxcluster_host"] == "dxfun.com"
    assert service.services["dxcluster_port"] == 8000


def test_save_then_reload_round_trips(tmp_path):
    path = tmp_path / "settings.json"

    service = SettingsService(config_path=path)
    service.network["hamqth_username"] = "ON3RT"
    service.services["dxcluster_port"] = 7300
    service.save()

    assert path.exists()

    reloaded = SettingsService(config_path=path)
    assert reloaded.network["hamqth_username"] == "ON3RT"
    assert reloaded.services["dxcluster_port"] == 7300
    # Une clé non modifiée garde sa valeur par défaut après un aller-retour.
    assert reloaded.services["dxcluster_host"] == "dxfun.com"


def test_missing_key_in_older_file_keeps_default(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"network": {"hamqth_username": "ON3RT"}}),
        encoding="utf-8",
    )

    service = SettingsService(config_path=path)

    assert service.network["hamqth_username"] == "ON3RT"
    assert service.network["lotw_username"] == ""  # absent du fichier -> défaut
    assert service.services["dxcluster_host"] == "dxfun.com"  # section absente -> défauts


def test_unknown_key_and_section_in_newer_file_are_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "network": {"hamqth_username": "ON3RT", "future_field": "???"},
                "future_section": {"anything": True},
            }
        ),
        encoding="utf-8",
    )

    service = SettingsService(config_path=path)

    assert service.network["hamqth_username"] == "ON3RT"
    assert "future_field" not in service.network
    assert not hasattr(service, "future_section")


def test_corrupt_file_keeps_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ceci n'est pas du JSON", encoding="utf-8")

    service = SettingsService(config_path=path)

    assert service.network["hamqth_username"] == ""
    assert service.services["dxcluster_port"] == 8000


def test_save_drops_unknown_keys_from_a_previous_version(tmp_path):
    """
    Un champ inconnu lu depuis le fichier n'est jamais réécrit : au
    prochain save(), seules les clés connues de cette version
    persistent (même comportement que StationService).
    """
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"network": {"hamqth_username": "ON3RT", "obsolete_field": "x"}}),
        encoding="utf-8",
    )

    service = SettingsService(config_path=path)
    service.save()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "obsolete_field" not in data["network"]
    assert data["network"]["hamqth_username"] == "ON3RT"
