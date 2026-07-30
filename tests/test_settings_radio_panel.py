"""
Tests de apps/settings/panels/radio_panel.py.

Vérifie que RadioPanel se limite à Port COM/Vitesse CAT, réutilise
ConnectionPanel tel quel, et persiste via la même clé QSettings que
CATServerWindow — sans jamais toucher au vrai registre
QSettings("ON3RT","CATServer") de la machine (isolé via monkeypatch
vers un fichier .ini temporaire).
"""

import pytest
from PySide6.QtCore import QObject, QSettings, Signal

from apps.settings.panels import radio_panel as radio_panel_module


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_qsettings(tmp_path, monkeypatch):
    """
    Redirige QSettings("ON3RT","CATServer") vers un fichier .ini
    temporaire pour toute la durée du test : jamais le vrai registre.
    """
    ini_path = tmp_path / "catserver_test.ini"

    def fake_qsettings(*args, **kwargs):
        return QSettings(str(ini_path), QSettings.Format.IniFormat)

    monkeypatch.setattr(radio_panel_module, "QSettings", fake_qsettings)
    yield ini_path


@pytest.fixture(autouse=True)
def fake_ports(monkeypatch):
    """Aucun vrai port série requis pour ces tests."""

    class FakePortInfo:
        def __init__(self, device):
            self.device = device

    monkeypatch.setattr(
        radio_panel_module.list_ports,
        "comports",
        lambda: [FakePortInfo("COM3"), FakePortInfo("COM5")],
    )


class FakeRadioService(QObject):
    connectionChanged = Signal(bool)

    def __init__(self):
        super().__init__()
        self.connected = False
        self.port = ""
        self.baudrate = 19200
        self.model = None
        self.reconfigure_calls = []
        self.connect_result = True
        self.disconnect_called = False

    def reconfigure(self, port, baudrate):
        self.reconfigure_calls.append((port, baudrate))
        self.port = port
        self.baudrate = baudrate

    def connect(self):
        self.connected = self.connect_result
        if self.connected:
            self.model = "IC-7300"
            self.connectionChanged.emit(True)
        return self.connected

    def disconnect(self):
        self.disconnect_called = True
        self.connected = False
        self.connectionChanged.emit(False)


def test_panel_builds_without_radio_service(qapp):
    from apps.settings.panels.radio_panel import RadioPanel

    panel = RadioPanel(radio_service=None)

    assert panel.connection_panel.btn_connect.isEnabled()
    assert not panel.connection_panel.btn_disconnect.isEnabled()

    panel.close()


def test_only_port_and_baudrate_are_exposed(qapp):
    """
    Non-régression du périmètre demandé : ni CI-V, ni polling, ni
    timeout, ni modèle éditable — uniquement ce que ConnectionPanel
    expose déjà (port/baudrate/connexion).
    """
    from apps.settings.panels.radio_panel import RadioPanel

    panel = RadioPanel(radio_service=None)

    assert hasattr(panel.connection_panel, "cmb_port")
    assert hasattr(panel.connection_panel, "cmb_baud")
    assert not hasattr(panel, "civ_address_field")
    assert not hasattr(panel, "polling_field")
    assert not hasattr(panel, "timeout_field")

    panel.close()


def test_refresh_populates_ports_and_restores_last_values(qapp, isolated_qsettings):
    from apps.settings.panels.radio_panel import RadioPanel

    settings = QSettings(str(isolated_qsettings), QSettings.Format.IniFormat)
    settings.setValue("last_port", "COM5")
    settings.setValue("last_baudrate", 9600)
    settings.sync()

    panel = RadioPanel(radio_service=None)

    assert panel.connection_panel.selected_port() == "COM5"
    assert panel.connection_panel.selected_baudrate() == 9600

    panel.close()


def test_connecting_calls_reconfigure_and_persists_last_values(qapp, isolated_qsettings):
    from apps.settings.panels.radio_panel import RadioPanel

    service = FakeRadioService()
    panel = RadioPanel(radio_service=service)

    panel.connection_panel.set_selected_port("COM3")
    panel.connection_panel.set_selected_baudrate(19200)
    panel.connection_panel.btn_connect.click()

    assert service.reconfigure_calls == [("COM3", 19200)]
    assert service.connected is True
    assert panel.connection_panel.lbl_model.text() == "Modèle : IC-7300"

    settings = QSettings(str(isolated_qsettings), QSettings.Format.IniFormat)
    assert settings.value("last_port") == "COM3"
    assert settings.value("last_baudrate", type=int) == 19200

    panel.close()


def test_disconnecting_calls_service_disconnect(qapp):
    from apps.settings.panels.radio_panel import RadioPanel

    service = FakeRadioService()
    panel = RadioPanel(radio_service=service)

    panel.connection_panel.set_selected_port("COM3")
    panel.connection_panel.btn_connect.click()
    assert service.connected is True

    panel.connection_panel.btn_disconnect.click()

    assert service.disconnect_called is True
    assert not panel.connection_panel.btn_disconnect.isEnabled()

    panel.close()


def test_already_connected_service_is_reflected_on_open(qapp):
    """
    Si RadioService est déjà connecté à l'ouverture du panneau (service
    partagé démarré en arrière-plan par Application), l'état affiché
    doit refléter la connexion réelle sans action de l'utilisateur.
    """
    from apps.settings.panels.radio_panel import RadioPanel

    service = FakeRadioService()
    service.connected = True
    service.port = "COM5"  # doit figurer dans la liste des ports détectés (fake_ports) pour être sélectionnable
    service.baudrate = 38400
    service.model = "IC-7300"

    panel = RadioPanel(radio_service=service)

    assert not panel.connection_panel.btn_connect.isEnabled()
    assert panel.connection_panel.btn_disconnect.isEnabled()
    assert panel.connection_panel.selected_port() == "COM5"
    assert panel.connection_panel.selected_baudrate() == 38400

    panel.close()
