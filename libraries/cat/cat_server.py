"""
==================================================
ON3RT HF Manager V2
Module : cat_server.py

Serveur CAT multi-clients

Auteur : ON3RT
==================================================
"""

from __future__ import annotations

import threading
import time
import logging
from typing import Callable

from libraries.cat.cat_engine import CATEngine


log = logging.getLogger(__name__)


class CATServer:
    """
    Serveur CAT central.

    Une seule connexion COM3 est ouverte.

    Tous les clients utilisent cette instance.
    """

    def __init__(
        self,
        port: str = "COM3",
        baudrate: int = 19200,
        debug: bool = False,
    ):

        self.engine = CATEngine(
            port=port,
            baudrate=baudrate,
        )

        self.debug = debug

        self.running = False

        self.lock = threading.RLock()

        self.clients: dict[int, Callable[[bytes], None]] = {}

        self.next_client = 1

        self.monitor_thread = None

        self.poll_delay = 0.10

        self.last_frequency = None
        self.last_mode = None
        self.last_ptt = None

        self.tx_frames = 0
        self.rx_frames = 0

    # ----------------------------------------------------------

    @property
    def connected(self):

        return self.engine.connected

    # ----------------------------------------------------------

    def start(self):

        if self.running:
            return True

        if not self.engine.connect():
            return False

        self.running = True

        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
        )

        self.monitor_thread.start()

        log.info("CAT Server démarré.")

        return True

    # ----------------------------------------------------------

    def stop(self):

        self.running = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)

        self.engine.disconnect()

        log.info("CAT Server arrêté.")

    # ----------------------------------------------------------

    def register_client(
        self,
        callback: Callable[[bytes], None],
    ) -> int:

        with self.lock:

            cid = self.next_client

            self.clients[cid] = callback

            self.next_client += 1

            log.info("Client %s connecté", cid)

            return cid

    # ----------------------------------------------------------

    def unregister_client(self, client_id: int):

        with self.lock:

            if client_id in self.clients:

                del self.clients[client_id]

                log.info("Client %s déconnecté", client_id)

    # ----------------------------------------------------------

    def transact(
        self,
        frame: bytes,
    ) -> bytes:

        with self.lock:

            reply = self.engine.transact(frame)

            self.tx_frames += 1
            self.rx_frames += 1

            self._broadcast(reply)

            return reply

    # ----------------------------------------------------------

    def read_frequency(self):

        with self.lock:
            return self.engine.read_frequency()

    # ----------------------------------------------------------

    def read_mode(self):

        with self.lock:
            return self.engine.read_mode()

    # ----------------------------------------------------------

    def read_ptt(self):

        with self.lock:
            return self.engine.read_ptt()

    # ----------------------------------------------------------

    def _broadcast(self, frame: bytes):

        with self.lock:

            dead = []

            for cid, callback in self.clients.items():

                try:

                    callback(frame)

                except Exception:

                    dead.append(cid)

            for cid in dead:

                self.clients.pop(cid, None)

    # ----------------------------------------------------------

    def _monitor_loop(self):

        while self.running:

            try:

                freq = self.read_frequency()

                if freq != self.last_frequency:

                    self.last_frequency = freq

                    if self.debug:

                        print(f"FREQ {freq}")

                mode = self.read_mode()

                if mode != self.last_mode:

                    self.last_mode = mode

                    if self.debug:

                        print(f"MODE {mode}")

                ptt = self.read_ptt()

                if ptt != self.last_ptt:

                    self.last_ptt = ptt

                    if self.debug:

                        print(f"PTT {ptt}")

            except Exception as exc:

                log.error(exc)

            time.sleep(self.poll_delay)

    # ----------------------------------------------------------

    def stats(self):

        return {

            "connected": self.connected,

            "clients": len(self.clients),

            "tx_frames": self.tx_frames,

            "rx_frames": self.rx_frames,

            "frequency": self.last_frequency,

            "mode": self.last_mode,

            "ptt": self.last_ptt,

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - cat_server.py")
    print("=" * 50)

    server = CATServer(debug=True)

    if server.start():

        try:

            while True:

                print(server.stats())

                time.sleep(2)

        except KeyboardInterrupt:

            pass

        finally:

            server.stop()

    else:

        print("Impossible d'ouvrir le CAT.")