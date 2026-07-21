"""
ON3RT HF Manager V2
modules/cat/mode.py
"""

from __future__ import annotations

from libraries.cat.civ_protocol import CIVProtocol
from libraries.cat.constants import (
    MODE_LSB,
    MODE_USB,
    MODE_AM,
    MODE_CW,
    MODE_RTTY,
    MODE_FM,
    MODE_CW_R,
    MODE_RTTY_R,
    MODE_DV,
)


class ModeManager:

    READ_COMMAND = bytes((0x04,))
    WRITE_COMMAND = bytes((0x06,))

    MODES = {
        "LSB": MODE_LSB,
        "USB": MODE_USB,
        "AM": MODE_AM,
        "CW": MODE_CW,
        "RTTY": MODE_RTTY,
        "FM": MODE_FM,
        "CW-R": MODE_CW_R,
        "RTTY-R": MODE_RTTY_R,
        "DV": MODE_DV,
    }

    def __init__(self):
        self.civ = CIVProtocol()

    def build_read_command(self) -> bytes:
        return self.civ.build(self.READ_COMMAND)

    def build_set_command(self, mode) -> bytes:
        if isinstance(mode, str):
            mode = self.MODES[mode.upper()]
        return self.civ.build(self.WRITE_COMMAND, bytes((mode, 0x01)))


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - mode.py")
    print("=" * 50)

    manager = ModeManager()

    print("Lecture :")
    print(manager.build_read_command().hex(" ").upper())

    print("\nUSB :")
    print(manager.build_set_command("USB").hex(" ").upper())

    print("\nFM :")
    print(manager.build_set_command("FM").hex(" ").upper())
