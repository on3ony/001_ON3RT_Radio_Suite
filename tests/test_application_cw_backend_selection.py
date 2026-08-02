"""
Tests de la sélection du backend/driver CW dans core/application.py
(étape 4) : settings_service.cw["keyer_backend"] choisit entre
CIVTextKeyerBackend (+ TextDriver) et PTTKeyerBackend (+ ElementDriver,
comportement par défaut, inchangé depuis l'étape 2a).

Vérifie uniquement le choix fait par Application -- CWService,
TextDriver, ElementDriver, CIVTextKeyerBackend et PTTKeyerBackend
eux-mêmes sont déjà couverts par leurs propres suites de tests, jamais
modifiés par cette étape.
"""

import pytest
from PySide6.QtCore import QSettings

import core.application as application_module
from apps.cat_server.cw_civ_text_backend import CIVTextKeyerBackend
from apps.cat_server.cw_ptt_backend import PTTKeyerBackend
from apps.settings.settings_service import SettingsService
from libraries.cw.element_driver import ElementDriver
from libraries.cw.text_driver import TextDriver


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


def _application_with_keyer_backend(tmp_path, monkeypatch, keyer_backend: str | None):
    """
    Construit une vraie Application dont settings_service pointe vers
    un config/settings.json jetable, pré-rempli avec le
    "keyer_backend" demandé avant l'instanciation (Application lit ce
    réglage de façon synchrone à la construction de cw_service).
    """

    settings_path = tmp_path / "settings.json"

    if keyer_backend is not None:
        seed = SettingsService(config_path=settings_path)
        seed.cw["keyer_backend"] = keyer_backend
        seed.save()

    monkeypatch.setattr(
        application_module,
        "SettingsService",
        lambda: SettingsService(config_path=settings_path),
    )

    from core.application import Application
    return Application()


# ------------------------------------------------------------------
# "civ_text" -> CIVTextKeyerBackend + TextDriver
# ------------------------------------------------------------------

def test_civ_text_keyer_backend_selects_civ_text_backend_and_text_driver(qapp, tmp_path, monkeypatch):
    application = _application_with_keyer_backend(tmp_path, monkeypatch, "civ_text")

    try:
        driver = application.cw_service._driver
        assert isinstance(driver, TextDriver)
        assert isinstance(driver._backend, CIVTextKeyerBackend)
        assert driver._backend._radio_service is application.radio_service
        assert driver._backend._ptt_guard is application.ptt_guard
    finally:
        application.close_all()


# ------------------------------------------------------------------
# Défaut ("ptt", ou toute valeur inconnue/absente) -> comportement
# inchangé depuis l'étape 2a : PTTKeyerBackend + ElementDriver
# ------------------------------------------------------------------

def test_ptt_keyer_backend_selects_ptt_backend_and_element_driver(qapp, tmp_path, monkeypatch):
    application = _application_with_keyer_backend(tmp_path, monkeypatch, "ptt")

    try:
        driver = application.cw_service._driver
        assert isinstance(driver, ElementDriver)
        assert isinstance(driver._backend, PTTKeyerBackend)
        assert driver._backend._ptt_guard is application.ptt_guard
    finally:
        application.close_all()


def test_default_settings_with_no_config_file_selects_ptt_backend(qapp, tmp_path, monkeypatch):
    """Aucun config/settings.json (première installation) : "ptt" est le défaut de SettingsService."""

    application = _application_with_keyer_backend(tmp_path, monkeypatch, None)

    try:
        driver = application.cw_service._driver
        assert isinstance(driver, ElementDriver)
        assert isinstance(driver._backend, PTTKeyerBackend)
    finally:
        application.close_all()


def test_unknown_keyer_backend_value_falls_back_to_ptt(qapp, tmp_path, monkeypatch):
    """Une valeur de settings.json ni "civ_text" ni "ptt" (ex. future valeur non encore supportée) reste sûre : PTT par défaut."""

    application = _application_with_keyer_backend(tmp_path, monkeypatch, "winkeyer")

    try:
        driver = application.cw_service._driver
        assert isinstance(driver, ElementDriver)
        assert isinstance(driver._backend, PTTKeyerBackend)
    finally:
        application.close_all()


# ------------------------------------------------------------------
# wpm/farnsworth_wpm toujours transmis, quel que soit le backend choisi
# ------------------------------------------------------------------

def test_wpm_and_farnsworth_are_still_read_from_settings_regardless_of_backend(qapp, tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    seed = SettingsService(config_path=settings_path)
    seed.cw["keyer_backend"] = "civ_text"
    seed.cw["wpm"] = 22
    seed.cw["farnsworth_wpm"] = 10
    seed.save()

    monkeypatch.setattr(
        application_module,
        "SettingsService",
        lambda: SettingsService(config_path=settings_path),
    )

    from core.application import Application
    application = Application()

    try:
        assert application.cw_service.wpm == 22
        assert application.cw_service.farnsworth_wpm == 10
    finally:
        application.close_all()
