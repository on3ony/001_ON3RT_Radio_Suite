"""
apps/contest/simple_form_dialog.py
ON3RT Radio Suite - Contest Logbook

Dialogue de formulaire générique (liste de champs clé/libellé rendus
en QLineEdit + boutons Ok/Annuler). Base commune aux dialogues
d'édition de QSO, de propriétés du concours et d'export Cabrillo.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox

from apps.contest.resources import ON3RT_DARK_THEME


class SimpleFormDialog(QDialog):

    FIELDS: list[tuple[str, str]] = []

    def __init__(self, values: dict, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(ON3RT_DARK_THEME)

        self.inputs = {}
        layout = QFormLayout(self)

        for key, label in self.FIELDS:
            field = QLineEdit(str(values.get(key, "") or ""))
            self.inputs[key] = field
            layout.addRow(label, field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def text(self, key: str) -> str:
        return self.inputs[key].text().strip()

    def int_value(self, key: str, default: int = 0) -> int:
        try:
            return int(self.text(key) or default)
        except ValueError:
            return default

    def values(self) -> dict:
        return {key: self.text(key) for key, _ in self.FIELDS}
