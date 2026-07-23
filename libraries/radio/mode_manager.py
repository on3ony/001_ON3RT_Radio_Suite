"""
mode_manager.py
----------------------------------------
ON3RT Radio Suite

Gestionnaire des modes radio.

Normalise les modes CAT provenant des différents
émetteurs (ICOM, Yaesu, Kenwood, etc.).
"""

from typing import Optional


class ModeManager:
    """Gestionnaire des modes radio."""

    MODES = {
        # Phone
        "USB": "USB",
        "LSB": "LSB",
        "AM": "AM",
        "FM": "FM",
        "NFM": "FM",
        "WFM": "FM",

        # CW
        "CW": "CW",
        "CW-R": "CW",
        "CWR": "CW",

        # Digital générique
        "DATA": "DATA",
        "USB-D": "DATA",
        "LSB-D": "DATA",
        "DIGI": "DATA",
        "DIG": "DATA",

        # RTTY
        "RTTY": "RTTY",
        "RTTY-R": "RTTY",

        # Modes numériques
        "FT8": "FT8",
        "FT4": "FT4",
        "JT65": "JT65",
        "JT9": "JT9",
        "FST4": "FST4",
        "FST4W": "FST4W",
        "Q65": "Q65",
        "MSK144": "MSK144",
        "JS8": "JS8",
        "VARAC": "VARAC",
        "OLIVIA": "OLIVIA",
        "CONTESTIA": "CONTESTIA",
        "PSK31": "PSK31",
        "PSK63": "PSK63",
    }

    def normalize(self, mode: Optional[str]) -> Optional[str]:
        """
        Retourne le mode normalisé.

        Exemple :
            USB-D -> DATA
            CW-R  -> CW
        """

        if mode is None:
            return None

        mode = str(mode).strip().upper()

        return self.MODES.get(mode, mode)

    def is_phone(self, mode: Optional[str]) -> bool:
        mode = self.normalize(mode)
        return mode in {
            "USB",
            "LSB",
            "AM",
            "FM",
        }

    def is_cw(self, mode: Optional[str]) -> bool:
        return self.normalize(mode) == "CW"

    def is_digital(self, mode: Optional[str]) -> bool:
        mode = self.normalize(mode)

        return mode in {
            "DATA",
            "RTTY",
            "FT8",
            "FT4",
            "JT65",
            "JT9",
            "FST4",
            "FST4W",
            "Q65",
            "MSK144",
            "JS8",
            "VARAC",
            "OLIVIA",
            "CONTESTIA",
            "PSK31",
            "PSK63",
        }