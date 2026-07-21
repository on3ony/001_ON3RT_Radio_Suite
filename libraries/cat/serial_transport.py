"""
ON3RT HF Manager V2
modules/cat/serial_transport.py
"""

from __future__ import annotations

import time
import serial
from serial.tools import list_ports


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

        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )

        return self.serial.is_open

    def disconnect(self):
        if self.is_connected:
            self.serial.close()

        self.serial = None

    def write(self, data: bytes):
        self.serial.write(data)

    def read_until(self, terminator=b"\xfd"):
        return self.serial.read_until(terminator)

    def transact(self, frame: bytes) -> bytes:
        """
        Envoie une trame CI-V et retourne la réponse radio.

        L'IC-7300 renvoie parfois l'écho de la commande
        avant la vraie réponse. On ignore donc les trames
        identiques à la commande envoyée.
        """

        if not self.is_connected:
            raise RuntimeError("Port série non connecté.")

        # Nettoyage du buffer RX
        self.serial.reset_input_buffer()

        # Envoi commande CI-V
        self.write(frame)

        # Recherche de la vraie réponse
        start = time.time()

        while True:

            response = self.read_until()

            if response and response != frame:
                return response

            # sécurité anti-boucle infinie
            if time.time() - start > self.timeout:
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