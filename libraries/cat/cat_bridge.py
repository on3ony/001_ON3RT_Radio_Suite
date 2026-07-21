"""
ON3RT HF Manager V2
modules/cat/cat_bridge.py
"""

from __future__ import annotations

from libraries.cat.cat_engine import CATEngine


class CATBridge:
    """
    Pont entre les clients CAT (serveur, COM virtuel, TCP)
    et le moteur CAT.
    """

    def __init__(self, port="COM3", baudrate=19200):
        self.engine = CATEngine(port=port, baudrate=baudrate)

    def connect(self):
        return self.engine.connect()

    def disconnect(self):
        self.engine.disconnect()

    @property
    def connected(self):
        return self.engine.connected

    def forward(self, frame: bytes) -> bytes:
        """
        Transmet une trame CI-V à la radio et renvoie la réponse.
        """
        return self.engine.transact(frame)

    def read_frequency(self):
        return self.engine.read_frequency()

    def read_mode(self):
        return self.engine.read_mode()

    def read_ptt(self):
        return self.engine.read_ptt()

    def read_vfo(self):
        return self.engine.read_vfo()


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - cat_bridge.py")
    print("=" * 50)

    bridge = CATBridge()

    try:
        if bridge.connect():
            print("Connexion OK")
            print("Fréquence :", bridge.read_frequency())
            print("Mode      :", bridge.read_mode())
            print("PTT       :", bridge.read_ptt())
            print("VFO       :", bridge.read_vfo())
        else:
            print("Connexion impossible")
    finally:
        bridge.disconnect()
