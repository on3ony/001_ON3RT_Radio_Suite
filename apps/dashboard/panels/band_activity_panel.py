#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Band Activity Panel
=========================================================
Description :
    Affiche l'activité par bande. Ne lit jamais data/live.json
    directement : reçoit une instance de live_service.py
    (LiveService) et s'abonne à son signal state_changed.

    Version de démonstration : les valeurs affichées sont des
    valeurs de secours tant que l'état fourni par LiveService ne
    contient pas de clé "bands". Il suffira alors que
    state["bands"] contienne un dict {"20m": "...", ...} pour que
    les vraies données remplacent automatiquement les valeurs de
    démonstration (voir update_state()).

    Repris tel quel depuis 001_ON3RT_live/panels/band_activity_panel.py.
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QGridLayout,
)

# ----------------------------------------------------------------------
# Bandes affichées
# ----------------------------------------------------------------------

BANDS = [
    "160m",
    "80m",
    "40m",
    "30m",
    "20m",
    "17m",
    "15m",
    "12m",
    "10m",
    "6m",
]

# Valeur affichée tant qu'aucune donnée réelle n'est fournie par LiveService.
DEMO_VALUE = "—"


class BandActivityPanel(QWidget):
    """
    Panneau d'activité par bande, piloté par LiveService.
    """

    def __init__(self, live_service, parent=None):

        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._live_service = live_service
        self._value_labels = {}

        self.setStyleSheet("""
            BandActivityPanel{
                background:#112743;
                border:2px solid #00cfff;
                border-radius:12px;
            }

            QLabel{
                color:white;
                border:none;
            }
        """)

        self.build_ui()

        self._live_service.state_changed.connect(self.update_state)

        self.update_state(self._live_service.state())

    # -----------------------------------------------------
    # Construction de l'interface
    # -----------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        # ------------------------------------------------

        titre = QLabel("📊 ACTIVITÉ PAR BANDE")

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

        grid = QGridLayout()
        grid.setSpacing(6)

        for row, band in enumerate(BANDS):

            band_label = QLabel(band)
            band_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            band_label.setStyleSheet("""
                font-size:13pt;
                color:#9beeff;
            """)

            value_label = QLabel(DEMO_VALUE)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            value_label.setStyleSheet("""
                font-size:13pt;
                font-weight:bold;
                color:white;
            """)

            grid.addWidget(band_label, row, 0)
            grid.addWidget(value_label, row, 1)

            self._value_labels[band] = value_label

        layout.addLayout(grid)
        layout.addStretch()

    # -----------------------------------------------------
    # Mise à jour depuis LiveService
    # -----------------------------------------------------

    def update_state(self, state):
        """
        Slot connecté à LiveService.state_changed.

        Attend un dict optionnel state["bands"] de la forme
        {"20m": "<valeur>", ...}. Tant que cette clé est absente
        (ou incomplète), les bandes concernées conservent la
        valeur de démonstration DEMO_VALUE.
        """

        bands_data = state.get("bands", {}) if isinstance(state, dict) else {}

        if not isinstance(bands_data, dict):
            bands_data = {}

        for band, label in self._value_labels.items():

            value = bands_data.get(band)
            label.setText(str(value) if value not in (None, "") else DEMO_VALUE)
