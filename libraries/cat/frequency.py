"""
ON3RT HF Manager V2
modules/cat/frequency.py
"""

from __future__ import annotations

from libraries.cat.civ_protocol import CIVProtocol


class FrequencyManager:

    READ_COMMAND = bytes((0x03,))
    WRITE_COMMAND = bytes((0x05,))

    def __init__(self):
        self.civ = CIVProtocol()

    def build_read_command(self) -> bytes:
        return self.civ.build(self.READ_COMMAND)

    def build_set_command(self, frequency_hz: int) -> bytes:
        data = self._encode_frequency(frequency_hz)
        return self.civ.build(self.WRITE_COMMAND, data)

    @staticmethod
    def _encode_frequency(frequency_hz: int) -> bytes:
        value = f"{frequency_hz:010d}"
        out = bytearray()

        for i in range(8, -1, -2):
            pair = value[i:i+2]
            out.append((int(pair[0]) << 4) | int(pair[1]))

        return bytes(out)


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - frequency.py")
    print("=" * 50)

    manager = FrequencyManager()

    print("Lecture :")
    print(manager.build_read_command().hex(" ").upper())

    print("\nEcriture :")
    print(manager.build_set_command(14074000).hex(" ").upper())
