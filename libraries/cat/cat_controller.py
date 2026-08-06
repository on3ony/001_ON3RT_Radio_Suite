"""
ON3RT HF Manager V2
modules/cat/cat_controller.py
"""

from __future__ import annotations

from libraries.cat.cat_engine import CATEngine


class CATController:

    def __init__(self, port="COM3", baudrate=19200):
        self.engine = CATEngine(port=port, baudrate=baudrate)

    def connect(self):
        return self.engine.connect()

    def disconnect(self):
        self.engine.disconnect()

    @property
    def connected(self):
        return self.engine.connected

    def read_frequency(self):
        return self.engine.read_frequency()

    def set_frequency(self, hz):
        self.engine.set_frequency(hz)

    def read_mode(self):
        return self.engine.read_mode()

    def set_mode(self, mode):
        self.engine.set_mode(mode)

    def read_ptt(self):
        return self.engine.read_ptt()

    def set_ptt(self, state):
        self.engine.set_ptt(state)

    def read_smeter(self):
        return self.engine.read_smeter()

    def set_data_mode(self, enabled):
        return self.engine.set_data_mode(enabled)

    def send_cw_message(self, text):
        self.engine.send_cw_message(text)

    def stop_cw_message(self):
        self.engine.stop_cw_message()

    def set_keying_speed(self, wpm):
        self.engine.set_keying_speed(wpm)

    def read_vfo(self):
        return self.engine.read_vfo()

    def set_vfo(self, vfo):
        self.engine.set_vfo(vfo)


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - cat_controller.py")
    print("=" * 50)

    controller = CATController()

    if controller.connect():
        print("Fréquence :", controller.read_frequency())
        print("Mode      :", controller.read_mode())
        print("PTT       :", controller.read_ptt())
        controller.disconnect()
    else:
        print("Connexion impossible.")
