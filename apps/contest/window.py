"""
apps/contest/window.py
ON3RT Radio Suite - Contest Logbook V5
"""

import shutil
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow,QWidget,QVBoxLayout,QGroupBox,QHeaderView,QMessageBox,QFileDialog

from apps.contest.database import ContestDatabase
from apps.contest.menu import create_menu
from apps.contest.toolbar import create_toolbar
from apps.contest.qso_entry import QSOEntry
from apps.contest.qso_table import QSOTable
from apps.contest.qso_edit_dialog import QSOEditDialog
from apps.contest.contest_properties_dialog import ContestPropertiesDialog
from apps.contest.adif_io import import_adif as read_adif_file, export_adif as write_adif_file
from apps.contest.cabrillo_export_dialog import CabrilloExportDialog
from apps.contest.cabrillo_export import export_cabrillo as write_cabrillo_file
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

        self.resize(1500,900)
        self.setStyleSheet(ON3RT_DARK_THEME)

        self.build_ui()
        self.refresh()
        self.update_window_title()

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
        self.qso_entry.set_next_serial(self.db.get_next_serial())

    def update_window_title(self):
        name = self.db.get_contest_info().get("contest_name") or ""
        self.setWindowTitle(f"{WINDOW_TITLE} — {name}" if name else WINDOW_TITLE)

    def edit_contest_properties(self):
        dialog = ContestPropertiesDialog(self.db.get_contest_info(), self)
        if dialog.exec() == ContestPropertiesDialog.DialogCode.Accepted:
            self.db.set_contest_info(**dialog.values())
            self.update_window_title()

    def new_contest(self):
        answer = QMessageBox.question(
            self,
            "Nouveau concours",
            "Le journal actuel va être archivé et remis à zéro. Continuer ?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        db_path = self.db.db_path
        archive_dir = db_path.parent / "archives"
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = archive_dir / f"{db_path.stem}_{stamp}.db"

        self.db.close()
        if db_path.exists():
            shutil.copy(db_path, archive_path)

        self.db = ContestDatabase(db_path)
        self.db.reset_qsos()
        self.refresh()
        self.edit_contest_properties()

    def open_contest(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir un concours", str(self.db.db_path.parent),
            "Bases SQLite (*.db)",
        )
        if not path:
            return

        self.db.close()
        self.db = ContestDatabase(path)
        self.refresh()
        self.update_window_title()

    def import_adif(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importer ADIF", str(self.db.db_path.parent),
            "Fichiers ADIF (*.adi *.adif)",
        )
        if not path:
            return

        qsos = read_adif_file(path)
        for qso in qsos:
            self.db.add_qso(**qso)
        self.refresh()
        QMessageBox.information(
            self, "Import ADIF", f"{len(qsos)} QSO importé(s)."
        )

    def export_adif(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter ADIF", str(self.db.db_path.parent / "export.adi"),
            "Fichiers ADIF (*.adi)",
        )
        if not path:
            return

        count = write_adif_file(self.db.get_all_qsos(), path)
        QMessageBox.information(
            self, "Export ADIF", f"{count} QSO exporté(s) vers :\n{path}"
        )

    def export_cabrillo(self):
        info = self.db.get_contest_info()
        stats = self.db.get_statistics()
        defaults = {
            "contest_name": info.get("contest_name", ""),
            "callsign": info.get("callsign", ""),
            "category_operator": info.get("category", ""),
            "category_power": info.get("power", ""),
            "club": info.get("club", ""),
            "name": info.get("operator", ""),
            "operators": info.get("operator", ""),
            "claimed_score": str(stats.get("score", "")),
        }

        dialog = CabrilloExportDialog(defaults, self)
        if dialog.exec() != CabrilloExportDialog.DialogCode.Accepted:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter Cabrillo", str(self.db.db_path.parent / "export.log"),
            "Fichiers Cabrillo (*.log *.cbr)",
        )
        if not path:
            return

        count = write_cabrillo_file(self.db.get_all_qsos(), dialog.values(), path)
        QMessageBox.information(
            self, "Export Cabrillo", f"{count} QSO exporté(s) vers :\n{path}"
        )

    def show_about(self):
        QMessageBox.about(
            self, "À propos",
            f"{WINDOW_TITLE}\n\nLogbook de concours ON3RT Radio Suite.",
        )

    def save_contest_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le concours sous", str(self.db.db_path),
            "Bases SQLite (*.db)",
        )
        if not path:
            return

        self.db.conn.commit()
        shutil.copy(self.db.db_path, path)
        QMessageBox.information(
            self, "Enregistrer", f"Concours enregistré dans :\n{path}"
        )
