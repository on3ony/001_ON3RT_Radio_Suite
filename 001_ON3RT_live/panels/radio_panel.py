#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Radio Panel
Version : 1.0
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

    def __init__(self):
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

        self.model = QLabel("IC-7300")

        self.frequency = QLabel("14.074.000 MHz")

        self.band = QLabel("20 mètres")

        self.mode = QLabel("FT8")

        self.ptt = QLabel("RX")

        self.power = QLabel("0 W")

        self.smeter = QLabel("S0")

        infos = [
            self.model,
            self.frequency,
            self.band,
            self.mode,
            self.ptt,
            self.power,
            self.smeter
        ]

        for widget in infos:

            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

            widget.setStyleSheet("""
                font-size:14pt;
                color:#9beeff;
            """)

            layout.addWidget(widget)

        layout.addStretch()

    # --------------------------------------------------

    def set_radio_data(
        self,
        model,
        frequency,
        band,
        mode,
        ptt,
        power,
        smeter
    ):

        self.model.setText(model)
        self.frequency.setText(frequency)
        self.band.setText(band)
        self.mode.setText(mode)
        self.ptt.setText(ptt)
        self.power.setText(power)
        self.smeter.setText(smeter)