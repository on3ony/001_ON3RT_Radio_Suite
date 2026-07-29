"""
ON3RT Radio Suite
Radio Control Controller
"""

from serial.tools import list_ports

from apps.cat_server.radio_service import RadioService


class RadioController:
    """
    Contrôleur de Radio Control.
    """

    def __init__(self, window, radio_service=None):

        self.window = window
        self.service = None

        self._connect_signals()
        self.refresh_ports()

        # RadioService partagé (apps.cat_server.radio_service), démarré et
        # connecté par Application : Radio Control ne se connecte plus
        # jamais lui-même en créant une instance séparée s'il en reçoit
        # une déjà existante. Si aucun service n'est fourni (lancement
        # isolé via apps/radio_control/main.py), le comportement autonome
        # d'origine (créer sa propre connexion depuis les boutons) reste
        # disponible.
        if radio_service is not None:
            self._attach_service(radio_service)

    def _connect_signals(self):

        panel = self.window.connection_panel

        panel.btn_refresh.clicked.connect(self.refresh_ports)
        panel.btn_connect.clicked.connect(self.connect_radio)
        panel.btn_disconnect.clicked.connect(self.disconnect_radio)

    def refresh_ports(self):

        ports = sorted([p.device for p in list_ports.comports()])

        self.window.connection_panel.set_ports(ports)
        self.window.statusBar().showMessage(
            f"{len(ports)} port(s) détecté(s)"
        )

    def connect_radio(self):

        panel = self.window.connection_panel
        port = panel.selected_port()
        baudrate = panel.selected_baudrate()

        if self.service is None:
            self._attach_service(RadioService(port=port, baudrate=baudrate))
        else:
            self.service.reconfigure(port, baudrate)

        self.service.connect()

    def disconnect_radio(self):

        if self.service:
            self.service.disconnect()

    # ------------------------------------------------------------------
    # Service CAT partagé (démarré en arrière-plan par Application)
    # ------------------------------------------------------------------

    def _attach_service(self, service: RadioService) -> None:
        """
        Se branche sur un RadioService déjà existant : évite d'ouvrir une
        seconde fois le même port série, et reflète immédiatement son état
        courant.
        """

        self.service = service

        service.updated.connect(self.update_radio)
        service.connectionChanged.connect(self.on_connection_changed)
        service.error.connect(self.window.statusBar().showMessage)

        self.on_connection_changed(service.connected)

        if service.connected:
            panel = self.window.connection_panel
            panel.set_selected_port(service.port)
            panel.set_selected_baudrate(service.baudrate)

    def on_connection_changed(self, connected: bool):

        self.window.connection_panel.set_connected(connected)
        self.window.radio_panel.set_connected(connected)

        self.window.statusBar().showMessage(
            "Connecté" if connected else "Déconnecté"
        )

        if connected:
            self.update_radio()

    def update_radio(self):

        if not self.service:
            return

        info = self.service.info()

        f = info.get("frequency")
        if f:
            self.window.radio_panel.set_frequency(
                f"{f/1000000:.6f} MHz"
            )

        self.window.radio_panel.set_mode(info.get("mode", "---"))
        self.window.radio_panel.set_vfo(str(info.get("vfo", "A")))
        self.window.radio_panel.set_ptt(bool(info.get("ptt", False)))
