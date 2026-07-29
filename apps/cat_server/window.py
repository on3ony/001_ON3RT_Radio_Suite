from __future__ import annotations

from serial.tools import list_ports

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from apps.cat_server.radio_service import RadioService
from apps.radio_control.panels.connection_panel import ConnectionPanel

# ----------------------------------------------------------------------
# Dernier port / baudrate utilisés : mémorisés entre deux lancements
# via QSettings (HKEY_CURRENT_USER sous Windows).
# ----------------------------------------------------------------------

DEFAULT_BAUDRATE = 19200


class CATServerWindow(QMainWindow):

    def __init__(self, service: RadioService | None = None):
        super().__init__()

        self.setWindowTitle("ON3RT Radio Suite - CAT Server")
        self.resize(700, 480)

        self.settings = QSettings("ON3RT", "CATServer")

        self.service = None

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        titre = QLabel("CAT SERVER")
        titre.setAlignment(Qt.AlignCenter)
        titre.setStyleSheet("font-size:24px;font-weight:bold;")
        layout.addWidget(titre)

        self.connection_panel = ConnectionPanel()
        layout.addWidget(self.connection_panel)

        self.lbl_freq = QLabel("Fréquence : -----")
        self.lbl_mode = QLabel("Mode : -----")
        self.lbl_ptt = QLabel("PTT : OFF")

        for lbl in (self.lbl_freq, self.lbl_mode, self.lbl_ptt):
            lbl.setStyleSheet("font-size:14px;")
            layout.addWidget(lbl)

        layout.addStretch()

        self.statusBar().showMessage("CAT Server prêt")

        self.connection_panel.btn_refresh.clicked.connect(self.refresh_ports)
        self.connection_panel.btn_connect.clicked.connect(self.connect_radio)
        self.connection_panel.btn_disconnect.clicked.connect(self.disconnect_radio)

        self.refresh_ports()

        if service is not None:
            self._attach_service(service)

    # ------------------------------------------------------------------
    # Service CAT partagé (démarré en arrière-plan par Application)
    # ------------------------------------------------------------------

    def _attach_service(self, service: "RadioService") -> None:
        """
        Se branche sur un RadioService déjà existant (celui démarré en
        arrière-plan au lancement de la suite, ou un nouveau créé depuis
        cette fenêtre) : évite d'ouvrir une seconde fois le même port
        série, et reflète immédiatement son état courant.
        """

        self.service = service

        service.updated.connect(self.refresh)
        service.connectionChanged.connect(self.on_connection_changed)
        service.error.connect(self.on_error)

        self.on_connection_changed(service.connected)

        if service.connected:
            self.connection_panel.set_selected_port(service.port)
            self.connection_panel.set_selected_baudrate(service.baudrate)

    # ------------------------------------------------------------------
    # Détection des ports / restauration des dernières valeurs utilisées
    # ------------------------------------------------------------------

    def refresh_ports(self):

        ports = sorted(p.device for p in list_ports.comports())

        self.connection_panel.set_ports(ports)

        last_port = self.settings.value("last_port", "")
        last_baudrate = self.settings.value(
            "last_baudrate", DEFAULT_BAUDRATE, type=int
        )

        if last_port:
            self.connection_panel.set_selected_port(last_port)

        self.connection_panel.set_selected_baudrate(last_baudrate)

        self.statusBar().showMessage(f"{len(ports)} port(s) détecté(s)")

    # ------------------------------------------------------------------
    # Connexion / déconnexion
    # ------------------------------------------------------------------

    def connect_radio(self):

        port = self.connection_panel.selected_port()

        if not port:
            self.statusBar().showMessage("Aucun port COM sélectionné")
            return

        baudrate = self.connection_panel.selected_baudrate()

        if self.service is None:
            self._attach_service(RadioService(port=port, baudrate=baudrate))
        else:
            self.service.reconfigure(port, baudrate)

        ok = self.service.connect()

        if ok:
            self.settings.setValue("last_port", port)
            self.settings.setValue("last_baudrate", baudrate)
        else:
            if not self.service.status.last_error:
                self.statusBar().showMessage(f"Connexion impossible sur {port}")

    def disconnect_radio(self):

        if self.service:
            self.service.disconnect()

    def on_connection_changed(self, connected: bool):

        self.connection_panel.set_connected(connected)

        self.connection_panel.set_model(
            self.service.model if (connected and self.service) else None
        )

        self.statusBar().showMessage(
            "Connecté" if connected else "Déconnecté"
        )

        if connected:
            self.refresh()
        else:
            self.lbl_freq.setText("Fréquence : -----")
            self.lbl_mode.setText("Mode : -----")
            self.lbl_ptt.setText("PTT : OFF")

    def on_error(self, message: str):
        self.statusBar().showMessage(message)

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------

    def refresh(self):

        if not self.service:
            return

        info = self.service.info()

        freq = info.get("frequency")
        if freq is not None:
            self.lbl_freq.setText(f"Fréquence : {freq:,} Hz".replace(",", "."))

        mode = info.get("mode")
        if mode:
            self.lbl_mode.setText(f"Mode : {mode}")

        self.lbl_ptt.setText(
            "PTT : ON" if info.get("ptt", False) else "PTT : OFF"
        )
