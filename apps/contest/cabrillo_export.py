"""
apps/contest/cabrillo_export.py
ON3RT Radio Suite - Contest Logbook

Export générique au format Cabrillo (v3). L'en-tête est configurable
(aucune règle spécifique à un concours précis n'est appliquée) : les
champs vides sont simplement omis.
"""

from __future__ import annotations

from pathlib import Path

_MODE_MAP = {
    "SSB": "PH", "USB": "PH", "LSB": "PH", "FM": "FM",
    "CW": "CW",
    "RTTY": "RY", "PSK31": "RY", "FT8": "RY", "FT4": "RY",
}

# clé d'en-tête -> tag Cabrillo
_HEADER_FIELDS = [
    ("contest_name", "CONTEST"),
    ("callsign", "CALLSIGN"),
    ("category_operator", "CATEGORY-OPERATOR"),
    ("category_assisted", "CATEGORY-ASSISTED"),
    ("category_band", "CATEGORY-BAND"),
    ("category_power", "CATEGORY-POWER"),
    ("category_mode", "CATEGORY-MODE"),
    ("category_station", "CATEGORY-STATION"),
    ("club", "CLUB"),
    ("name", "NAME"),
    ("email", "EMAIL"),
    ("location", "LOCATION"),
    ("operators", "OPERATORS"),
]


def _cabrillo_mode(mode: str) -> str:
    return _MODE_MAP.get((mode or "").upper(), (mode or "??")[:2].upper() or "??")


def _cabrillo_date(qso_date: str) -> str:
    qso_date = str(qso_date or "")
    if len(qso_date) == 8:
        return f"{qso_date[0:4]}-{qso_date[4:6]}-{qso_date[6:8]}"
    return qso_date


def _qso_line(qso: dict, my_callsign: str) -> str:
    try:
        freq_khz = int(float(qso.get("freq") or 0) / 1000)
    except (TypeError, ValueError):
        freq_khz = 0

    return (
        f"QSO: {freq_khz:>5} {_cabrillo_mode(qso.get('mode')):<2} "
        f"{_cabrillo_date(qso.get('qso_date')):<10} {str(qso.get('time_on') or ''):<4} "
        f"{my_callsign:<13} {str(qso.get('rst_sent') or ''):<3} {str(qso.get('exchange_sent') or ''):<6} "
        f"{str(qso.get('callsign') or ''):<13} {str(qso.get('rst_recv') or ''):<3} {str(qso.get('exchange_recv') or ''):<6}"
    )


def export_cabrillo(qsos: list[dict], header: dict, filename: str) -> int:
    """Écrit un fichier Cabrillo à partir des QSO et de l'en-tête fourni.

    header : dict de champs génériques (voir _HEADER_FIELDS), les clés
    absentes ou vides sont simplement omises de l'en-tête.
    """
    my_callsign = str(header.get("callsign") or "")

    lines = ["START-OF-LOG: 3.0"]
    for key, tag in _HEADER_FIELDS:
        value = header.get(key)
        if value:
            lines.append(f"{tag}: {value}")

    claimed_score = header.get("claimed_score")
    if claimed_score:
        lines.append(f"CLAIMED-SCORE: {claimed_score}")

    for qso in qsos:
        lines.append(_qso_line(qso, my_callsign))

    lines.append("END-OF-LOG:")

    Path(filename).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return len(qsos)
