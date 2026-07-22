"""
ON3RT Radio Suite
Module Logbook
Modèles de données.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class QSO:
    id: Optional[int] = None

    qso_date: str = ""
    time_on: str = ""

    callsign: str = ""

    band: str = ""
    frequency: int = 0
    mode: str = ""

    rst_sent: str = ""
    rst_recv: str = ""

    operator: str = ""
    name: str = ""
    qth: str = ""
    locator: str = ""
    country: str = ""

    tx_power: int = 0
    rig: str = ""
    antenna: str = ""

    comment: str = ""

    software: str = ""

    imported: bool = False