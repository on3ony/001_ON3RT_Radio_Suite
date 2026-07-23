"""
apps/contest/qso_table.py
ON3RT Radio Suite - Contest Logbook
"""

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt


class QSOTable(QTableWidget):

    HEADERS = [
        "ID",
        "Date",
        "UTC",
        "Call",
        "Band",
        "Mode",
        "Freq",
        "RST TX",
        "RST RX",
        "N° TX",
        "N° RX",
        "Exchange TX",
        "Exchange RX",
        "Points",
        "Mult",
        "Score",
    ]

    def __init__(self, parent=None):
        super().__init__(0, len(self.HEADERS), parent)

        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)

    def format_date(self, date):

        date = str(date)

        if len(date) == 8:
            return f"{date[6:8]}/{date[4:6]}/{date[0:4]}"

        return date

    def format_time(self, time):

        time = str(time)

        if len(time) == 4:
            return f"{time[:2]}:{time[2:4]}"

        return time

    def load_qsos(self, qsos):

        self.setSortingEnabled(False)
        self.setRowCount(0)

        for qso in qsos:

            row = self.rowCount()
            self.insertRow(row)

            score = (
                qso.get("points", 0)
                * max(qso.get("multiplier", 1), 1)
            )

            values = [
                qso.get("id", ""),
                self.format_date(qso.get("qso_date", "")),
                self.format_time(qso.get("time_on", "")),
                qso.get("callsign", ""),
                qso.get("band", ""),
                qso.get("mode", ""),
                qso.get("freq", ""),
                qso.get("rst_sent", ""),
                qso.get("rst_recv", ""),
                qso.get("serial_sent", ""),
                qso.get("serial_recv", ""),
                qso.get("exchange_sent", ""),
                qso.get("exchange_recv", ""),
                qso.get("points", ""),
                qso.get("multiplier", ""),
                score,
            ]

            for col, value in enumerate(values):

                item = QTableWidgetItem(str(value))
                item.setFlags(
                    item.flags()
                    & ~Qt.ItemFlag.ItemIsEditable
                )

                self.setItem(row, col, item)

        self.resizeColumnsToContents()
        self.setSortingEnabled(True)
