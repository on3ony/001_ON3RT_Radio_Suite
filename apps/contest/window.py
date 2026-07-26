"""
apps/contest/window.py
ON3RT Radio Suite - Contest Logbook V5
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow,QWidget,QVBoxLayout,QGroupBox,QHeaderView,QMessageBox

from apps.contest.database import ContestDatabase
from apps.contest.menu import create_menu
from apps.contest.toolbar import create_toolbar
from apps.contest.qso_entry import QSOEntry
from apps.contest.qso_table import QSOTable
from apps.contest.qso_edit_dialog import QSOEditDialog
from apps.contest.statistics_panel import StatisticsPanel
from apps.contest.resources import WINDOW_TITLE, ON3RT_DARK_THEME
from libraries.radio.radio_manager import RadioManager

class ContestWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.db = ContestDatabase()
        self.radio = RadioManager()

        try:
            ok = self.radio.connect()
        except Exception:
            ok = False

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1500,900)
        self.setStyleSheet(ON3RT_DARK_THEME)

        self.build_ui()
        self.refresh()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_radio)
        self.timer.start(500)

        self.statusBar().showMessage(
            "CAT connecté" if ok else "CAT non connecté"
        )

    def build_ui(self):
        create_menu(self)
        create_toolbar(self)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        entry_box = QGroupBox("Saisie rapide Contest")
        entry_layout = QVBoxLayout(entry_box)
        self.qso_entry = QSOEntry(self.radio)
        entry_layout.addWidget(self.qso_entry)
        layout.addWidget(entry_box)

        table_box = QGroupBox("Logbook Contest")
        table_layout = QVBoxLayout(table_box)
        self.qso_table = QSOTable()
        h=self.qso_table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(True)
        table_layout.addWidget(self.qso_table)
        layout.addWidget(table_box,1)

        stats_box = QGroupBox("Statistiques")
        stats_layout = QVBoxLayout(stats_box)
        self.statistics = StatisticsPanel()
        stats_layout.addWidget(self.statistics)
        layout.addWidget(stats_box)

        self.qso_entry.qso_add_requested.connect(self.add_qso)
        self.qso_table.editRequested.connect(self.edit_qso)
        self.qso_table.deleteRequested.connect(self.delete_qso)

    def update_radio(self):
        try:
            self.radio.info()
            self.qso_entry.update_from_radio()
        except Exception:
            pass

    def add_qso(self,data):
        serial=self.db.get_next_serial()
        exchange_recv=data.get("exchange_recv") or ""
        try:
            serial_recv=int(exchange_recv)
        except (TypeError, ValueError):
            serial_recv=0
        self.db.add_qso(
            callsign=data.get("callsign"),
            qso_date=data.get("qso_date"),
            time_on=data.get("time_on"),
            band=data.get("band"),
            freq=data.get("freq"),
            mode=data.get("mode"),
            rst_sent=data.get("rst_sent"),
            rst_recv=data.get("rst_recv"),
            serial_sent=serial,
            serial_recv=serial_recv,
            exchange_sent=f"{serial:03d}",
            exchange_recv=exchange_recv,
            points=1,
            multiplier=1,
        )
        self.refresh()

    def edit_qso(self, qso_id):
        qso = self.db.get_qso(qso_id)
        if qso is None:
            return
        dialog = QSOEditDialog(qso, self)
        if dialog.exec() == QSOEditDialog.DialogCode.Accepted:
            self.db.update_qso(qso_id, **dialog.values())
            self.refresh()

    def delete_qso(self, qso_id):
        qso = self.db.get_qso(qso_id)
        if qso is None:
            return
        answer = QMessageBox.question(
            self,
            "Supprimer le QSO",
            f"Supprimer le QSO avec {qso.get('callsign', '')} ?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.db.delete_qso(qso_id)
            self.refresh()

    def refresh(self):
        self.qso_table.load_qsos(self.db.get_all_qsos())
        self.statistics.update_statistics(self.db.get_statistics())
