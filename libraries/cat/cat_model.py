"""
ON3RT HF Manager V2
modules/cat/cat_model.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CATModel:
    frequency: int = 0
    mode: str = ""
    vfo: str = "A"
    ptt: bool = False
    connected: bool = False
    port: str = ""
    baudrate: int = 19200
    last_update: datetime = field(default_factory=datetime.now)

    def update(
        self,
        *,
        frequency=None,
        mode=None,
        vfo=None,
        ptt=None,
        connected=None,
    ):
        if frequency is not None:
            self.frequency = frequency
        if mode is not None:
            self.mode = mode
        if vfo is not None:
            self.vfo = vfo
        if ptt is not None:
            self.ptt = ptt
        if connected is not None:
            self.connected = connected

        self.last_update = datetime.now()

    def as_dict(self):
        return {
            "frequency": self.frequency,
            "mode": self.mode,
            "vfo": self.vfo,
            "ptt": self.ptt,
            "connected": self.connected,
            "port": self.port,
            "baudrate": self.baudrate,
            "last_update": self.last_update.isoformat(),
        }


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - cat_model.py")
    print("=" * 50)

    model = CATModel()
    model.update(
        frequency=14074000,
        mode="USB",
        ptt=False,
        connected=True,
    )

    print(model)
    print(model.as_dict())
