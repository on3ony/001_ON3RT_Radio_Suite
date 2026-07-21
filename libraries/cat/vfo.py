"""
ON3RT HF Manager V2
modules/cat/vfo.py
"""

from __future__ import annotations

from libraries.cat.civ_protocol import CIVProtocol
from libraries.cat.constants import VFO_A, VFO_B


class VFOManager:

    READ_COMMAND = bytes((0x07,))
    SELECT_COMMAND = bytes((0x07,))

    VFO_CODES = {
        VFO_A: 0x00,
        VFO_B: 0x01,
    }

    def __init__(self):
        self.civ = CIVProtocol()

    def build_read_command(self) -> bytes:
        return self.civ.build(self.READ_COMMAND)

    def build_set_command(self, vfo) -> bytes:
        if isinstance(vfo, str):
            vfo = self.VFO_CODES[vfo.upper()]
        return self.civ.build(self.SELECT_COMMAND, bytes((vfo,)))

    def select_a(self):
        return self.build_set_command(VFO_A)

    def select_b(self):
        return self.build_set_command(VFO_B)


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - vfo.py")
    print("=" * 50)

    manager = VFOManager()

    print("Lecture :")
    print(manager.build_read_command().hex(" ").upper())

    print("\nVFO A :")
    print(manager.select_a().hex(" ").upper())

    print("\nVFO B :")
    print(manager.select_b().hex(" ").upper())
