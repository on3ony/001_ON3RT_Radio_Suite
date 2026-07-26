"""
apps/contest/contest_properties_dialog.py
ON3RT Radio Suite - Contest Logbook
"""

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox
)

from apps.contest.resources import ON3RT_DARK_THEME


class ContestPropertiesDialog(QDialog):

    FIELDS = [
        ("contest_name", "Concours"),
        ("callsign", "Indicatif"),
        ("operator", "Opérateur"),
        ("category", "Catégorie"),
        ("power", "Puissance"),
        ("club", "Club"),
    ]

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Propriétés du concours")
        self.setStyleSheet(ON3RT_DARK_THEME)

        self.inputs = {}
        layout = QFormLayout(self)

        for key, label in self.FIELDS:
            field = QLineEdit(str(info.get(key, "") or ""))
            self.inputs[key] = field
            layout.addRow(label, field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> dict:
        return {key: self.inputs[key].text().strip() for key, _ in self.FIELDS}
