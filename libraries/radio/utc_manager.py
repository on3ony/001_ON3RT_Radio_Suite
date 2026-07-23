"""
utc_manager.py
----------------------------------------
ON3RT Radio Suite

Gestionnaire unique des dates et heures UTC.

Utilisé par :
- Contest
- Logbook
- ADIF
- Cabrillo
- QRZ
"""

from datetime import datetime, timezone


class UTCManager:
    """Gestionnaire des dates et heures UTC."""

    @staticmethod
    def now() -> datetime:
        """Retourne la date/heure UTC."""
        return datetime.now(timezone.utc)

    @classmethod
    def date(cls) -> str:
        """Date ISO : 2026-07-23"""
        return cls.now().strftime("%Y-%m-%d")

    @classmethod
    def time(cls) -> str:
        """Heure UTC : 14:35:42"""
        return cls.now().strftime("%H:%M:%S")

    @classmethod
    def datetime(cls) -> str:
        """Date + heure ISO."""
        return cls.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def adif_date(cls) -> str:
        """Format ADIF : YYYYMMDD"""
        return cls.now().strftime("%Y%m%d")

    @classmethod
    def adif_time(cls) -> str:
        """Format ADIF : HHMMSS"""
        return cls.now().strftime("%H%M%S")

    @classmethod
    def cabrillo_date(cls) -> str:
        """Format Cabrillo : YYYY-MM-DD"""
        return cls.now().strftime("%Y-%m-%d")

    @classmethod
    def cabrillo_time(cls) -> str:
        """Format Cabrillo : HHMM"""
        return cls.now().strftime("%H%M")

    @classmethod
    def timestamp(cls) -> int:
        """Timestamp Unix UTC."""
        return int(cls.now().timestamp())