"""
ON3RT Radio Suite
libraries/station/station_service.py

Source de vérité unique pour l'identité et les caractéristiques
permanentes de la station : indicatif, nom de l'opérateur, locator,
position, QTH, altitude, antennes déclarées, interfaces déclarées,
préférences communes.

Ce que StationService NE contient JAMAIS :
    - les paramètres de connexion CAT (port, baudrate...) : ils
      restent sous la responsabilité exclusive de RadioService
      (apps/cat_server/radio_service.py) ;
    - l'état dynamique de tout autre service (fréquence, spots DX
      Cluster, décodages WSJT-X, indices de propagation...) : chaque
      service dynamique reste seul responsable de son propre état.

StationService peut être lu par n'importe quel service ou module de
la suite, mais aucun d'eux ne doit y écrire son propre état.

Persistance : config/station.json. Ce fichier est créé vide (aucune
valeur par défaut codée en dur) : la première configuration réelle
de la station se fait depuis la page Station de la suite.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "station.json"


class StationService:
    """
    Expose directement les informations permanentes de la station en
    attributs, et via info() pour un instantané sous forme de dict.
    Aucune classe métier intermédiaire : StationService est lui-même
    la source de vérité.
    """

    def __init__(self, config_path=None):

        self._path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

        self.callsign = ""
        self.operator_name = ""
        self.locator = ""
        self.latitude = None
        self.longitude = None
        self.qth = ""
        self.altitude = None
        self.antennas = []
        self.interfaces = {}
        self.timezone = "UTC"
        self.license_class = ""

        self.load()

    # ---------------------------------------------------------
    # Persistance
    # ---------------------------------------------------------

    def load(self):
        """
        Charge config/station.json. Si le fichier est absent, vide,
        illisible, ou mal formé, la station reste non configurée
        (valeurs par défaut ci-dessus) : aucune donnée n'est
        inventée.
        """

        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return

        if not isinstance(data, dict):
            return

        self.callsign = data.get("callsign", self.callsign)
        self.operator_name = data.get("operator_name", self.operator_name)
        self.locator = data.get("locator", self.locator)
        self.latitude = data.get("latitude", self.latitude)
        self.longitude = data.get("longitude", self.longitude)
        self.qth = data.get("qth", self.qth)
        self.altitude = data.get("altitude", self.altitude)
        self.antennas = data.get("antennas", self.antennas)
        self.interfaces = data.get("interfaces", self.interfaces)
        self.timezone = data.get("timezone", self.timezone)
        self.license_class = data.get("license_class", self.license_class)

    def save(self):
        """
        Écrit l'état courant dans config/station.json, en écriture
        atomique (fichier temporaire puis remplacement).
        """

        self._path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self._path.with_suffix(".tmp")

        tmp_path.write_text(
            json.dumps(self.info(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        tmp_path.replace(self._path)

    # ---------------------------------------------------------
    # Lecture
    # ---------------------------------------------------------

    def info(self):
        """Retourne un instantané des informations de la station."""

        return {
            "callsign": self.callsign,
            "operator_name": self.operator_name,
            "locator": self.locator,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "qth": self.qth,
            "altitude": self.altitude,
            "antennas": list(self.antennas),
            "interfaces": dict(self.interfaces),
            "timezone": self.timezone,
            "license_class": self.license_class,
        }
