"""
Tests de la coordination RadioService <-> CWService dans core/application.py.

Bug matériel réel trouvé lors de la première validation IC-7300
(2026-08-02) : radio_service.timer interroge la radio en continu
(fréquence/mode/PTT, CI-V bloquant) sur la même liaison série que
PTTKeyerBackend pendant le keying CW -- concurrence qui gelait par
intermittence la boucle d'événements Qt (barre de progression figée,
bouton Stop sans effet apparent). Correctif : suspendre
radio_service.timer pendant toute émission CW (cw_started ->
cw_finished/cw_stopped/cw_error), le reprendre seulement si la radio
est toujours connectée.

Vérifie ce comportement sans aucun matériel réel (radio_service jamais
réellement connecté dans ces tests -- son minuteur est piloté à la main
pour simuler un état "en cours de polling"), et confirme qu'aucun
fichier de libraries/cw/ ni apps/cat_server/cw_ptt_backend.py n'est
nécessaire à cette coordination : seuls des signaux déjà publics de
CWService sont utilisés.
"""

import pytest
from PySide6.QtCore import QSettings

import core.application as application_module


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
    """
    ContestMessageService.__init__() sauvegarde immédiatement si son
    fichier de configuration n'existe pas encore (chargement du seed) :
    jamais le vrai data/contest_assistant.json du dépôt pendant les tests.
    """
    from apps.contest_assistant.message_service import ContestMessageService

    config_path = tmp_path / "contest_assistant.json"
    seed_path = tmp_path / "contest_assistant_seed.json"

    monkeypatch.setattr(
        application_module,
        "ContestMessageService",
        lambda: ContestMessageService(config_path=config_path, seed_path=seed_path),
    )


@pytest.fixture
def application(qapp):
    from core.application import Application
    app = Application()
    yield app
    app.close_all()


def _simulate_connected_and_polling(application) -> None:
    """
    radio_service n'est jamais réellement connecté dans ces tests (pas
    de port série) : on simule directement l'état "connectée et en
    cours de polling" pour tester la coordination indépendamment de
    connect()/poll() eux-mêmes, déjà couverts par d'autres tests.
    """

    application.radio_service.status.connected = True
    application.radio_service.timer.start()


# ------------------------------------------------------------------
# cw_started suspend le polling
# ------------------------------------------------------------------

def test_cw_started_stops_radio_polling(application):
    _simulate_connected_and_polling(application)
    assert application.radio_service.timer.isActive()

    application.cw_service.cw_started.emit("req-1")

    assert not application.radio_service.timer.isActive()


# ------------------------------------------------------------------
# Fin d'émission (finished/stopped/error) reprend le polling
# ------------------------------------------------------------------

def test_cw_finished_resumes_polling_if_still_connected(application):
    _simulate_connected_and_polling(application)

    application.cw_service.cw_started.emit("req-1")
    assert not application.radio_service.timer.isActive()

    application.cw_service.cw_finished.emit("req-1")
    assert application.radio_service.timer.isActive()


def test_cw_stopped_resumes_polling_if_still_connected(application):
    _simulate_connected_and_polling(application)

    application.cw_service.cw_started.emit("req-1")
    application.cw_service.cw_stopped.emit("req-1")

    assert application.radio_service.timer.isActive()


def test_cw_error_resumes_polling_if_still_connected(application):
    _simulate_connected_and_polling(application)

    application.cw_service.cw_started.emit("req-1")
    application.cw_service.cw_error.emit("req-1", "panne simulée")

    assert application.radio_service.timer.isActive()


# ------------------------------------------------------------------
# Ne jamais relancer le polling si la radio n'est plus connectée
# ------------------------------------------------------------------

def test_polling_not_resumed_if_radio_disconnected_during_transmission(application):
    _simulate_connected_and_polling(application)

    application.cw_service.cw_started.emit("req-1")

    # La radio a été déconnectée pendant l'émission (câble débranché,
    # action manuelle...) -- disconnect() a déjà arrêté le minuteur.
    application.radio_service.status.connected = False

    application.cw_service.cw_finished.emit("req-1")

    assert not application.radio_service.timer.isActive()


# ------------------------------------------------------------------
# Ne rien faire si aucune émission n'a mis le polling en pause
# ------------------------------------------------------------------

def test_transmission_ended_without_prior_started_does_not_start_polling(application):
    """
    Cas d'un échec synchrone immédiat de CWService.send() (ex. WPM
    invalide) : cw_started n'est jamais émis, seul cw_error l'est.
    Ne doit jamais relancer un polling que nous n'avons pas nous-mêmes
    mis en pause.
    """

    application.radio_service.status.connected = True
    assert not application.radio_service.timer.isActive()

    application.cw_service.cw_error.emit("req-x", "échec immédiat")

    assert not application.radio_service.timer.isActive()


def test_second_cw_cycle_pauses_and_resumes_polling_again(application):
    """Non-régression : le drapeau de pause doit se réarmer correctement pour une émission suivante."""

    _simulate_connected_and_polling(application)

    application.cw_service.cw_started.emit("req-1")
    application.cw_service.cw_finished.emit("req-1")
    assert application.radio_service.timer.isActive()

    application.cw_service.cw_started.emit("req-2")
    assert not application.radio_service.timer.isActive()

    application.cw_service.cw_stopped.emit("req-2")
    assert application.radio_service.timer.isActive()
