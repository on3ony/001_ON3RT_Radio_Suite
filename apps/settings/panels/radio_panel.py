"""
ON3RT Radio Suite
apps/settings/panels/radio_panel.py

Panneau "Radio" de l'écran Settings — se limite aux deux seuls
paramètres radio réellement actifs aujourd'hui : Port COM et Vitesse
CAT. Modèle, adresse CI-V, polling et timeout ne sont volontairement
pas exposés ici : rien dans la chaîne CAT (RadioService/CATController/
CATEngine) ne les rend configurables pour l'instant.

Réutilise ConnectionPanel (apps/radio_control/panels/connection_panel.py)
tel quel — le même widget déjà utilisé par CATServerWindow
(apps/cat_server/window.py) — plutôt que de reconstruire une seconde
paire de listes déroulantes Port/Baudrate. Persiste le port et la
vitesse via la même clé QSettings("ON3RT","CATServer") que
CATServerWindow : pas une seconde source de vérité, le même
mécanisme, la même logique de restauration/connexion.

RadioService reste injecté (jamais créé ici), comme dans tous les
autres modules de la suite.
"""

from __future__ import annotations

from serial.tools import list_ports

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QVBoxLayout, QWidget

from apps.radio_control.panels.connection_panel import ConnectionPanel

DEFAULT_BAUDRATE = 19200


class RadioPanel(QWidget):

    def __init__(self, radio_service=None, parent=None):
        super().__init__(parent)

        self.radio_service = radio_service
        self.settings = QSettings("ON3RT", "CATServer")

        self._build_ui()
        self._connect_signals()

        self._refresh_ports()

        if self.radio_service is not None:
            self.radio_service.connectionChanged.connect(self._on_connection_changed)

        self._on_connection_changed(
            self.radio_service.connected if self.radio_service is not None else False
        )

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.connection_panel = ConnectionPanel()

        layout.addWidget(self.connection_panel)
        layout.addStretch(1)

    def _connect_signals(self):
        self.connection_panel.btn_refresh.clicked.connect(self._refresh_ports)
        self.connection_panel.btn_connect.clicked.connect(self._on_connect_clicked)
        self.connection_panel.btn_disconnect.clicked.connect(self._on_disconnect_clicked)

    # ------------------------------------------------------------------
    # Ports / dernières valeurs utilisées (même mécanisme que CATServerWindow)
    # ------------------------------------------------------------------

    def _refresh_ports(self):
        ports = sorted(p.device for p in list_ports.comports())
        self.connection_panel.set_ports(ports)

        last_port = self.settings.value("last_port", "")
        last_baudrate = self.settings.value("last_baudrate", DEFAULT_BAUDRATE, type=int)

        if last_port:
            self.connection_panel.set_selected_port(last_port)

        self.connection_panel.set_selected_baudrate(last_baudrate)

    # ------------------------------------------------------------------
    # Connexion / déconnexion (RadioService partagé, jamais recréé ici)
    # ------------------------------------------------------------------

    def _on_connect_clicked(self):
        if self.radio_service is None:
            return

        port = self.connection_panel.selected_port()
        if not port:
            return

        baudrate = self.connection_panel.selected_baudrate()

        self.radio_service.reconfigure(port, baudrate)

        if self.radio_service.connect():
            self.settings.setValue("last_port", port)
            self.settings.setValue("last_baudrate", baudrate)

    def _on_disconnect_clicked(self):
        if self.radio_service is not None:
            self.radio_service.disconnect()

    def _on_connection_changed(self, connected: bool):
        self.connection_panel.set_connected(connected)
        self.connection_panel.set_model(
            self.radio_service.model if (connected and self.radio_service is not None) else None
        )

        if connected and self.radio_service is not None:
            self.connection_panel.set_selected_port(self.radio_service.port)
            self.connection_panel.set_selected_baudrate(self.radio_service.baudrate)
