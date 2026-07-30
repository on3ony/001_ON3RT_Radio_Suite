"""
Tests de apps/settings/panels/network_panel.py.

Vérifie : QRZ passe uniquement par les fonctions existantes de
libraries/qrz/service.py (jamais dupliquées, jamais de connexion
réseau automatique) ; HamQTH/LoTW/eQSL/Club Log sont de purs
champs stockés dans SettingsService.network ; aucun bouton "Tester" ;
aucune régression sur les autres sections de SettingsService.

_config_file() de libraries/qrz/service.py est systématiquement
monkeypatché vers un fichier temporaire : ces tests ne doivent jamais
lire ni écrire le vrai config/qrz.json du dépôt.
"""

import json

import pytest
from PySide6.QtWidgets import QPushButton

from apps.settings.settings_service import SettingsService
from libraries.qrz import service as qrz_service


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_qrz_config(tmp_path, monkeypatch):
    fake_path = tmp_path / "qrz.json"
    monkeypatch.setattr(qrz_service, "_config_file", lambda: fake_path)
    monkeypatch.setattr(qrz_service, "_client", None)
    yield fake_path


@pytest.fixture
def settings_service(tmp_path):
    return SettingsService(config_path=tmp_path / "settings.json")


@pytest.fixture
def panel(qapp, settings_service):
    from apps.settings.panels.network_panel import NetworkPanel
    p = NetworkPanel(settings_service)
    yield p
    p.close()


def test_panel_builds_with_no_qrz_json(panel):
    assert panel.edit_qrz_username.text() == ""
    assert panel.edit_qrz_password.text() == ""


def test_panel_loads_existing_qrz_credentials(qapp, settings_service, isolated_qrz_config):
    isolated_qrz_config.write_text(
        json.dumps({"username": "ON3RT", "password": "secret123"}),
        encoding="utf-8",
    )

    from apps.settings.panels.network_panel import NetworkPanel
    panel = NetworkPanel(settings_service)

    assert panel.edit_qrz_username.text() == "ON3RT"
    assert panel.edit_qrz_password.text() == "secret123"

    panel.close()


def test_panel_loads_network_section_from_settings_service(qapp, settings_service):
    settings_service.network["hamqth_username"] = "ON3RT"
    settings_service.network["clublog_email"] = "on3rt@example.com"

    from apps.settings.panels.network_panel import NetworkPanel
    panel = NetworkPanel(settings_service)

    assert panel.edit_hamqth_username.text() == "ON3RT"
    assert panel.edit_clublog_email.text() == "on3rt@example.com"
    assert panel.edit_lotw_username.text() == ""
    assert panel.edit_eqsl_username.text() == ""

    panel.close()


def test_opening_the_panel_never_triggers_a_qrz_network_call(qapp, settings_service, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("client()/login() ne doit jamais être appelé à l'ouverture du panneau")

    monkeypatch.setattr(qrz_service, "client", fail_if_called)

    from apps.settings.panels.network_panel import NetworkPanel
    panel = NetworkPanel(settings_service)
    panel.close()  # aucune AssertionError levée => aucun appel réseau déclenché


def test_no_test_connection_button_exists(panel):
    buttons = panel.findChildren(QPushButton)
    labels = [b.text().lower() for b in buttons]

    assert not any("test" in label for label in labels)
    assert labels.count("enregistrer") == 1  # un seul bouton d'action pour tout le panneau


def test_save_writes_qrz_credentials_via_existing_function(panel, isolated_qrz_config):
    panel.edit_qrz_username.setText("ON3RT")
    panel.edit_qrz_password.setText("secret123")

    panel.btn_save.click()

    data = json.loads(isolated_qrz_config.read_text(encoding="utf-8"))
    assert data == {"username": "ON3RT", "password": "secret123"}


def test_save_writes_all_four_new_integrations_to_settings_service(panel, settings_service):
    panel.edit_hamqth_username.setText("hamqth_user")
    panel.edit_hamqth_password.setText("hamqth_pass")
    panel.edit_lotw_username.setText("lotw_user")
    panel.edit_lotw_password.setText("lotw_pass")
    panel.edit_eqsl_username.setText("eqsl_user")
    panel.edit_eqsl_password.setText("eqsl_pass")
    panel.edit_clublog_email.setText("club@example.com")
    panel.edit_clublog_password.setText("club_pass")

    panel.btn_save.click()

    assert settings_service.network == {
        "hamqth_username": "hamqth_user",
        "hamqth_password": "hamqth_pass",
        "lotw_username": "lotw_user",
        "lotw_password": "lotw_pass",
        "eqsl_username": "eqsl_user",
        "eqsl_password": "eqsl_pass",
        "clublog_email": "club@example.com",
        "clublog_password": "club_pass",
    }


def test_save_persists_settings_service_to_disk(panel, settings_service):
    panel.edit_hamqth_username.setText("hamqth_user")
    panel.btn_save.click()

    reloaded = SettingsService(config_path=settings_service._path)
    assert reloaded.network["hamqth_username"] == "hamqth_user"


def test_save_does_not_affect_the_services_section(panel, settings_service):
    """Non-régression : ce panneau ne touche jamais à SettingsService.services."""

    original_services = dict(settings_service.services)

    panel.btn_save.click()

    assert settings_service.services == original_services
