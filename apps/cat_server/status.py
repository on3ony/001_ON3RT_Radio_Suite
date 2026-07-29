"""
ON3RT Radio Suite
apps/cat_server/status.py

État partagé du CAT Server.
"""

from __future__ import annotations

from dataclasses import dataclass

from libraries.radio.band_manager import BandManager

_BAND_MANAGER = BandManager()


@dataclass
class RadioStatus:
    connected: bool = False
    port: str = "COM3"
    baudrate: int = 19200
    model: str = "IC-7300"

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
        return _BAND_MANAGER.get_band(self.frequency) or "--"