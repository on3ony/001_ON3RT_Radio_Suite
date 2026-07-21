"""
ON3RT HF Manager V2
modules/cat/civ_protocol.py
"""

from __future__ import annotations

from libraries.cat.constants import (
    CIV_PREAMBLE,
    CIV_EOM,
    CONTROLLER_ADDRESS,
    IC7300_ADDRESS,
)


class CIVProtocol:

    def __init__(
        self,
        radio_address: int = IC7300_ADDRESS,
        controller_address: int = CONTROLLER_ADDRESS,
    ):
        self.radio_address = radio_address
        self.controller_address = controller_address

    def build(self, command: bytes, data: bytes = b"") -> bytes:
        return (
            CIV_PREAMBLE
            + bytes((self.radio_address,))
            + bytes((self.controller_address,))
            + command
            + data
            + bytes((CIV_EOM,))
        )

    @staticmethod
    def hex_dump(frame: bytes) -> str:
        return " ".join(f"{b:02X}" for b in frame)

    @staticmethod
    def is_valid(frame: bytes) -> bool:
        return (
            len(frame) >= 6
            and frame[:2] == CIV_PREAMBLE
            and frame[-1] == CIV_EOM
        )


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - civ_protocol.py")
    print("=" * 50)

    civ = CIVProtocol()

    frame = civ.build(bytes((0x03,)))

    print("Trame :", civ.hex_dump(frame))
    print("Valide :", civ.is_valid(frame))
