"""
ON3RT Radio Suite
libraries/logbook/adif_parser.py

Parseur ADIF compatible avec :
- WSJT-X
- JTDX
- VarAC
- JS8Call
- FLDIGI
- N1MM Logger+

Python 3.13+
"""

from __future__ import annotations

from pathlib import Path


class ADIFParser:
    """Lecture d'un fichier ADIF."""

    def __init__(self) -> None:
        pass

    def read(self, filename: str | Path) -> list[dict]:

        path = Path(filename)

        if not path.exists():
            return []

        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        text = text.replace("\r", "")

        records = []
        current = {}

        i = 0
        n = len(text)

        while i < n:

            if text[i] != "<":
                i += 1
                continue

            j = text.find(">", i)

            if j == -1:
                break

            tag = text[i + 1 : j].strip()

            if not tag:
                i = j + 1
                continue

            upper = tag.upper()

            if upper == "EOH":
                current.clear()
                i = j + 1
                continue

            if upper == "EOR":
                if current:
                    records.append(current)
                current = {}
                i = j + 1
                continue

            parts = tag.split(":")

            if len(parts) < 2:
                i = j + 1
                continue

            field = parts[0].upper()

            try:
                length = int(parts[1])
            except ValueError:
                i = j + 1
                continue

            value_start = j + 1
            value_end = value_start + length

            value = text[value_start:value_end]

            current[field] = value

            i = value_end

        if current:
            records.append(current)

        return records