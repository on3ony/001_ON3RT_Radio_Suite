"""
ON3RT HF Manager V2
modules/cat/cat_monitor.py
"""

from __future__ import annotations

import time
from threading import Thread

from libraries.cat.cat_engine import CATEngine


class CATMonitor:

    def __init__(self, port="COM3", baudrate=19200, interval=0.5):
        self.engine = CATEngine(port=port, baudrate=baudrate)
        self.interval = interval
        self.running = False
        self.thread = None

    def start(self):
        if not self.engine.connected:
            self.engine.connect()

        self.running = True
        self.thread = Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        self.engine.disconnect()

    def _loop(self):
        while self.running:
            try:
                print(
                    f"FREQ={self.engine.read_frequency()}  "
                    f"MODE={self.engine.read_mode()}  "
                    f"PTT={self.engine.read_ptt()}"
                )
            except Exception as exc:
                print(f"Erreur CAT : {exc}")

            time.sleep(self.interval)


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - cat_monitor.py")
    print("=" * 50)

    monitor = CATMonitor()

    try:
        monitor.start()
        input("\nEntrée pour arrêter...\n")
    finally:
        monitor.stop()
