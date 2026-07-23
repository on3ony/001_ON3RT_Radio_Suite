"""
apps/contest/models.py
ON3RT Radio Suite - Contest Logbook V1
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class ContestQSO:
    id: int | None = None
    callsign: str = ""
    qso_date: str = ""
    time_on: str = ""
    band: str = ""
    freq: float | None = None
    mode: str = ""
    rst_sent: str = ""
    rst_recv: str = ""
    serial_sent: int = 0
    serial_recv: int = 0
    exchange_sent: str = ""
    exchange_recv: str = ""
    operator: str = ""
    locator: str = ""
    points: int = 1
    multiplier: int = 0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContestQSO":
        fields = cls.__dataclass_fields__.keys()
        values = {k: data.get(k) for k in fields}
        return cls(**values)

    @property
    def score(self) -> int:
        return self.points * max(self.multiplier, 1)

    def __str__(self) -> str:
        return (
            f"{self.callsign} {self.band} {self.mode} "
            f"{self.qso_date} {self.time_on}"
        )


if __name__ == "__main__":
    qso = ContestQSO(
        callsign="ON3RT",
        qso_date="20260723",
        time_on="0815",
        band="20m",
        mode="SSB",
        rst_sent="59",
        rst_recv="59",
        serial_sent=1,
        serial_recv=1,
        exchange_sent="001",
        exchange_recv="001",
        points=1,
        multiplier=1,
    )
    print(qso)
    print(qso.to_dict())
