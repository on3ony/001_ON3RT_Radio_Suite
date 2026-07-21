"""
ON3RT HF Manager V2
modules/cat/parser.py
"""

from __future__ import annotations

from libraries.cat.constants import MODE_NAMES


class CIVParser:

    def parse(self, frame: bytes) -> dict:

        result = {
            "raw": frame,
            "decoded": {}
        }

        if not frame or len(frame) < 6:
            return result

        command = frame[4]

        if command == 0x03:
            result["decoded"]["frequency_hz"] = self._decode_frequency(frame[5:-1])

        elif command == 0x04:
            mode = frame[5]
            result["decoded"]["mode"] = mode
            result["decoded"]["mode_name"] = MODE_NAMES.get(mode, "UNKNOWN")

        elif command == 0x1C:
            result["decoded"]["ptt"] = bool(frame[-2])

        elif command == 0x07:
            result["decoded"]["vfo"] = frame[-2]

        return result

    @staticmethod
    def _decode_frequency(data: bytes) -> int:
        if len(data) < 5:
            return 0

        digits = ""

        for b in reversed(data[:5]):
            digits += f"{b >> 4:X}{b & 0x0F:X}"

        try:
            return int(digits)
        except ValueError:
            return 0


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - parser.py")
    print("=" * 50)

    parser = CIVParser()

    frame = bytes.fromhex(
        "FE FE E0 94 03 00 74 40 01 00 FD"
    )

    print(parser.parse(frame))
