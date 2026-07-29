#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Weather Panel
=========================================================
Description :
    Affiche la météo réelle de la station (WeatherService, via
    LiveService) : température, conditions, vent (vitesse et
    rafales), lever et coucher du soleil. N'accède jamais à
    WeatherService directement : reçoit une instance de LiveService
    et lit exclusivement les clés "weather_connected" / "weather_data"
    de l'état partagé (alimentées par
    data_sources/weather_source.py — WeatherLiveDataSource).

    Panneau V1 strictement descriptif : aucune interprétation, aucun
    seuil, aucun indicateur calculé — les symboles ☀/🌙 sont de
    simples étiquettes statiques, jamais un état jour/nuit déduit de
    l'heure courante. Aucune interaction utilisateur.
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QFrame


class WeatherPanel(QFrame):

    def __init__(self, live_service, parent=None):
        super().__init__(parent)

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

        titre = QLabel("🌤 MÉTÉO")

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

        self.connection = QLabel("Connexion inconnue")
        self.connection.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection.setStyleSheet("""
            font-size:10pt;
            color:#9beeff;
        """)
        layout.addWidget(self.connection)

        self._rows_container = QVBoxLayout()
        layout.addLayout(self._rows_container)
        layout.addStretch()

        self._row_labels = []

        # ------------------------------------------------
        # LiveService : seule source d'information de ce panneau.
        # ------------------------------------------------

        self._live_service = live_service
        self._live_service.state_changed.connect(self.update_state)
        self.update_state(self._live_service.state())

    # -----------------------------------------------------
    # Mise à jour depuis LiveService
    # -----------------------------------------------------

    def update_state(self, state):
        """
        Slot connecté à LiveService.state_changed. Lit uniquement
        "weather_connected" et "weather_data" ; toute autre forme se
        traduit par un état déconnecté et un message explicite,
        jamais par une donnée inventée.
        """

        connected = bool(state.get("weather_connected", False)) if isinstance(state, dict) else False
        weather = state.get("weather_data") if isinstance(state, dict) else None

        self.connection.setText("Connecté" if connected else "Déconnecté")
        self.connection.setStyleSheet(f"""
            font-size:10pt;
            font-weight:bold;
            color:{'#00ff88' if connected else '#ffb454'};
        """)

        self._render(weather if isinstance(weather, dict) else None)

    def _render(self, weather):

        while self._row_labels:
            label = self._row_labels.pop()
            self._rows_container.removeWidget(label)
            label.deleteLater()

        if weather is None:
            empty = QLabel("Météo indisponible.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("""
                font-size:13pt;
                color:#9beeff;
            """)
            self._rows_container.addWidget(empty)
            self._row_labels.append(empty)
            return

        for text in (
            self._format_temperature_line(weather),
            self._format_wind_line(weather),
            self._format_sun_line(weather),
        ):
            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                font-size:12pt;
                color:#9beeff;
            """)

            self._rows_container.addWidget(label)
            self._row_labels.append(label)

    # -----------------------------------------------------
    # Mise en forme des lignes (affichage brut, aucune interprétation)
    # -----------------------------------------------------

    @staticmethod
    def _format_temperature_line(weather):
        temperature = weather.get("temperature_c")
        conditions = weather.get("conditions")

        temperature_text = f"{temperature:.1f}°C" if isinstance(temperature, (int, float)) else "--"
        conditions_text = conditions if conditions else "--"

        return f"{temperature_text} · {conditions_text}"

    @staticmethod
    def _format_wind_line(weather):
        wind_speed = weather.get("wind_speed_kmh")
        wind_gusts = weather.get("wind_gusts_kmh")

        speed_text = f"{wind_speed:.0f} km/h" if isinstance(wind_speed, (int, float)) else "--"
        gusts_text = f"{wind_gusts:.0f} km/h" if isinstance(wind_gusts, (int, float)) else "--"

        return f"Vent : {speed_text} (rafales {gusts_text})"

    @staticmethod
    def _format_sun_line(weather):
        sunrise = WeatherPanel._format_time(weather.get("sunrise"))
        sunset = WeatherPanel._format_time(weather.get("sunset"))

        return f"☀ {sunrise}   🌙 {sunset}"

    @staticmethod
    def _format_time(value):
        """Extrait "HH:MM" d'un horodatage ISO 8601 ("...T HH:MM"), sans autre calcul."""

        if not isinstance(value, str) or "T" not in value:
            return "--"

        return value.split("T", 1)[1][:5]
