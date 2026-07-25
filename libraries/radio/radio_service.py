"""
libraries/radio/radio_service.py
-------------------------------------------------
ON3RT Radio Suite V3

Service radio central.

Toutes les applications utilisent cette classe.

- Contest
- Logbook
- CAT
- Scanner
- DX Cluster
- Propagation

COM20 uniquement.
"""

from typing import Optional

from libraries.radio.radio_manager import RadioManager


class RadioService:
    """Service radio partagé par toute la Radio Suite."""

    def __init__(self, port: Optional[str] = None, baudrate: int = 19200):

        if port is None:
            self._radio = RadioManager()
        else:
            self._radio = RadioManager(port, baudrate)

    # ---------------------------------------------------------
    # Connexion
    # ---------------------------------------------------------

    def connect(self) -> bool:
        """Connexion CAT."""
        try:
            return self._radio.connect()
        except Exception:
            return False

    def disconnect(self):
        """Déconnexion CAT."""
        try:
            self._radio.disconnect()
        except Exception:
            pass

    def is_connected(self) -> bool:
        """Etat de la connexion."""
        return self._radio.connected

    # ---------------------------------------------------------
    # Lecture
    # ---------------------------------------------------------

    def get_frequency(self):
        """Fréquence actuelle."""
        return self._radio.frequency

    def get_mode(self):
        """Mode actuel."""
        return self._radio.mode

    def get_band(self):
        """Bande actuelle."""
        return self._radio.band

    # ---------------------------------------------------------
    # UTC
    # ---------------------------------------------------------

    def get_utc_date(self):
        return self._radio.utc_date

    def get_utc_time(self):
        return self._radio.utc_time

    def get_adif_date(self):
        return self._radio.adif_date

    def get_adif_time(self):
        return self._radio.adif_time

    # ---------------------------------------------------------
    # Informations
    # ---------------------------------------------------------

    def info(self):

        return {
            "connected": self.is_connected(),
            "frequency": self.get_frequency(),
            "band": self.get_band(),
            "mode": self.get_mode(),
            "utc_date": self.get_utc_date(),
            "utc_time": self.get_utc_time(),
        }