"""
ON3RT Radio Suite
Radio Control - Connection Panel
"""

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
)


class ConnectionPanel(QGroupBox):
    """
    Panneau de connexion CAT.
    """

    def __init__(self):
        super().__init__("Connexion")

        self._build_ui()

    def _build_ui(self):

        layout = QGridLayout(self)
        layout.setHorizontalSpacing(15)
        layout.setVerticalSpacing(10)

        # ---------------------------------------------------------
        # Port COM
        # ---------------------------------------------------------

        layout.addWidget(QLabel("Port COM"), 0, 0)

        self.cmb_port = QComboBox()
        self.cmb_port.setMinimumWidth(150)

        layout.addWidget(self.cmb_port, 0, 1)

        # ---------------------------------------------------------
        # Baudrate
        # ---------------------------------------------------------

        layout.addWidget(QLabel("Baudrate"), 0, 2)

        self.cmb_baud = QComboBox()

        self.cmb_baud.addItems([
            "4800",
            "9600",
            "19200",
            "38400",
            "57600",
            "115200",
        ])

        self.cmb_baud.setCurrentText("19200")

        layout.addWidget(self.cmb_baud, 0, 3)

        # ---------------------------------------------------------
        # Boutons
        # ---------------------------------------------------------

        self.btn_connect = QPushButton("Connexion")
        self.btn_disconnect = QPushButton("Déconnexion")
        self.btn_refresh = QPushButton("Actualiser")

        self.btn_disconnect.setEnabled(False)

        layout.addWidget(self.btn_connect, 1, 0, 1, 2)
        layout.addWidget(self.btn_disconnect, 1, 2)
        layout.addWidget(self.btn_refresh, 1, 3)

    # ==========================================================
    # Méthodes publiques
    # ==========================================================

    def set_ports(self, ports):
        """
        Met à jour la liste des ports COM.
        """

        self.cmb_port.clear()

        for port in ports:
            self.cmb_port.addItem(port)

    def selected_port(self):
        """
        Retourne le port sélectionné.
        """

        return self.cmb_port.currentText()

    def selected_baudrate(self):
        """
        Retourne le baudrate sélectionné.
        """

        return int(self.cmb_baud.currentText())

    def set_connected(self, connected: bool):
        """
        Met à jour l'état des boutons.
        """

        self.btn_connect.setEnabled(not connected)
        self.btn_disconnect.setEnabled(connected)
        self.cmb_port.setEnabled(not connected)
        self.cmb_baud.setEnabled(not connected)