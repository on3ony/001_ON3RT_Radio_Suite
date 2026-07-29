#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Band Activity Panel
Version : 1.1.0
Auteur : ON3RT
Description :
    Affiche l'activité par bande. Ne lit jamais data/live.json
    directement : reçoit une instance de services/live_service.py
    (LiveService) et s'abonne à son signal state_changed.

    Chaque bande est présentée avec un BandIndicator (theme.py),
    composant graphique réutilisable prêt à afficher un niveau
    d'activité de 0 à 100 % avec dégradé et transition animée.
    Actuellement laissé en mode démonstration (niveau à 0) : aucune
    donnée réelle n'est tracée tant que state["bands"] ne fournit
    rien. Lorsque de vraies données seront disponibles, seul
    BandIndicator devra évoluer — ce panneau n'aura qu'à lui
    transmettre le niveau via set_level().

    Version de démonstration : les valeurs affichées sont des
    valeurs de secours tant que l'état fourni par LiveService ne
    contient pas de clé "bands". Il suffira alors que
    state["bands"] contienne un dict {"20m": "...", ...} pour que
    les vraies données remplacent automatiquement les valeurs de
    démonstration (voir update_state()).
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGridLayout

from .. import theme

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

        theme.apply_panel_frame(self)

        self.build_ui()

        self._live_service.state_changed.connect(self.update_state)

        self.update_state(self._live_service.state())

    # -----------------------------------------------------
    # Construction de l'interface
    # -----------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(0)

        layout.addWidget(theme.make_panel_title("📊 ACTIVITÉ PAR BANDE"))

        body = QVBoxLayout()

        body.setContentsMargins(*theme.PANEL_CONTENT_MARGINS)

        body.setSpacing(theme.PANEL_CONTENT_SPACING)

        layout.addLayout(body)

        # ------------------------------------------------
        # Une ligne par bande : nom · BandIndicator (futur graphique) · valeur
        # ------------------------------------------------

        grid = QGridLayout()
        grid.setHorizontalSpacing(theme.SPACING_MD)
        grid.setVerticalSpacing(theme.SPACING_SM)

        for row, band in enumerate(BANDS):

            band_label = QLabel(band)
            band_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            band_label.setStyleSheet(theme.info_row_qss())

            track = theme.BandIndicator()

            value_label = QLabel(DEMO_VALUE)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_label.setStyleSheet(theme.value_text_qss())

            grid.addWidget(band_label, row, 0)
            grid.addWidget(track, row, 1)
            grid.addWidget(value_label, row, 2)

            self._value_labels[band] = value_label

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)

        body.addLayout(grid)
        body.addStretch()

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
