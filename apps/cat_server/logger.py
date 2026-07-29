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
            "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
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

    # ------------------------------------------------------------------
    # Instrumentation CAT détaillée (diagnostic TIMEOUT / désynchronisation)
    # ------------------------------------------------------------------

    def port_opening(self, port: str, baudrate: int, timeout: float) -> None:
        self.info(f"Ouverture du port série {port} @ {baudrate} bauds (timeout={timeout}s)")

    def port_opened(self, port: str) -> None:
        self.info(f"Port série {port} ouvert (handle OS actif)")

    def port_closed(self, port: str) -> None:
        self.info(f"Port série {port} fermé")

    def polling_started(self, interval_ms: int) -> None:
        self.info(f"Polling démarré (intervalle {interval_ms} ms)")

    def polling_stopped(self) -> None:
        self.info("Polling arrêté")

    def tx(self, frame: bytes) -> None:
        self.info(f"TX : {frame.hex(' ').upper()}")

    def rx(self, frame: bytes) -> None:
        self.info(f"RX : {frame.hex(' ').upper()}")

    def rx_ignored_echo(self, frame: bytes) -> None:
        self.info(f"RX (écho ignoré) : {frame.hex(' ').upper()}")

    def cat_timeout(self, frame: bytes, elapsed: float, last_response: bytes) -> None:
        self.warning(
            f"TIMEOUT après {elapsed:.3f}s pour TX {frame.hex(' ').upper()}"
            f" (dernier octet reçu : {last_response.hex(' ').upper() if last_response else 'aucun'})"
        )

    def decoded(self, label: str, response: bytes, decoded: dict) -> None:
        self.info(
            f"{label} : RX brut={response.hex(' ').upper() if response else '(vide)'} -> décodé={decoded}"
        )


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