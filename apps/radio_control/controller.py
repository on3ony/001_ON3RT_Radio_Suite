"""
ON3RT Radio Suite
Radio Control Controller

Gestion de l'interface Radio Control.
"""

from serial.tools import list_ports


class RadioController:
    """
    Contrôleur de Radio Control.
    """

    def __init__(self, window):

        self.window = window

        self._connect_signals()

        # Remplit immédiatement la liste des ports
        self.refresh_ports()

    # ==========================================================
    # Signaux
    # ==========================================================

    def _connect_signals(self):

        panel = self.window.connection_panel

        panel.btn_refresh.clicked.connect(self.refresh_ports)

    # ==========================================================
    # Ports série
    # ==========================================================

    def refresh_ports(self):
        """
        Recherche les ports COM disponibles.
        """

        ports = []

        for port in list_ports.comports():
            ports.append(port.device)

        ports.sort()

        self.window.connection_panel.set_ports(ports)

        self.window.statusBar().showMessage(
            f"{len(ports)} port(s) détecté(s)"
        )