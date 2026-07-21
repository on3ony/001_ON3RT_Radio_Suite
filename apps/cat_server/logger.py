"""
ON3RT Radio Suite
apps/cat_server/logger.py

Journal du CAT Server
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import logging


LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "cat_server.log"


class CATLogger:

    def __init__(self):

        self.logger = logging.getLogger("CAT_SERVER")

        if self.logger.handlers:
            return

        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(
            LOG_FILE,
            encoding="utf-8"
        )

        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def exception(self, exc: Exception):
        self.logger.exception(exc)

    def connected(self, port: str):
        self.info(f"Connexion radio : {port}")

    def disconnected(self):
        self.info("Déconnexion radio")

    def frequency(self, hz: int):

        mhz = hz / 1_000_000

        self.info(
            f"Fréquence : {mhz:.6f} MHz"
        )

    def mode(self, mode: str):
        self.info(f"Mode : {mode}")

    def ptt(self, state: bool):

        if state:
            self.info("PTT ON")
        else:
            self.info("PTT OFF")

    def event(self, text: str):
        self.info(text)

    def separator(self):

        self.info("-" * 70)


logger = CATLogger()


if __name__ == "__main__":

    logger.separator()
    logger.connected("COM3")
    logger.frequency(7103000)
    logger.mode("LSB")
    logger.ptt(False)
    logger.event("CAT Server démarré")
    logger.disconnected()

    print()
    print("Journal créé :")
    print(LOG_FILE)