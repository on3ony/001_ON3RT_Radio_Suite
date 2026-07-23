"""
radio_manager.py
----------------------------------------
ON3RT Radio Suite

Gestionnaire central de la Radio Suite.

Centralise :
    - CAT Controller
    - Band Manager
    - Mode Manager
    - UTC Manager

Auteur : ON3RT
"""

from typing import Optional

from libraries.cat.cat_controller import CATController
from libraries.radio.band_manager import BandManager
from libraries.radio.mode_manager import ModeManager
from libraries.radio.utc_manager import UTCManager


class RadioManager:
    """Gestionnaire principal de la radio."""

    def __init__(self, port: Optional[str] = None, baudrate: int = 19200):

        self.cat = CATController(port, baudrate)

        self.band_manager = BandManager()
        self.mode_manager = ModeManager()
        self.utc_manager = UTCManager()

    # ---------------------------------------------------------
    # CAT
    # ---------------------------------------------------------

    def connect(self):
        """Connexion CAT."""
        return self.cat.connect()

    def disconnect(self):
        """Déconnexion CAT."""
        return self.cat.disconnect()

    @property
    def connected(self) -> bool:
        return self.cat.connected

    # ---------------------------------------------------------
    # Lecture Radio
    # ---------------------------------------------------------

    @property
    def frequency(self) -> Optional[int]:

        try:
            return self.cat.read_frequency()
        except Exception:
            return None

    @property
    def mode(self) -> Optional[str]:

        try:
            mode = self.cat.read_mode()
            return self.mode_manager.normalize(mode)
        except Exception:
            return None

    @property
    def band(self) -> Optional[str]:

        freq = self.frequency

        if freq is None:
            return None

        return self.band_manager.get_band(freq)

    # ---------------------------------------------------------
    # UTC
    # ---------------------------------------------------------

    @property
    def utc_date(self):

        return self.utc_manager.date()

    @property
    def utc_time(self):

        return self.utc_manager.time()

    @property
    def adif_date(self):

        return self.utc_manager.adif_date()

    @property
    def adif_time(self):

        return self.utc_manager.adif_time()

    # ---------------------------------------------------------
    # Informations
    # ---------------------------------------------------------

    def info(self):

        return {
            "connected": self.connected,
            "frequency": self.frequency,
            "band": self.band,
            "mode": self.mode,
            "utc_date": self.utc_date,
            "utc_time": self.utc_time,
        }