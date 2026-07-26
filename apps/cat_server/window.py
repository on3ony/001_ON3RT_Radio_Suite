from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QGridLayout,
)

from apps.cat_server.radio_service import RadioService


class CATServerWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ON3RT Radio Suite - CAT Server")
        self.resize(700, 450)

        self.service = RadioService(port="COM3", baudrate=19200)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        titre = QLabel("CAT SERVER")
        titre.setAlignment(Qt.AlignCenter)
        titre.setStyleSheet("font-size:24px;font-weight:bold;")
        layout.addWidget(titre)

        grille = QGridLayout()

        self.lbl_port = QLabel(f"Port : {self.service.status.port}")
        self.lbl_status = QLabel("État : Déconnecté")
        self.lbl_freq = QLabel("Fréquence : -----")
        self.lbl_mode = QLabel("Mode : -----")
        self.lbl_ptt = QLabel("PTT : OFF")

        grille.addWidget(self.lbl_port, 0, 0)
        grille.addWidget(self.lbl_status, 1, 0)
        grille.addWidget(self.lbl_freq, 2, 0)
        grille.addWidget(self.lbl_mode, 3, 0)
        grille.addWidget(self.lbl_ptt, 4, 0)

        layout.addLayout(grille)

        self.btn_connect = QPushButton("Connexion IC-7300")
        self.btn_disconnect = QPushButton("Déconnexion")
        self.btn_disconnect.setEnabled(False)

        layout.addWidget(self.btn_connect)
        layout.addWidget(self.btn_disconnect)

        self.statusBar().showMessage("CAT Server prêt")

        self.btn_connect.clicked.connect(self.connect_radio)
        self.btn_disconnect.clicked.connect(self.disconnect_radio)

        self.service.updated.connect(self.refresh)
        self.service.connectionChanged.connect(self.on_connection_changed)
        self.service.error.connect(self.on_error)

    def connect_radio(self):
        self.service.connect()

    def disconnect_radio(self):
        self.service.disconnect()

    def on_connection_changed(self, connected: bool):
        self.lbl_status.setText("État : Connecté" if connected else "État : Déconnecté")
        self.btn_connect.setEnabled(not connected)
        self.btn_disconnect.setEnabled(connected)
        self.statusBar().showMessage(
            "IC-7300 connecté" if connected else "Déconnecté"
        )
        if connected:
            self.refresh()
        else:
            self.lbl_freq.setText("Fréquence : -----")
            self.lbl_mode.setText("Mode : -----")
            self.lbl_ptt.setText("PTT : OFF")

    def on_error(self, message: str):
        self.statusBar().showMessage(message)

    def refresh(self):
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
