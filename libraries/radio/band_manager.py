"""
band_manager.py
----------------------------------------
ON3RT Radio Suite

Gestionnaire des bandes radioamateur.

Convertit automatiquement une fréquence (Hz)
en nom de bande.

Exemple :
    14074000 -> 20m
    7074000  -> 40m
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Band:
    name: str
    lower: int
    upper: int


class BandManager:
    """Gestionnaire des bandes radioamateur."""

    BANDS = [
        Band("2200m", 135700, 137800),
        Band("630m", 472000, 479000),
        Band("160m", 1800000, 2000000),
        Band("80m", 3500000, 3800000),
        Band("60m", 5351000, 5366500),
        Band("40m", 7000000, 7200000),
        Band("30m", 10100000, 10150000),
        Band("20m", 14000000, 14350000),
        Band("17m", 18068000, 18168000),
        Band("15m", 21000000, 21450000),
        Band("12m", 24890000, 24990000),
        Band("10m", 28000000, 29700000),
        Band("6m", 50000000, 52000000),
        Band("4m", 70000000, 71000000),
        Band("2m", 144000000, 146000000),
        Band("70cm", 430000000, 440000000),
        Band("23cm", 1240000000, 1300000000),
    ]

    def get_band(self, frequency_hz: int) -> Optional[str]:
        """
        Retourne le nom de la bande.

        Parameters
        ----------
        frequency_hz : int
            Fréquence en Hertz.

        Returns
        -------
        str | None
        """

        try:
            frequency_hz = int(frequency_hz)
        except (TypeError, ValueError):
            return None

        for band in self.BANDS:
            if band.lower <= frequency_hz <= band.upper:
                return band.name

        return None

    def is_hf(self, frequency_hz: int) -> bool:
        """Retourne True si la fréquence est en HF."""

        band = self.get_band(frequency_hz)
        return band in {
            "2200m",
            "630m",
            "160m",
            "80m",
            "60m",
            "40m",
            "30m",
            "20m",
            "17m",
            "15m",
            "12m",
            "10m",
        }

    def is_vhf(self, frequency_hz: int) -> bool:
        """Retourne True si la fréquence est en VHF."""

        return self.get_band(frequency_hz) in {
            "6m",
            "4m",
            "2m",
        }

    def is_uhf(self, frequency_hz: int) -> bool:
        """Retourne True si la fréquence est en UHF."""

        return self.get_band(frequency_hz) in {
            "70cm",
            "23cm",
        }