"""
apps/contest/contest_properties_dialog.py
ON3RT Radio Suite - Contest Logbook
"""

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox
)

from apps.contest.resources import ON3RT_DARK_THEME

CONTEST_NAMES = [
    "IARU HF World Championship",
    "CQ WW DX SSB",
    "CQ WW DX CW",
    "CQ WPX SSB",
    "CQ WPX CW",
    "ARRL DX",
    "REF HF",
    "UBA DX",
    "WAE",
    "Autre...",
]

OPERATOR_CATEGORIES = ["Single Operator", "Multi Operator"]

CONTEST_CATEGORIES = ["SOAB", "SOSB", "Multi", "Checklog"]

POWER_LEVELS = [
    "5 W (QRP)", "10 W", "25 W", "50 W",
    "100 W (LOW)", "200 W", "500 W", "1000 W (HIGH)",
]

DEFAULT_CALLSIGN = "ON3RT"
DEFAULT_POWER = "25 W"


class ContestPropertiesDialog(QDialog):

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Propriétés du concours")
        self.setStyleSheet(ON3RT_DARK_THEME)

        layout = QFormLayout(self)

        self.contest_name = QComboBox()
        self.contest_name.setEditable(True)
        self.contest_name.addItems(CONTEST_NAMES)
        self.contest_name.activated.connect(self._clear_on_autre)
        self._set_combo_text(self.contest_name, info.get("contest_name"))
        layout.addRow("Concours", self.contest_name)

        self.callsign = QLineEdit(info.get("callsign") or DEFAULT_CALLSIGN)
        layout.addRow("Indicatif", self.callsign)

        self.operator = QComboBox()
        self.operator.addItems(OPERATOR_CATEGORIES)
        self._set_combo_text(self.operator, info.get("operator"), OPERATOR_CATEGORIES[0])
        layout.addRow("Opérateur", self.operator)

        self.category = QComboBox()
        self.category.addItems(CONTEST_CATEGORIES)
        self._set_combo_text(self.category, info.get("category"), CONTEST_CATEGORIES[0])
        layout.addRow("Catégorie", self.category)

        self.power = QComboBox()
        self.power.addItems(POWER_LEVELS)
        self._set_combo_text(self.power, info.get("power"), DEFAULT_POWER)
        layout.addRow("Puissance", self.power)

        self.club = QLineEdit(info.get("club") or "")
        layout.addRow("Club", self.club)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @staticmethod
    def _set_combo_text(combo: QComboBox, value, fallback: str = ""):
        value = value or fallback
        index = combo.findText(value) if value else -1
        if index >= 0:
            combo.setCurrentIndex(index)
        elif combo.isEditable():
            combo.setEditText(value)

    def _clear_on_autre(self, index: int):
        if self.contest_name.itemText(index) == "Autre...":
            self.contest_name.setEditText("")

    def values(self) -> dict:
        return {
            "contest_name": self.contest_name.currentText().strip(),
            "callsign": self.callsign.text().strip(),
            "operator": self.operator.currentText().strip(),
            "category": self.category.currentText().strip(),
            "power": self.power.currentText().strip(),
            "club": self.club.text().strip(),
        }
