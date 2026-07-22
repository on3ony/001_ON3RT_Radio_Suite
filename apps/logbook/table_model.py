"""
ON3RT Radio Suite
Module Logbook
Modèle Qt pour l'affichage des QSOs.
"""

from PySide6.QtCore import QAbstractTableModel
from PySide6.QtCore import QModelIndex
from PySide6.QtCore import Qt

from apps.logbook.models import QSO


class LogbookTableModel(QAbstractTableModel):

    HEADERS = [
        "Date",
        "Heure",
        "Indicatif",
        "Bande",
        "Fréquence",
        "Mode",
        "RST TX",
        "RST RX",
        "Nom",
        "QTH",
        "Pays",
        "Logiciel",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[QSO] = []

    def set_qsos(self, qsos: list[QSO]) -> None:
        self.beginResetModel()
        self._rows = list(qsos)
        self.endResetModel()

    def qso(self, row: int) -> QSO:
        return self._rows[row]

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            return self.HEADERS[section]

        return section + 1

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role != Qt.DisplayRole:
            return None

        qso = self._rows[index.row()]
        column = index.column()

        match column:
            case 0:
                return qso.qso_date
            case 1:
                return qso.time_on
            case 2:
                return qso.callsign
            case 3:
                return qso.band
            case 4:
                return f"{qso.frequency:,}".replace(",", " ")
            case 5:
                return qso.mode
            case 6:
                return qso.rst_sent
            case 7:
                return qso.rst_recv
            case 8:
                return qso.name
            case 9:
                return qso.qth
            case 10:
                return qso.country
            case 11:
                return qso.software

        return None