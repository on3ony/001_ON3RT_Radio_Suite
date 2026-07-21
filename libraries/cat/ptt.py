"""
ON3RT HF Manager V2
modules/cat/ptt.py
"""

from __future__ import annotations

from libraries.cat.civ_protocol import CIVProtocol


class PTTManager:

    READ_COMMAND = bytes((0x1C, 0x00))
    WRITE_COMMAND = bytes((0x1C, 0x00))

    def __init__(self):
        self.civ = CIVProtocol()

    def build_read_command(self) -> bytes:
        return self.civ.build(self.READ_COMMAND)

    def build_set_command(self, tx: bool) -> bytes:
        state = 0x01 if tx else 0x00
        return self.civ.build(self.WRITE_COMMAND, bytes((state,)))


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - ptt.py")
    print("=" * 50)

    manager = PTTManager()

    print("Lecture :")
    print(manager.build_read_command().hex(" ").upper())

    print("\nPTT ON :")
    print(manager.build_set_command(True).hex(" ").upper())

    print("\nPTT OFF :")
    print(manager.build_set_command(False).hex(" ").upper())
