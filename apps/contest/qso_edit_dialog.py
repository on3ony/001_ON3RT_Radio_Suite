"""
apps/contest/qso_edit_dialog.py
ON3RT Radio Suite - Contest Logbook
"""

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox
)

from apps.contest.resources import ON3RT_DARK_THEME


class QSOEditDialog(QDialog):

    FIELDS = [
        ("callsign", "Call"),
        ("band", "Band"),
        ("mode", "Mode"),
        ("rst_sent", "RST TX"),
        ("rst_recv", "RST RX"),
        ("serial_sent", "N° TX"),
        ("serial_recv", "N° RX"),
        ("exchange_sent", "Exchange TX"),
        ("exchange_recv", "Exchange RX"),
        ("points", "Points"),
        ("multiplier", "Mult"),
    ]

    def __init__(self, qso: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Modifier QSO #{qso.get('id')}")
        self.setStyleSheet(ON3RT_DARK_THEME)

        self.inputs = {}
        layout = QFormLayout(self)

        for key, label in self.FIELDS:
            field = QLineEdit(str(qso.get(key, "") if qso.get(key) is not None else ""))
            self.inputs[key] = field
            layout.addRow(label, field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> dict:
        callsign = self.inputs["callsign"].text().strip().upper()
        band = self.inputs["band"].text().strip()
        mode = self.inputs["mode"].text().strip().upper()
        rst_sent = self.inputs["rst_sent"].text().strip()
        rst_recv = self.inputs["rst_recv"].text().strip()
        exchange_sent = self.inputs["exchange_sent"].text().strip()
        exchange_recv = self.inputs["exchange_recv"].text().strip()

        try:
            serial_sent = int(self.inputs["serial_sent"].text().strip() or 0)
        except ValueError:
            serial_sent = 0
        try:
            serial_recv = int(self.inputs["serial_recv"].text().strip() or 0)
        except ValueError:
            serial_recv = 0
        try:
            points = int(self.inputs["points"].text().strip() or 0)
        except ValueError:
            points = 0
        try:
            multiplier = int(self.inputs["multiplier"].text().strip() or 0)
        except ValueError:
            multiplier = 0

        return {
            "callsign": callsign,
            "band": band,
            "mode": mode,
            "rst_sent": rst_sent,
            "rst_recv": rst_recv,
            "serial_sent": serial_sent,
            "serial_recv": serial_recv,
            "exchange_sent": exchange_sent,
            "exchange_recv": exchange_recv,
            "points": points,
            "multiplier": multiplier,
        }
