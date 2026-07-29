#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Weather Panel
Version : 1.1.0
Auteur : ON3RT
Description :
    Affiche les conditions météo locales. Données temporaires
    (démonstration) en attendant le branchement à une véritable
    source météo. Température mise en avant comme valeur hero,
    sous une icône météo ; les données secondaires sont organisées
    en grille légende/valeur.
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QFrame

from .. import theme

# Données de démonstration : à remplacer par un vrai service météo.
MOCK_DATA = {
    "temperature": "18°C",
    "conditions": "Ciel dégagé",
    "wind": "12 km/h NO",
    "humidity": "64 %",
    "pressure": "1015 hPa",
    "sunrise": "06:12",
    "sunset": "21:47",
}


class WeatherPanel(QFrame):

    def __init__(self, weather_service=None, parent=None):
        super().__init__(parent)

        theme.apply_panel_frame(self)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(0)

        layout.addWidget(theme.make_panel_title("🌤 MÉTÉO"))

        body = QVBoxLayout()

        body.setContentsMargins(*theme.PANEL_CONTENT_MARGINS)

        body.setSpacing(theme.PANEL_CONTENT_SPACING)

        layout.addLayout(body)

        # ------------------------------------------------
        # Icône + température — valeur hero
        # ------------------------------------------------

        body.addWidget(theme.make_icon_label("🌤"))

        body.addWidget(theme.make_hero_caption("TEMPÉRATURE"))

        self.temperature = theme.make_hero_value()

        body.addWidget(self.temperature)

        body.addSpacing(theme.SPACING_SM)

        # ------------------------------------------------
        # Données secondaires — grille légende/valeur
        # ------------------------------------------------

        grid = QGridLayout()

        grid.setHorizontalSpacing(theme.SPACING_LG)

        grid.setVerticalSpacing(theme.SPACING_SM)

        secondary_fields = [
            ("CONDITIONS", "conditions"),
            ("VENT", "wind"),
            ("HUMIDITÉ", "humidity"),
            ("PRESSION", "pressure"),
            ("LEVER", "sunrise"),
            ("COUCHER", "sunset"),
        ]

        for index, (caption, attr_name) in enumerate(secondary_fields):

            widget, value_label = theme.make_info_pair(caption)

            setattr(self, attr_name, value_label)

            grid.addWidget(widget, index // 2, index % 2)

        body.addLayout(grid)

        body.addStretch()

        caption = theme.make_caption_label("Données de démonstration — à connecter")

        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)

        body.addWidget(caption)

        self._weather_service = weather_service

        self.refresh(MOCK_DATA)

    # --------------------------------------------------

    def refresh(self, data):
        """
        Met à jour l'affichage à partir d'un dict de données météo.
        Utilisable dès qu'un vrai service météo sera branché.
        """

        self.temperature.setText(str(data.get("temperature", "--")))
        self.conditions.setText(str(data.get("conditions", "--")))
        self.wind.setText(str(data.get("wind", "--")))
        self.humidity.setText(str(data.get("humidity", "--")))
        self.pressure.setText(str(data.get("pressure", "--")))
        self.sunrise.setText(str(data.get("sunrise", "--")))
        self.sunset.setText(str(data.get("sunset", "--")))
