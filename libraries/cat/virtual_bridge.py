"""
==================================================
ON3RT HF Manager V2
Module : virtual_bridge.py

Bridge CAT transparent
COM20 <-> COM21 (VSPE)
COM21 <-> COM3 (IC-7300)

Auteur : ON3RT
==================================================
"""

from __future__ import annotations

import threading
import time

import serial


class VirtualBridge:
    """
    Bridge série transparent entre
    COM21 (VSPE) et COM3 (IC-7300).
    """

    def __init__(
        self,
        virtual_port: str = "COM21",
        radio_port: str = "COM3",
        baudrate: int = 19200,
        timeout: float = 0.05,
        debug: bool = True,
    ) -> None:

        self.virtual_port = virtual_port
        self.radio_port = radio_port
        self.baudrate = baudrate
        self.timeout = timeout
        self.debug = debug

        self.virtual_serial = None
        self.radio_serial = None

        self.running = False

        self.thread_v2r = None
        self.thread_r2v = None

    def start(self):

        if self.running:
            return

        print(f"Ouverture {self.virtual_port}...")

        self.virtual_serial = serial.Serial(
            self.virtual_port,
            self.baudrate,
            timeout=self.timeout,
        )

        print(f"Ouverture {self.radio_port}...")

        self.radio_serial = serial.Serial(
            self.radio_port,
            self.baudrate,
            timeout=self.timeout,
        )

        self.running = True

        self.thread_v2r = threading.Thread(
            target=self._forward_virtual_to_radio,
            daemon=True,
        )

        self.thread_r2v = threading.Thread(
            target=self._forward_radio_to_virtual,
            daemon=True,
        )

        self.thread_v2r.start()
        self.thread_r2v.start()

        print()
        print("========================================")
        print("Bridge actif")
        print("========================================")
        print(f"{self.virtual_port} <--> {self.radio_port}")
        print("========================================")

    def stop(self):

        self.running = False

        time.sleep(0.2)

        if self.virtual_serial:
            self.virtual_serial.close()

        if self.radio_serial:
            self.radio_serial.close()

        print("Bridge arrêté.")

    def _forward_virtual_to_radio(self):

        while self.running:

            try:

                count = self.virtual_serial.in_waiting

                if count:

                    data = self.virtual_serial.read(count)

                    if self.debug:
                        print("[V→R]", data.hex(" ").upper())

                    self.radio_serial.write(data)

                else:

                    time.sleep(0.002)

            except Exception as e:

                print("Erreur V→R :", e)
                self.running = False

    def _forward_radio_to_virtual(self):

        while self.running:

            try:

                count = self.radio_serial.in_waiting

                if count:

                    data = self.radio_serial.read(count)

                    if self.debug:
                        print("[R→V]", data.hex(" ").upper())

                    self.virtual_serial.write(data)

                else:

                    time.sleep(0.002)

            except Exception as e:

                print("Erreur R→V :", e)
                self.running = False


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - virtual_bridge.py")
    print("=" * 50)

    bridge = VirtualBridge()

    try:

        bridge.start()

        input("\nEntrée pour arrêter...\n")

    except KeyboardInterrupt:

        pass

    finally:

        bridge.stop()