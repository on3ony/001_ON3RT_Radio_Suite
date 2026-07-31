"""
ON3RT Radio Suite
libraries/voice/logger.py

Journal du service Voix (VoiceService) — même structure que
apps/cat_server/logger.py (CATLogger), mais fichier et logger dédiés :
VoiceService vit dans libraries/voice/ précisément parce qu'il n'a
aucune dépendance CAT (voir sa docstring) — réutiliser le logger
"CAT_SERVER" aurait créé une dépendance à l'envers (libraries/ ->
apps/) et aurait mélangé deux journaux sans rapport dans le même
fichier.

owner trace le demandeur de chaque synthèse, même convention que
PTTGuard/TransmissionService (apps/cat_server/) — pour une traçabilité
complète de bout en bout de la chaîne vocale, même si les deux
journaux restent des fichiers séparés (logs/cat_server.log vs
logs/voice.log).
"""

from __future__ import annotations

import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "voice.log"


class VoiceLogger:

    def __init__(self):
        self.logger = logging.getLogger("VOICE")

        if self.logger.handlers:
            return

        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def exception(self, exc: Exception) -> None:
        self.logger.exception(exc)

    # ------------------------------------------------------------------
    # Événements de synthèse — chaque étape importante d'une demande
    # ------------------------------------------------------------------

    def synthesis_requested(self, owner: str | None, engine: str | None) -> None:
        self.info(f"Synthèse demandée (demandeur={owner or 'inconnu'}, moteur={engine or 'auto'})")

    def synthesis_cache_hit(self, owner: str | None, cache_key: str) -> None:
        self.info(f"Cache HIT (demandeur={owner or 'inconnu'}, clé={cache_key})")

    def synthesis_cache_miss(self, owner: str | None, cache_key: str) -> None:
        self.info(f"Cache MISS (demandeur={owner or 'inconnu'}, clé={cache_key})")

    def synthesis_engine_fallback(self, owner: str | None, requested: str, reason: str) -> None:
        self.warning(
            f"Moteur '{requested}' indisponible (demandeur={owner or 'inconnu'}) — {reason} — repli sur pyttsx3"
        )

    def synthesis_completed(self, owner: str | None, engine: str, duration_s: float) -> None:
        self.info(f"Synthèse terminée (demandeur={owner or 'inconnu'}, moteur={engine}, durée={duration_s:.3f}s)")

    def synthesis_error(self, owner: str | None, reason: str) -> None:
        self.warning(f"Erreur de synthèse (demandeur={owner or 'inconnu'}) — {reason}")

    # ------------------------------------------------------------------
    # Nettoyage du cache (prune_cache) — étape 4c
    # ------------------------------------------------------------------

    def cache_pruned(self, removed_count: int, freed_bytes: int) -> None:
        if removed_count <= 0:
            return
        self.info(f"Cache vocal nettoyé (fichiers supprimés={removed_count}, espace libéré={freed_bytes} octets)")

    def cache_prune_file_error(self, path: str, reason: str) -> None:
        self.warning(f"Suppression impossible (fichier={path}) — {reason}")


logger = VoiceLogger()
