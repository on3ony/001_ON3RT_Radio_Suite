from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QGridLayout,
)

from libraries.cat.cat_controller import CATController


class CATServerWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ON3RT Radio Suite - CAT Server")
        self.resize(700, 450)

        self.controller = CATController(port="COM3", baudrate=19200)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        titre = QLabel("CAT SERVER")
        titre.setAlignment(Qt.AlignCenter)
        titre.setStyleSheet("font-size:24px;font-weight:bold;")

        layout.addWidget(titre)

        grille = QGridLayout()

        self.lbl_port = QLabel("Port : COM3")
        self.lbl_status = QLabel("Etat : Déconnecté")
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

        layout.addWidget(self.btn_connect)
        layout.addWidget(self.btn_disconnect)

        self.statusBar().showMessage("CAT Server prêt")

        self.btn_connect.clicked.connect(self.connect_radio)
        self.btn_disconnect.clicked.connect(self.disconnect_radio)

        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.refresh)

    def connect_radio(self):
        try:
            if self.controller.connect():
                self.lbl_status.setText("Etat : Connecté")
                self.statusBar().showMessage("IC-7300 connecté")
                self.timer.start()
            else:
                self.lbl_status.setText("Etat : Erreur de connexion")
        except Exception as e:
            self.lbl_status.setText("Etat : Erreur")
            self.statusBar().showMessage(str(e))

    def disconnect_radio(self):
        self.timer.stop()

        try:
            self.controller.disconnect()
        except Exception:
            pass

        self.lbl_status.setText("Etat : Déconnecté")
        self.lbl_freq.setText("Fréquence : -----")
        self.lbl_mode.setText("Mode : -----")
        self.lbl_ptt.setText("PTT : OFF")

        self.statusBar().showMessage("Déconnecté")

    def refresh(self):
        if not self.controller.connected:
            return

        try:
            freq = self.controller.read_frequency()
            mode = self.controller.read_mode()
            ptt = self.controller.read_ptt()

            if freq:
                self.lbl_freq.setText(f"Fréquence : {freq:,} Hz".replace(",", "."))

            self.lbl_mode.setText(f"Mode : {mode}")

            if isinstance(ptt, dict):
                state = ptt.get("ptt", False)
            else:
                state = bool(ptt)

            self.lbl_ptt.setText("PTT : ON" if state else "PTT : OFF")

        except Exception as e:
            self.statusBar().showMessage(str(e))