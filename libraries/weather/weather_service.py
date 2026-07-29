"""
ON3RT Radio Suite
libraries/weather/weather_service.py

Service météo partagé de la suite : interroge périodiquement
Open-Meteo (open-meteo.com — aucune clé API requise, usage non
commercial) pour la position de la station.

La position (latitude/longitude) n'est JAMAIS copiée localement :
elle est lue directement dans StationService à chaque cycle de
sondage, exactement comme DXClusterService lit l'indicatif de
StationService à chaque tentative de connexion. StationService reste
l'unique source de vérité pour la position de la station.

Aucune requête n'est envoyée tant que StationService.latitude ou
StationService.longitude valent None (station non configurée) — même
principe que le garde-fou déjà appliqué à DXClusterService avec un
indicatif vide : un état honnêtement "non configuré" plutôt qu'une
requête vouée à l'échec.

Contrat de données publié (figé, voir échanges de conception) :
    received_at             str    ISO 8601 UTC, horodatage de réception
    temperature_c            float | None
    apparent_temperature_c   float | None
    humidity_pct             float | None
    pressure_hpa             float | None
    wind_speed_kmh           float | None
    wind_gusts_kmh           float | None
    wind_direction_deg       float | None
    cloud_cover_pct          float | None
    precipitation_mm         float | None
    visibility_m             float | None
    conditions               str | None   dérivé du code WMO (table fixe
                                          ci-dessous), jamais du texte libre
    sunrise                  str | None   ISO 8601 (bloc "daily")
    sunset                   str | None   ISO 8601 (bloc "daily")
    source                   str          constante "Open-Meteo", jamais déduite

Le JSON brut de la dernière requête réussie est conservé uniquement en
interne (propriété `last_raw_response`, usage débogage) — il n'est
JAMAIS inclus dans le dict publié via `weather_updated`.

Fréquence de sondage par défaut : 10 minutes (les modèles météo
sous-jacents ne se rafraîchissent pas plus vite).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QTimer, QUrl, QUrlQuery, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

DEFAULT_POLL_INTERVAL_MS = 10 * 60 * 1000  # 10 minutes

SOURCE_NAME = "Open-Meteo"

BASE_URL = "https://api.open-meteo.com/v1/forecast"

CURRENT_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "visibility",
]

DAILY_VARIABLES = ["sunrise", "sunset"]

# Table de correspondance code WMO -> libellé (français), déterministe
# et documentée : https://open-meteo.com/en/docs (weather_code).
# Dérivation fixe, jamais une interprétation d'un texte libre.
WMO_CONDITIONS = {
    0: "Ciel dégagé",
    1: "Principalement dégagé",
    2: "Partiellement nuageux",
    3: "Couvert",
    45: "Brouillard",
    48: "Brouillard givrant",
    51: "Bruine légère",
    53: "Bruine modérée",
    55: "Bruine dense",
    56: "Bruine verglaçante légère",
    57: "Bruine verglaçante dense",
    61: "Pluie légère",
    63: "Pluie modérée",
    65: "Pluie forte",
    66: "Pluie verglaçante légère",
    67: "Pluie verglaçante forte",
    71: "Neige légère",
    73: "Neige modérée",
    75: "Neige forte",
    77: "Grains de neige",
    80: "Averses légères",
    81: "Averses modérées",
    82: "Averses violentes",
    85: "Averses de neige légères",
    86: "Averses de neige fortes",
    95: "Orage",
    96: "Orage avec grêle légère",
    99: "Orage avec grêle forte",
}


class WeatherService(QObject):
    """
    Interroge périodiquement Open-Meteo pour la position lue dans
    StationService (jamais copiée localement). Émet `weather_updated`
    (dict conforme au contrat) et `connectionChanged(bool)`.
    """

    weather_updated = Signal(dict)
    connectionChanged = Signal(bool)

    def __init__(self, station_service, poll_interval_ms=DEFAULT_POLL_INTERVAL_MS, parent=None):
        super().__init__(parent)

        self._station_service = station_service

        self._connected = False
        self._last_raw_response = None

        self._manager = QNetworkAccessManager(self)
        self._reply = None

        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_ms)
        self._timer.timeout.connect(self._poll)

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def start(self):
        """Démarre le sondage périodique (sonde immédiatement, puis à intervalle régulier)."""

        if not self._timer.isActive():
            self._timer.start()

        self._poll()

    def stop(self):
        """Arrête le sondage périodique. N'annule pas une requête déjà en vol."""

        self._timer.stop()

    @property
    def connected(self):
        return self._connected

    @property
    def last_raw_response(self):
        """
        Réponse JSON brute de la dernière requête réussie, pour
        débogage uniquement — jamais publiée via `weather_updated`.
        """

        return self._last_raw_response

    # ------------------------------------------------------------------
    # Sondage
    # ------------------------------------------------------------------

    def _poll(self):
        if self._reply is not None:
            # Une requête est déjà en vol : ne pas en superposer une autre.
            return

        latitude = getattr(self._station_service, "latitude", None)
        longitude = getattr(self._station_service, "longitude", None)

        if latitude is None or longitude is None:
            # Station non configurée : aucune requête, état honnête.
            self._set_connected(False)
            return

        url = QUrl(BASE_URL)
        query = QUrlQuery()
        query.addQueryItem("latitude", str(latitude))
        query.addQueryItem("longitude", str(longitude))
        query.addQueryItem("current", ",".join(CURRENT_VARIABLES))
        query.addQueryItem("daily", ",".join(DAILY_VARIABLES))
        query.addQueryItem("timezone", "UTC")
        url.setQuery(query)

        self._reply = self._manager.get(QNetworkRequest(url))
        self._reply.finished.connect(self._on_reply_finished)

    def _on_reply_finished(self):
        reply = self._reply
        self._reply = None

        if reply is None:
            return

        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._set_connected(False)
                return

            try:
                data = json.loads(bytes(reply.readAll()).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self._set_connected(False)
                return

            if not isinstance(data, dict):
                self._set_connected(False)
                return

            self._last_raw_response = data

            self.weather_updated.emit(self._build_weather_dict(data))
            self._set_connected(True)
        finally:
            reply.deleteLater()

    def _set_connected(self, connected):
        if connected != self._connected:
            self._connected = connected
            self.connectionChanged.emit(connected)

    # ------------------------------------------------------------------
    # Construction du contrat publié
    # ------------------------------------------------------------------

    @staticmethod
    def _build_weather_dict(data):
        current = data.get("current") or {}
        daily = data.get("daily") or {}

        weather_code = current.get("weather_code")
        conditions = WMO_CONDITIONS.get(weather_code) if isinstance(weather_code, int) else None

        sunrise_list = daily.get("sunrise") or []
        sunset_list = daily.get("sunset") or []

        return {
            "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "temperature_c": current.get("temperature_2m"),
            "apparent_temperature_c": current.get("apparent_temperature"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "pressure_hpa": current.get("pressure_msl"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "wind_gusts_kmh": current.get("wind_gusts_10m"),
            "wind_direction_deg": current.get("wind_direction_10m"),
            "cloud_cover_pct": current.get("cloud_cover"),
            "precipitation_mm": current.get("precipitation"),
            "visibility_m": current.get("visibility"),
            "conditions": conditions,
            "sunrise": sunrise_list[0] if sunrise_list else None,
            "sunset": sunset_list[0] if sunset_list else None,
            "source": SOURCE_NAME,
        }
