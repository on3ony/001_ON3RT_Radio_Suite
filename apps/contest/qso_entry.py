"""
apps/contest/qso_entry.py
ON3RT Radio Suite - Contest Logbook V4

Validation QSO par TAB (style contest)
"""

from datetime import datetime, timezone

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)


class QSOEntry(QWidget):

    qso_add_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.serial = 1

        self.call = QLineEdit()
        self.band = QLineEdit()
        self.mode = QLineEdit()

        self.rst_sent = QLineEdit("59")
        self.rst_recv = QLineEdit("59")

        self.number = QLineEdit()
        self.exchange = QLineEdit()

        self.add_button = QPushButton("Ajouter")

        self.fields = [
            self.call,
            self.band,
            self.mode,
            self.rst_sent,
            self.rst_recv,
            self.number,
            self.exchange,
        ]

        layout = QHBoxLayout(self)

        for name, widget in [
            ("Call", self.call),
            ("Band", self.band),
            ("Mode", self.mode),
            ("RST TX", self.rst_sent),
            ("RST RX", self.rst_recv),
            ("N°", self.number),
            ("Exchange", self.exchange),
        ]:
            layout.addWidget(QLabel(name))
            layout.addWidget(widget)

        layout.addWidget(self.add_button)

        self.add_button.clicked.connect(self.emit_qso)

        for field in self.fields:
            field.installEventFilter(self)

        self.call.setFocus()

    def eventFilter(self, obj, event):

        if (
            obj in self.fields
            and event.type() == event.Type.KeyPress
            and event.key() == Qt.Key.Key_Tab
        ):

            index = self.fields.index(obj)

            if index == len(self.fields) - 1:
                self.emit_qso()
                return True

        return super().eventFilter(obj, event)

    def emit_qso(self):

        now = datetime.now(timezone.utc)

        data = {
            "callsign": self.call.text().strip().upper(),
            "band": self.band.text().strip(),
            "mode": self.mode.text().strip().upper(),
            "rst_sent": self.rst_sent.text(),
            "rst_recv": self.rst_recv.text(),
            "serial": self.number.text() or str(self.serial),
            "exchange": self.exchange.text(),
            "qso_date": now.strftime("%Y%m%d"),
            "time_on": now.strftime("%H%M"),
        }

        self.serial += 1

        self.qso_add_requested.emit(data)

        self.clear()

    def clear(self):

        for field in [
            self.call,
            self.number,
            self.exchange,
        ]:
            field.clear()

        self.call.setFocus()
