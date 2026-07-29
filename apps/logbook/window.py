"""
ON3RT Radio Suite
Module Logbook
"""

from PySide6.QtWidgets import QFileDialog, QMessageBox

from libraries.ui.base_window import BaseWindow
from libraries.logbook.import_manager import ImportManager
from libraries.logbook.export_manager import ExportManager

from apps.logbook.models import QSO
from apps.logbook.qso_dialog import QSODialog
from apps.logbook.repository import LogbookRepository
from apps.logbook.table_model import LogbookTableModel
from apps.logbook.ui import LogbookUI


class LogbookWindow(BaseWindow):

    def __init__(self, radio_service=None):
        super().__init__(
            title="Logbook",
            subtitle="Gestion du carnet de trafic"
        )

        self.repository = LogbookRepository()
        self.model = LogbookTableModel()

        # RadioService partagé (apps.cat_server.radio_service), démarré et
        # connecté par Application : le Logbook ne se connecte plus jamais
        # lui-même au port série, il ne fait que lire cette instance
        # unique. Si aucun service n'est fourni (lancement isolé via
        # apps/logbook/main.py), le Logbook reste utilisable sans CAT,
        # comme avant.
        self.radio = radio_service

        # Dernières valeurs reçues du CAT, conservées pour de futures
        # évolutions. Aucun affichage ne s'appuie dessus à ce stade.
        self.radio_frequency = None
        self.radio_mode = None
        self.radio_ptt = False
        self.radio_connected = False

        self.ui = LogbookUI()
        self.ui.table.setModel(self.model)
        self.content_layout.addWidget(self.ui)

        self.ui.add_button.clicked.connect(self.new_qso)
        self.ui.search_button.clicked.connect(self.search_qso)
        self.ui.delete_button.clicked.connect(self.delete_qso)
        self.ui.import_button.clicked.connect(self.import_adif)
        self.ui.export_button.clicked.connect(self.export_adif)

        self.load_logbook()

        if self.radio is not None:
            self.radio.updated.connect(self.update_radio)
            self.radio.connectionChanged.connect(self.on_cat_connection_changed)

            self.radio_connected = self.radio.connected
            self.update_radio()

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

    def update_radio(self):
        """
        Reçoit fréquence/mode/PTT depuis le RadioService partagé et
        les conserve pour de futures évolutions. N'affiche rien à ce
        stade.
        """

        if self.radio is None:
            return

        self.radio_frequency = self.radio.frequency
        self.radio_mode = self.radio.mode
        self.radio_ptt = self.radio.status.ptt

    def on_cat_connection_changed(self, connected: bool):
        """
        Reçoit l'état de connexion CAT depuis le RadioService partagé
        et le conserve pour de futures évolutions. N'affiche rien à
        ce stade.
        """

        self.radio_connected = connected

        if connected:
            self.update_radio()

    def closeEvent(self, event):
        self.repository.close()
        super().closeEvent(event)
