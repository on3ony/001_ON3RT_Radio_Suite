"""
ON3RT Radio Suite
Module Banque de fréquences
Modèles de données.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Frequency:

    # ----- Identifiant -----
    id: Optional[int] = None

    # ----- Fréquences -----
    frequency: float = 0.0
    start_frequency: float = 0.0
    end_frequency: float = 0.0

    # ----- Classification -----
    band: str = ""
    mode: str = ""
    category: str = ""

    # ----- Paramètres radio -----
    step: int = 0
    modulation: str = ""
    service: str = ""

    # ----- Description -----
    name: str = ""
    description: str = ""

    # ----- Provenance -----
    country: str = ""
    region: str = ""
    source: str = ""

    # ----- Options -----
    favorite: bool = False
    priority: int = 0
    active: bool = True
    color: str = ""
