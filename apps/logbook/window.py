"""
ON3RT Radio Suite
Module Logbook
"""

from PySide6.QtWidgets import QFileDialog, QMessageBox

from libraries.ui.base_window import BaseWindow
from libraries.cat.cat_controller import CATController
from libraries.logbook.import_manager import ImportManager
from libraries.logbook.export_manager import ExportManager

from apps.logbook.models import QSO
from apps.logbook.qso_dialog import QSODialog
from apps.logbook.repository import LogbookRepository
from apps.logbook.table_model import LogbookTableModel
from apps.logbook.ui import LogbookUI


class LogbookWindow(BaseWindow):

    def __init__(self):
        super().__init__(
            title="Logbook",
            subtitle="Gestion du carnet de trafic"
        )

        self.repository = LogbookRepository()
        self.model = LogbookTableModel()
        self.cat = CATController()

        self.ui = LogbookUI()
        self.ui.table.setModel(self.model)
        self.content_layout.addWidget(self.ui)

        self.ui.add_button.clicked.connect(self.new_qso)
        self.ui.search_button.clicked.connect(self.search_qso)
        self.ui.delete_button.clicked.connect(self.delete_qso)
        self.ui.import_button.clicked.connect(self.import_adif)
        self.ui.export_button.clicked.connect(self.export_adif)

        self.load_logbook()

    def load_logbook(self):
        qsos = self.repository.get_all()
        self.model.set_qsos(qsos)
        self.statusBar().showMessage(f"{len(qsos)} QSO(s)")

    def search_qso(self):
        text = self.ui.search_edit.text().strip()
        if not text:
            self.load_logbook()
            return
        self.model.set_qsos(self.repository.search(text))

    def new_qso(self):
        dialog = QSODialog(self, QSO())
        if dialog.exec():
            self.repository.add_qso(dialog.get_qso())
            self.load_logbook()

    def delete_qso(self):
        index = self.ui.table.currentIndex()
        if not index.isValid():
            return
        qso = self.model.qso(index.row())
        self.repository.delete(qso.id)
        self.load_logbook()

    def import_adif(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Importer ADIF",
            "",
            "ADIF (*.adi *.adif)"
        )
        if not filename:
            return

        manager = ImportManager()
        try:
            result = manager.import_file(filename)
        finally:
            manager.close()

        self.load_logbook()

        QMessageBox.information(
            self,
            "Import ADIF",
            f"Total : {result['total']}\n"
            f"Importés : {result['imported']}\n"
            f"Doublons : {result['duplicates']}\n"
            f"Erreurs : {result['errors']}"
        )

    def export_adif(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter ADIF",
            "",
            "ADIF (*.adi)"
        )
        if not filename:
            return

        manager = ExportManager()
        count = manager.export(self.repository.get_all(), filename)

        QMessageBox.information(
            self,
            "Export ADIF",
            f"{count} QSO exporté(s)."
        )

    def closeEvent(self, event):
        self.repository.close()
        super().closeEvent(event)
