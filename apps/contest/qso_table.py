"""
apps/contest/qso_table.py
ON3RT Radio Suite - Contest Logbook
"""

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QMenu
from PySide6.QtCore import Qt, Signal


class QSOTable(QTableWidget):

    editRequested = Signal(int)
    deleteRequested = Signal(int)

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

    def format_freq(self, freq):
        try:
            if freq in (None, "", "None"):
                return ""
            hz = int(float(freq))
            return f"{hz:,}".replace(",", ".")
        except Exception:
            return str(freq)

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
                self.format_freq(qso.get("freq", "")),
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

    def _selected_qso_id(self):
        row=self.currentRow()
        if row<0:
            return None
        item=self.item(row,0)
        if item is None:
            return None
        try:
            return int(item.text())
        except Exception:
            return None

    def mouseDoubleClickEvent(self,event):
        qso_id=self._selected_qso_id()
        if qso_id is not None:
            self.editRequested.emit(qso_id)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self,event):
        qso_id=self._selected_qso_id()
        if qso_id is None:
            return
        menu=QMenu(self)
        a1=menu.addAction("Modifier")
        a2=menu.addAction("Supprimer")
        act=menu.exec(event.globalPos())
        if act==a1:
            self.editRequested.emit(qso_id)
        elif act==a2:
            self.deleteRequested.emit(qso_id)

