"""
ON3RT Radio Suite
libraries/logbook/duplicate_checker.py

Détection des doublons QSO.

Compatible :
- WSJT-X
- JTDX
- VarAC
- JS8Call
- FLDIGI
- N1MM Logger+

Python 3.13+
"""

from __future__ import annotations


class DuplicateChecker:
    """
    Vérifie si un QSO existe déjà dans une liste.
    """

    DEFAULT_FIELDS = (
        "CALL",
        "QSO_DATE",
        "TIME_ON",
        "BAND",
        "MODE",
    )

    def __init__(self, fields: tuple[str, ...] | None = None) -> None:
        self.fields = fields or self.DEFAULT_FIELDS

    def normalize(self, value) -> str:
        if value is None:
            return ""

        return str(value).strip().upper()

    def key(self, qso: dict) -> tuple:

        return tuple(
            self.normalize(qso.get(field))
            for field in self.fields
        )

    def is_duplicate(
        self,
        qso: dict,
        existing_qsos: list[dict],
    ) -> bool:

        target = self.key(qso)

        for existing in existing_qsos:

            if self.key(existing) == target:
                return True

        return False

    def filter_new(
        self,
        imported_qsos: list[dict],
        existing_qsos: list[dict],
    ) -> list[dict]:

        existing_keys = {
            self.key(qso)
            for qso in existing_qsos
        }

        new_qsos = []

        for qso in imported_qsos:

            k = self.key(qso)

            if k not in existing_keys:
                new_qsos.append(qso)
                existing_keys.add(k)

        return new_qsos