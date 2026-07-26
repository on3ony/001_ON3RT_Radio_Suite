"""
apps/contest/adif_io.py
ON3RT Radio Suite - Contest Logbook

Adapte les QSO du logbook contest (colonnes internes) vers/depuis le
format ADIF, en réutilisant les outils génériques de libraries/logbook.
"""

from __future__ import annotations

from typing import Any

from libraries.logbook.adif_importer import ADIFImporter
from libraries.logbook.export_manager import ExportManager

# colonne interne -> tag ADIF
_EXPORT_FIELDS = {
    "callsign": "CALL",
    "qso_date": "QSO_DATE",
    "time_on": "TIME_ON",
    "band": "BAND",
    "mode": "MODE",
    "rst_sent": "RST_SENT",
    "rst_recv": "RST_RCVD",
    "serial_sent": "STX",
    "serial_recv": "SRX",
    "exchange_sent": "STX_STRING",
    "exchange_recv": "SRX_STRING",
    "operator": "OPERATOR",
    "locator": "GRIDSQUARE",
    "notes": "COMMENT",
}

# tag ADIF -> colonne interne (inverse du mapping ci-dessus)
_IMPORT_FIELDS = {tag: col for col, tag in _EXPORT_FIELDS.items()}


def _to_adif_record(qso: dict) -> dict:
    record = {}
    for col, tag in _EXPORT_FIELDS.items():
        value = qso.get(col)
        if value not in (None, ""):
            record[tag] = value

    freq = qso.get("freq")
    if freq not in (None, ""):
        try:
            record["FREQ"] = f"{float(freq) / 1_000_000:.6f}"
        except (TypeError, ValueError):
            pass

    return record


def export_adif(qsos: list[dict], filename: str) -> int:
    """Exporte une liste de QSO (colonnes internes) au format ADIF."""
    records = [_to_adif_record(qso) for qso in qsos]
    return ExportManager().export(records, filename)


def _from_adif_record(record: dict[str, str]) -> dict[str, Any]:
    qso: dict[str, Any] = {}
    for tag, value in record.items():
        col = _IMPORT_FIELDS.get(tag.upper())
        if col:
            qso[col] = value

    freq_mhz = record.get("FREQ")
    if freq_mhz:
        try:
            qso["freq"] = float(freq_mhz) * 1_000_000
        except ValueError:
            pass

    for col in ("serial_sent", "serial_recv"):
        if col in qso:
            try:
                qso[col] = int(qso[col])
            except (TypeError, ValueError):
                qso[col] = 0

    qso.setdefault("callsign", "")
    qso.setdefault("points", 1)
    qso.setdefault("multiplier", 1)
    return qso


def import_adif(filename: str) -> list[dict]:
    """Lit un fichier ADIF et retourne des QSO au format des colonnes internes."""
    records = ADIFImporter().load(filename)
    return [_from_adif_record(r) for r in records]
