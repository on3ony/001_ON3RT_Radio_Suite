"""
apps/contest/cabrillo_export_dialog.py
ON3RT Radio Suite - Contest Logbook
"""

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox
)

from apps.contest.resources import ON3RT_DARK_THEME


class CabrilloExportDialog(QDialog):

    FIELDS = [
        ("contest_name", "Concours (CONTEST)"),
        ("callsign", "Indicatif (CALLSIGN)"),
        ("category_operator", "Catégorie opérateur"),
        ("category_assisted", "Assisted"),
        ("category_band", "Bande"),
        ("category_power", "Puissance"),
        ("category_mode", "Mode"),
        ("category_station", "Station"),
        ("club", "Club"),
        ("name", "Nom"),
        ("email", "Email"),
        ("location", "Localisation"),
        ("operators", "Opérateurs"),
        ("claimed_score", "Score revendiqué"),
    ]

    def __init__(self, defaults: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Cabrillo")
        self.setStyleSheet(ON3RT_DARK_THEME)

        self.inputs = {}
        layout = QFormLayout(self)

        for key, label in self.FIELDS:
            field = QLineEdit(str(defaults.get(key, "") or ""))
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
