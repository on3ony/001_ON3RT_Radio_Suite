#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Radio Panel
=========================================================
Description :
    Repris tel quel depuis 001_ON3RT_live/panels/radio_panel.py
    (validé avec un IC-7300 réel).
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QFrame,
)


class RadioPanel(QFrame):

    def __init__(self, live_service=None):
        super().__init__()

        self.setStyleSheet("""
            QFrame{
                background:#112743;
                border:2px solid #00cfff;
                border-radius:12px;
            }

            QLabel{
                color:white;
                border:none;
            }
        """)

        layout = QVBoxLayout(self)

        # ------------------------------------------------

        titre = QLabel("📻 RADIO")

        font = QFont()
        font.setPointSize(15)
        font.setBold(True)

        titre.setFont(font)
        titre.setAlignment(Qt.AlignmentFlag.AlignCenter)

        titre.setStyleSheet("""
            color:#00dfff;
            padding:8px;
        """)

        layout.addWidget(titre)

        # ------------------------------------------------

        self.model = QLabel("--")

        self.port = QLabel("--")

        self.baudrate = QLabel("--")

        self.frequency = QLabel("--")

        self.band = QLabel("--")

        self.mode = QLabel("--")

        self.ptt = QLabel("--")

        self.power = QLabel("--")

        self.smeter = QLabel("--")

        # ------------------------------------------------
        # État de connexion (nouveau, piloté par LiveService)
        # ------------------------------------------------

        self.connection = QLabel("Connexion inconnue")

        # ------------------------------------------------
        # Champs préparés pour de futures données (non
        # alimentés pour le moment)
        # ------------------------------------------------

        self.swr = QLabel("SWR : --")

        self.antenna = QLabel("Antenne : --")

        self.vfo = QLabel("--")

        infos = [
            self.connection,
            self.model,
            self.port,
            self.baudrate,
            self.frequency,
            self.band,
            self.mode,
            self.ptt,
            self.vfo,
            self.power,
            self.smeter,
            self.swr,
            self.antenna,
        ]

        for widget in infos:

            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

            widget.setStyleSheet("""
                font-size:14pt;
                color:#9beeff;
            """)

            layout.addWidget(widget)

            if widget is self.baudrate:
                layout.addSpacing(10)

        layout.addStretch()

        # ------------------------------------------------
        # LiveService (optionnel) : si fourni, prend le relais
        # pour la mise à jour automatique depuis data/live.json
        # (alimenté par apps/cat_server/radio_service.py).
        # ------------------------------------------------

        self._live_service = live_service

        if self._live_service is not None:
            self._live_service.state_changed.connect(self.update_from_state)
            self.update_from_state(self._live_service.state())

    # --------------------------------------------------

    @staticmethod
    def _text_or_dash(value):
        if value in (None, "", "{}"):
            return "--"

        return str(value)

    # --------------------------------------------------

    def update_from_state(self, state):
        """
        Slot connecté à LiveService.state_changed. Alimente le
        panneau avec l'état réel provenant du moteur CAT (via
        data/live.json). power et smeter restent "--" tant que
        le moteur CAT ne les fournit pas (aucune valeur inventée).
        """

        if not isinstance(state, dict):
            return

        connected = bool(state.get("connected", False))

        self.connection.setText("Connecté" if connected else "Déconnecté")

        self.connection.setStyleSheet(f"""
            font-size:14pt;
            font-weight:bold;
            color:{'#00ff88' if connected else '#ff6666'};
        """)

        self.model.setText("Modèle : " + self._text_or_dash(state.get("model")))
        self.port.setText("Port : " + self._text_or_dash(state.get("port")))

        baudrate = state.get("baudrate")
        self.baudrate.setText(
            "Vitesse : " + (f"{baudrate} bauds" if baudrate else "--")
        )

        frequency = state.get("frequency")
        self.frequency.setText(
            "Fréquence : "
            + (f"{int(frequency):,} Hz".replace(",", ".") if frequency else "--")
        )

        self.band.setText("Bande : " + self._text_or_dash(state.get("band")))
        self.mode.setText("Mode : " + self._text_or_dash(state.get("mode")))

        ptt = state.get("ptt")
        self.ptt.setText("PTT : " + ("TX" if ptt else "RX"))

        self.vfo.setText("VFO : " + self._text_or_dash(state.get("vfo")))
        self.power.setText("Puissance : " + self._text_or_dash(state.get("power")))
        self.smeter.setText("S-mètre : " + self._text_or_dash(state.get("smeter")))
