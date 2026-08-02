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
    assert service.cw["wpm"] == 20
    assert service.cw["farnsworth_wpm"] is None
    assert service.cw["keyer_backend"] == "ptt"
    assert service.cw["winkeyer_port"] == ""
    assert service.cw["sidetone_hz"] == 700
    assert service.cw["macros"] == [""] * 12


def test_save_then_reload_round_trips(tmp_path):
    path = tmp_path / "settings.json"

    service = SettingsService(config_path=path)
    service.network["hamqth_username"] = "ON3RT"
    service.services["dxcluster_port"] = 7300
    service.cw["wpm"] = 25
    service.cw["farnsworth_wpm"] = 15
    service.cw["sidetone_hz"] = 600
    service.save()

    assert path.exists()

    reloaded = SettingsService(config_path=path)
    assert reloaded.network["hamqth_username"] == "ON3RT"
    assert reloaded.services["dxcluster_port"] == 7300
    # Une clé non modifiée garde sa valeur par défaut après un aller-retour.
    assert reloaded.services["dxcluster_host"] == "dxfun.com"
    assert reloaded.cw["wpm"] == 25
    assert reloaded.cw["farnsworth_wpm"] == 15
    assert reloaded.cw["keyer_backend"] == "ptt"  # non modifie -> garde son defaut
    assert reloaded.cw["sidetone_hz"] == 600


def test_cw_farnsworth_none_round_trips_correctly(tmp_path):
    """None (pas de Farnsworth) doit survivre un aller-retour JSON (null), pas devenir une autre valeur."""

    path = tmp_path / "settings.json"

    service = SettingsService(config_path=path)
    service.cw["farnsworth_wpm"] = 12
    service.save()
    service.cw["farnsworth_wpm"] = None
    service.save()

    reloaded = SettingsService(config_path=path)
    assert reloaded.cw["farnsworth_wpm"] is None


def test_cw_macros_round_trip_correctly(tmp_path):
    """Les 12 emplacements F1-F12 (texte fixe) doivent survivre un aller-retour JSON."""

    path = tmp_path / "settings.json"

    service = SettingsService(config_path=path)
    macros = ["CQ CQ DE ON3RT"] + [""] * 10 + ["73"]
    service.cw["macros"] = macros
    service.save()

    reloaded = SettingsService(config_path=path)
    assert reloaded.cw["macros"] == macros


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
    assert service.cw["wpm"] == 20  # section "cw" absente d'un fichier plus ancien -> défauts
    assert service.cw["sidetone_hz"] == 700  # idem pour un champ ajouté après coup
    assert service.cw["macros"] == [""] * 12  # idem pour "macros", ajouté à l'étape 2d


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
