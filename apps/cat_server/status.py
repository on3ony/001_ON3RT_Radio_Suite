"""
ON3RT Radio Suite
apps/cat_server/status.py

État partagé du CAT Server.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RadioStatus:
    connected: bool = False
    port: str = "COM3"

    frequency: int = 0
    mode: str = "---"

    ptt: bool = False

    vfo: str = "A"

    last_error: str = ""

    def reset(self) -> None:
        self.connected = False
        self.frequency = 0
        self.mode = "---"
        self.ptt = False
        self.vfo = "A"
        self.last_error = ""

    @property
    def frequency_mhz(self) -> str:
        if self.frequency <= 0:
            return "-----"

        return f"{self.frequency / 1_000_000:.6f}"

    @property
    def band(self) -> str:

        f = self.frequency

        if f == 0:
            return "--"

        if f < 2_000_000:
            return "160 m"

        if f < 4_000_000:
            return "80 m"

        if f < 6_000_000:
            return "60 m"

        if f < 8_000_000:
            return "40 m"

        if f < 11_000_000:
            return "30 m"

        if f < 15_000_000:
            return "20 m"

        if f < 19_000_000:
            return "17 m"

        if f < 22_000_000:
            return "15 m"

        if f < 26_000_000:
            return "12 m"

        if f < 30_000_000:
            return "10 m"

        if f < 54_000_000:
            return "6 m"

        if f < 148_000_000:
            return "2 m"

        if f < 450_000_000:
            return "70 cm"

        return "HF"