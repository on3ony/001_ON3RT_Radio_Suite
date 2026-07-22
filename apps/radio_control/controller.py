"""
ON3RT Radio Suite
Radio Control Controller
"""

from serial.tools import list_ports

from PySide6.QtCore import QTimer

from libraries.cat.cat_controller import CATController


class RadioController:
    """
    Contrôleur de Radio Control.
    """

    def __init__(self, window):

        self.window = window

        self.cat = None

        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_radio)

        self._connect_signals()

        self.refresh_ports()

    # ==========================================================
    # Signaux
    # ==========================================================

    def _connect_signals(self):

        panel = self.window.connection_panel

        panel.btn_refresh.clicked.connect(self.refresh_ports)
        panel.btn_connect.clicked.connect(self.connect_radio)
        panel.btn_disconnect.clicked.connect(self.disconnect_radio)

    # ==========================================================
    # Ports série
    # ==========================================================

    def refresh_ports(self):

        ports = []

        for port in list_ports.comports():
            ports.append(port.device)

        ports.sort()

        self.window.connection_panel.set_ports(ports)

        self.window.statusBar().showMessage(
            f"{len(ports)} port(s) détecté(s)"
        )

    # ==========================================================
    # Connexion
    # ==========================================================

    def connect_radio(self):

        panel = self.window.connection_panel

        port = panel.selected_port()
        baud = panel.selected_baudrate()

        self.cat = CATController(
            port=port,
            baudrate=baud
        )

        if self.cat.connect():

            panel.set_connected(True)
            self.window.radio_panel.set_connected(True)

            self.timer.start()

            self.window.statusBar().showMessage(
                f"Connecté à {port}"
            )

        else:

            self.window.statusBar().showMessage(
                "Connexion impossible"
            )

    def disconnect_radio(self):

        self.timer.stop()

        if self.cat:

            self.cat.disconnect()

        self.window.connection_panel.set_connected(False)
        self.window.radio_panel.set_connected(False)

        self.window.statusBar().showMessage(
            "Déconnecté"
        )

    # ==========================================================
    # Rafraîchissement
    # ==========================================================

    def update_radio(self):

        if not self.cat:
            return

        try:

            frequency = self.cat.read_frequency()

            mhz = frequency / 1000000.0

            self.window.radio_panel.set_frequency(
                f"{mhz:,.6f} MHz".replace(",", " ")
            )

        except Exception:
            pass

        try:

            mode = self.cat.read_mode()

            self.window.radio_panel.set_mode(str(mode))

        except Exception:
            pass

        try:

            vfo = self.cat.read_vfo()

            if isinstance(vfo, dict):

                if "vfo" in vfo:
                    value = vfo["vfo"]
                elif "name" in vfo:
                    value = vfo["name"]
                else:
                    value = str(vfo)

            else:
                value = str(vfo)

            self.window.radio_panel.set_vfo(value)

        except Exception:
            pass

        try:

            ptt = self.cat.read_ptt()

            if isinstance(ptt, dict):

                if "ptt" in ptt:
                    value = bool(ptt["ptt"])
                elif "state" in ptt:
                    value = bool(ptt["state"])
                else:
                    value = False

            else:
                value = bool(ptt)

            self.window.radio_panel.set_ptt(value)

        except Exception:
            pass