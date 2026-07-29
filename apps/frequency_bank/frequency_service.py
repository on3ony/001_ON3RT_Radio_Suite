"""
ON3RT Radio Suite
Module Banque de fréquences
Service partagé.

FrequencyService détient l'unique accès à FrequencyRepository et
publie des signaux Qt à chaque mutation, pour que tout consommateur
(fenêtre du module, futurs Dashboard/Scanner) reste synchronisé sans
avoir à sonder la base.

La détection de bande s'appuie sur BandManager
(libraries/radio/band_manager.py), seule référence des bandes de
toute la Suite — consommé ici en lecture seule, sans aucune
modification de ce fichier. Cette étape ne renvoie donc pour
l'instant que le nom de bande, sans classification LF/MF/HF/VHF/UHF/
SHF ni bornes enrichies : cette richesse est prévue pour le chantier
distinct d'unification de BandManager, différé après la validation
complète de ce module.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from apps.frequency_bank.models import Frequency
from apps.frequency_bank.repository import FrequencyRepository
from libraries.radio.band_manager import BandManager

DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "frequency_bank_seed.json"


class FrequencyService(QObject):

    frequency_added = Signal(dict)
    frequency_updated = Signal(dict)
    frequency_deleted = Signal(int)
    bank_reloaded = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._repository = FrequencyRepository()
        self._band_manager = BandManager()

        # Premier lancement : si la base est vide, charge automatiquement
        # le jeu de données de référence (data/frequency_bank_seed.json).
        # Ne se déclenche qu'une seule fois : dès que la base contient au
        # moins une entrée (y compris juste après ce chargement), plus
        # aucun import automatique n'a lieu aux démarrages suivants — les
        # modifications de l'utilisateur sont préservées.
        if self._repository.count() == 0 and DEFAULT_SEED_PATH.exists():
            self.load_from_json(DEFAULT_SEED_PATH)

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def close(self):
        self._repository.close()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, frequency: Frequency) -> int:
        new_id = self._repository.add(frequency)
        frequency.id = new_id
        self.frequency_added.emit(asdict(frequency))
        return new_id

    def update(self, frequency: Frequency) -> None:
        self._repository.update(frequency)
        self.frequency_updated.emit(asdict(frequency))

    def delete(self, frequency_id: int) -> None:
        self._repository.delete(frequency_id)
        self.frequency_deleted.emit(frequency_id)

    def get_all(self) -> list[Frequency]:
        return self._repository.get_all()

    def get_by_id(self, frequency_id: int):
        return self._repository.get_by_id(frequency_id)

    def count(self) -> int:
        return self._repository.count()

    # ------------------------------------------------------------------
    # Recherches
    # ------------------------------------------------------------------

    def by_band(self, band: str) -> list[Frequency]:
        return self._repository.by_band(band)

    def by_mode(self, mode: str) -> list[Frequency]:
        return self._repository.by_mode(mode)

    def by_category(self, category: str) -> list[Frequency]:
        return self._repository.by_category(category)

    def by_range(self, start: float, end: float) -> list[Frequency]:
        return self._repository.by_range(start, end)

    def by_nearest(self, frequency: float, tolerance: float = 0.005) -> list[Frequency]:
        return self._repository.by_nearest(frequency, tolerance)

    def favorites(self) -> list[Frequency]:
        return self._repository.favorites()

    def active(self) -> list[Frequency]:
        return self._repository.active()

    def search(self, text: str) -> list[Frequency]:
        return self._repository.search(text)

    # ------------------------------------------------------------------
    # Détection de bande (BandManager, lecture seule, portée réduite)
    # ------------------------------------------------------------------

    def detect_band(self, frequency_mhz: float) -> dict:
        frequency_hz = int(round(frequency_mhz * 1_000_000))
        band_name = self._band_manager.get_band(frequency_hz)

        return {
            "frequency": frequency_mhz,
            "band": band_name,
            "known_matches": (
                self._repository.by_nearest(frequency_mhz) if band_name else []
            ),
        }

    # ------------------------------------------------------------------
    # Chargement initial depuis un fichier JSON
    # ------------------------------------------------------------------

    def load_from_json(self, path) -> int:
        path = Path(path)

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        for existing in self._repository.get_all():
            self._repository.delete(existing.id)

        for item in data:
            frequency = Frequency(
                frequency=item["frequency"],
                start_frequency=item.get("start_frequency", item["frequency"]),
                end_frequency=item.get("end_frequency", item["frequency"]),
                band=item.get("band", ""),
                mode=item.get("mode", ""),
                category=item.get("category", ""),
                step=item.get("step", 0),
                modulation=item.get("modulation", ""),
                service=item.get("service", ""),
                name=item.get("name", ""),
                description=item.get("description", ""),
                country=item.get("country", ""),
                region=item.get("region", ""),
                source=item.get("source", ""),
                favorite=item.get("favorite", False),
                priority=item.get("priority", 0),
                active=item.get("active", True),
                color=item.get("color", ""),
            )
            self._repository.add(frequency)

        self.bank_reloaded.emit()
        return self._repository.count()
