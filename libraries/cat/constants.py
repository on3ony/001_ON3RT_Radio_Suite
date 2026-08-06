"""
ON3RT HF Manager V2
modules/cat/constants.py
"""

from __future__ import annotations

DEFAULT_BAUDRATE = 19200
DEFAULT_TIMEOUT = 1.0

CIV_PREAMBLE = bytes((0xFE, 0xFE))
CIV_EOM = 0xFD

CIV_ACK = 0xFB
CIV_NG = 0xFA

CONTROLLER_ADDRESS = 0xE0
IC7300_ADDRESS = 0x94

VFO_A = "A"
VFO_B = "B"

MODE_LSB = 0x00
MODE_USB = 0x01
MODE_AM = 0x02
MODE_CW = 0x03
MODE_RTTY = 0x04
MODE_FM = 0x05
MODE_CW_R = 0x07
MODE_RTTY_R = 0x08
MODE_DV = 0x17

MODE_NAMES = {
    MODE_LSB: "LSB",
    MODE_USB: "USB",
    MODE_AM: "AM",
    MODE_CW: "CW",
    MODE_RTTY: "RTTY",
    MODE_FM: "FM",
    MODE_CW_R: "CW-R",
    MODE_RTTY_R: "RTTY-R",
    MODE_DV: "DV",
}

if __name__ == "__main__":
    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - constants.py")
    print("=" * 50)
    print("Adresse IC-7300 :", hex(IC7300_ADDRESS))
    print("Baudrate :", DEFAULT_BAUDRATE)
    print("Modes :", ", ".join(MODE_NAMES.values()))
