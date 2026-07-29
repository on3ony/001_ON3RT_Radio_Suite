"""
ON3RT HF Manager V2
libraries/cat/serial_transport.py
"""

from __future__ import annotations

import logging
import time
import serial
from serial.tools import list_ports

# Même logger que apps/cat_server/logger.py ("CAT_SERVER") : cette couche
# basse ne dépend pas de apps/ (respect des couches), mais réutilise le
# logging standard sous le même nom, ce qui route automatiquement vers
# les mêmes handlers (fichier + console) une fois CATLogger initialisé.
_log = logging.getLogger("CAT_SERVER")


class SerialTransport:

    def __init__(self, port="", baudrate=19200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    @property
    def is_connected(self):
        return self.serial is not None and self.serial.is_open

    def connect(self):
        if self.is_connected:
            return True

        _log.info(f"Ouverture du port série {self.port} @ {self.baudrate} bauds (timeout={self.timeout}s)")

        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )

        _log.info(f"Port série {self.port} ouvert : is_open={self.serial.is_open}")

        return self.serial.is_open

    def disconnect(self):
        if self.is_connected:
            _log.info(f"Fermeture du port série {self.port}")
            self.serial.close()

        self.serial = None

    def write(self, data: bytes):
        self.serial.write(data)

    def read_until(self, terminator=b"\xfd"):
        return self.serial.read_until(terminator)

    def transact(self, frame: bytes) -> bytes:
        """
        Envoie une trame CI-V et retourne la réponse radio.

        Chaque commande envoyée, chaque trame reçue (écho compris) et
        chaque timeout sont tracés vers le logger "CAT_SERVER" (fichier +
        console), avec le délai réellement écoulé, pour pouvoir situer
        précisément l'instant où la radio cesse de répondre.

        L'écho éventuel de la commande envoyée est ignoré.
        """

        if not self.is_connected:
            raise RuntimeError("Port série non connecté.")

        # Nettoyage du buffer RX
        self.serial.reset_input_buffer()

        _log.info(f"TX : {frame.hex(' ').upper()}")

        self.write(frame)

        start = time.time()
        last_response = b""

        while True:

            response = self.read_until()

            if response:
                last_response = response

            if response and response != frame:
                elapsed = time.time() - start
                _log.info(f"RX ({elapsed:.3f}s) : {response.hex(' ').upper()}")
                return response

            if response and response == frame:
                _log.info(f"RX (écho ignoré) : {response.hex(' ').upper()}")

            if time.time() - start > self.timeout:
                elapsed = time.time() - start
                _log.warning(
                    f"TIMEOUT après {elapsed:.3f}s pour TX {frame.hex(' ').upper()}"
                    f" (dernier octet reçu : {last_response.hex(' ').upper() if last_response else 'aucun'})"
                )
                return response

    @staticmethod
    def available_ports():

        return [
            p.device
            for p in list_ports.comports()
        ]


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - serial_transport.py")
    print("=" * 50)

    ports = SerialTransport.available_ports()

    print("Ports détectés :")

    for p in ports:
        print(" -", p)