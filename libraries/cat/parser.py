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

        elif command == 0x15:
            # Famille "mètres" (S-mètre, Po mètre, SWR...), toutes sous
            # la commande 0x15 avec une sous-commande distincte (voir
            # libraries/cat/smeter.py) -- le parser ne fait qu'extraire
            # la sous-commande et les octets de donnée bruts, jamais
            # leur interprétation (propre à chaque manager de mètre,
            # comme KeyingSpeedManager.decode_wpm() pour 14 0C).
            if len(frame) >= 6:
                result["decoded"]["meter_subcommand"] = frame[5]
                result["decoded"]["meter_data"] = frame[6:-1]

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
