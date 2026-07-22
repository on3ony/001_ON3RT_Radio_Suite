"""
ON3RT Radio Suite
Module Logbook
"""

from libraries.ui.base_window import BaseWindow
from libraries.cat.cat_controller import CATController

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

        self.load_logbook()

    def load_logbook(self):
        qsos = self.repository.get_all()
        self.model.set_qsos(qsos)

        self.statusBar().showMessage(
            f"{len(qsos)} QSO(s)"
        )

    def _frequency_to_band(self, frequency: int) -> str:

        bands = [
            (1800000, 2000000, "160m"),
            (3500000, 4000000, "80m"),
            (5351000, 5367000, "60m"),
            (7000000, 7300000, "40m"),
            (10100000, 10150000, "30m"),
            (14000000, 14350000, "20m"),
            (18068000, 18168000, "17m"),
            (21000000, 21450000, "15m"),
            (24890000, 24990000, "12m"),
            (28000000, 29700000, "10m"),
            (50000000, 52000000, "6m"),
            (70000000, 70500000, "4m"),
            (144000000, 146000000, "2m"),
            (430000000, 440000000, "70cm"),
            (1240000000, 1300000000, "23cm"),
        ]

        for start, end, band in bands:
            if start <= frequency <= end:
                return band

        return ""

    def new_qso(self):

        qso = QSO()

        try:

            if self.cat.connect():

                frequency = self.cat.read_frequency()
                mode = self.cat.read_mode()

                self.cat.disconnect()

                if frequency:
                    qso.frequency = frequency
                    qso.band = self._frequency_to_band(frequency)

                if mode:
                    qso.mode = mode

        except Exception:
            pass

        dialog = QSODialog(self, qso)

        if dialog.exec():

            qso = dialog.get_qso()

            self.repository.add_qso(qso)

            self.load_logbook()

    def closeEvent(self, event):
        self.repository.close()
        super().closeEvent(event)