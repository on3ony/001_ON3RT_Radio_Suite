"""
ON3RT Radio Suite
Module Logbook
"""

from libraries.ui.base_window import BaseWindow

from apps.logbook.ui import LogbookUI
from apps.logbook.repository import LogbookRepository
from apps.logbook.table_model import LogbookTableModel


class LogbookWindow(BaseWindow):

    def __init__(self):
        super().__init__(
            title="Logbook",
            subtitle="Gestion du carnet de trafic"
        )

        self.repository = LogbookRepository()
        self.model = LogbookTableModel()

        self.ui = LogbookUI()

        #
        # Remplacement du QTableWidget par le modèle Qt
        #
        self.ui.table.setModel(self.model)

        self.content_layout.addWidget(self.ui)

        self.load_logbook()

        self.statusBar().showMessage("Logbook prêt")

    def load_logbook(self):
        qsos = self.repository.get_all()
        self.model.set_qsos(qsos)

        self.statusBar().showMessage(
            f"{len(qsos)} QSO(s) chargé(s)"
        )

    def closeEvent(self, event):
        self.repository.close()
        super().closeEvent(event)