"""
ON3RT Radio Suite
libraries/cw/logger.py

Journal du chantier CW (CWService) — même structure que
libraries/voice/logger.py (VoiceLogger), mais fichier et logger dédiés :
CWService vit dans libraries/cw/ précisément parce qu'il n'a aucune
dépendance à apps/cat_server/ (le backend réel, PTTKeyerBackend, lui
est injecté depuis l'extérieur — voir docstring de cw_service.py) —
réutiliser le logger CAT_SERVER ou VOICE aurait mélangé des journaux
sans rapport dans le même fichier.

owner trace le demandeur de chaque envoi, même convention que
PTTGuard/TransmissionService/VoiceService — pour une traçabilité
complète, même si chacun garde son propre fichier de log.
"""

from __future__ import annotations

import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "cw.log"


class CWLogger:

    def __init__(self):
        self.logger = logging.getLogger("CW")

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

    # ------------------------------------------------------------------
    # Événements d'émission — chaque étape importante d'un envoi
    # ------------------------------------------------------------------

    def cw_requested(self, owner: str | None) -> None:
        self.info(f"Émission CW demandée (demandeur={owner or 'inconnu'})")

    def cw_rejected(self, owner: str | None, reason: str) -> None:
        self.warning(f"Émission CW refusée (demandeur={owner or 'inconnu'}) — {reason}")

    def cw_started(self, owner: str | None) -> None:
        self.info(f"Émission CW démarrée (demandeur={owner or 'inconnu'})")

    def cw_finished(self, owner: str | None) -> None:
        self.info(f"Émission CW terminée (demandeur={owner or 'inconnu'})")

    def cw_stopped(self, owner: str | None) -> None:
        self.info(f"Émission CW arrêtée manuellement (demandeur={owner or 'inconnu'})")

    def cw_error(self, owner: str | None, reason: str) -> None:
        self.warning(f"Erreur d'émission CW (demandeur={owner or 'inconnu'}) — {reason}")


logger = CWLogger()
