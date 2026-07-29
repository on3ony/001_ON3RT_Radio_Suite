#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Radio Panel
Version : 1.1
Description :
    Fréquence et mode mis en avant comme sur un afficheur de
    transceiver ; les données secondaires (modèle, port, bande,
    PTT, VFO, puissance, S-mètre, SWR, antenne) sont organisées en
    grille légende/valeur pour une lecture rapide.
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QFrame, QLabel

from .. import theme


class RadioPanel(QFrame):

    def __init__(self, live_service=None):
        super().__init__()

        theme.apply_panel_frame(self)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(0)

        layout.addWidget(theme.make_panel_title("📻 RADIO"))

        body = QVBoxLayout()

        body.setContentsMargins(*theme.PANEL_CONTENT_MARGINS)

        body.setSpacing(theme.PANEL_CONTENT_SPACING)

        layout.addLayout(body)

        # ------------------------------------------------
        # État de connexion (piloté par LiveService)
        # ------------------------------------------------

        self.connection = QLabel("Connexion inconnue")

        self.connection.setAlignment(Qt.AlignmentFlag.AlignCenter)

        body.addWidget(self.connection, 0, Qt.AlignmentFlag.AlignCenter)

        # ------------------------------------------------
        # Fréquence — valeur hero, comme un afficheur de transceiver
        # ------------------------------------------------

        body.addWidget(theme.make_hero_caption("FRÉQUENCE"))

        self.frequency = theme.make_hero_value()

        body.addWidget(self.frequency)

        # ------------------------------------------------
        # Mode — badge mis en valeur
        # ------------------------------------------------

        body.addWidget(theme.make_hero_caption("MODE"))

        self.mode = theme.make_accent_badge()

        body.addWidget(self.mode, 0, Qt.AlignmentFlag.AlignCenter)

        body.addSpacing(theme.SPACING_SM)

        # ------------------------------------------------
        # Données secondaires — grille légende/valeur
        # ------------------------------------------------

        grid = QGridLayout()

        grid.setHorizontalSpacing(theme.SPACING_LG)

        grid.setVerticalSpacing(theme.SPACING_SM)

        secondary_fields = [
            ("MODÈLE", "model"),
            ("PORT", "port"),
            ("VITESSE", "baudrate"),
            ("BANDE", "band"),
            ("PTT", "ptt"),
            ("VFO", "vfo"),
            ("PUISSANCE", "power"),
            ("S-MÈTRE", "smeter"),
            ("SWR", "swr"),
            ("ANTENNE", "antenna"),
        ]

        for index, (caption, attr_name) in enumerate(secondary_fields):

            widget, value_label = theme.make_info_pair(caption)

            setattr(self, attr_name, value_label)

            grid.addWidget(widget, index // 2, index % 2)

        body.addLayout(grid)

        body.addStretch()

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

        self.connection.setStyleSheet(theme.state_pill_qss(connected))

        self.model.setText(self._text_or_dash(state.get("model")))
        self.port.setText(self._text_or_dash(state.get("port")))

        baudrate = state.get("baudrate")
        self.baudrate.setText(f"{baudrate} bauds" if baudrate else "--")

        frequency = state.get("frequency")
        self.frequency.setText(
            f"{int(frequency):,} Hz".replace(",", ".") if frequency else "--"
        )

        self.band.setText(self._text_or_dash(state.get("band")))
        self.mode.setText(self._text_or_dash(state.get("mode")))

        ptt = state.get("ptt")
        self.ptt.setText("TX" if ptt else "RX")

        self.vfo.setText(self._text_or_dash(state.get("vfo")))
        self.power.setText(self._text_or_dash(state.get("power")))
        self.smeter.setText(self._text_or_dash(state.get("smeter")))
