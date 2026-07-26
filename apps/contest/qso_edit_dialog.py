"""
apps/contest/qso_edit_dialog.py
ON3RT Radio Suite - Contest Logbook
"""

from apps.contest.simple_form_dialog import SimpleFormDialog


class QSOEditDialog(SimpleFormDialog):

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
        super().__init__(qso, f"Modifier QSO #{qso.get('id')}", parent)

    def values(self) -> dict:
        return {
            "callsign": self.text("callsign").upper(),
            "band": self.text("band"),
            "mode": self.text("mode").upper(),
            "rst_sent": self.text("rst_sent"),
            "rst_recv": self.text("rst_recv"),
            "serial_sent": self.int_value("serial_sent"),
            "serial_recv": self.int_value("serial_recv"),
            "exchange_sent": self.text("exchange_sent"),
            "exchange_recv": self.text("exchange_recv"),
            "points": self.int_value("points"),
            "multiplier": self.int_value("multiplier"),
        }
