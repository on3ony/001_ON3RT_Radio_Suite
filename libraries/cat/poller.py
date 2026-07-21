"""
ON3RT HF Manager V2
modules/cat/poller.py
"""

from __future__ import annotations

import time
from threading import Event, Thread

from libraries.cat.cat_engine import CATEngine


class CATPoller:

    def __init__(self, port="COM3", baudrate=19200, interval=0.5):
        self.engine = CATEngine(port=port, baudrate=baudrate)
        self.interval = interval
        self._stop = Event()
        self._thread = None

    def start(self):
        if not self.engine.connected:
            self.engine.connect()

        self._stop.clear()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        self.engine.disconnect()

    def _run(self):
        while not self._stop.is_set():
            try:
                self.poll()
            except Exception as exc:
                print(f"Poller: {exc}")
            self._stop.wait(self.interval)

    def poll(self):
        frequency = self.engine.read_frequency()
        mode = self.engine.read_mode()
        ptt = self.engine.read_ptt()
        print(f"{frequency} Hz | {mode} | PTT={ptt}")


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - poller.py")
    print("=" * 50)

    poller = CATPoller()

    try:
        poller.start()
        input("\nEntrée pour arrêter...\n")
    finally:
        poller.stop()
