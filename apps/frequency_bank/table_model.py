"""
ON3RT Radio Suite
Module Banque de fréquences
Modèle Qt pour l'affichage des fréquences.
"""

from PySide6.QtCore import QAbstractTableModel
from PySide6.QtCore import QModelIndex
from PySide6.QtCore import Qt

from apps.frequency_bank.models import Frequency


class FrequencyTableModel(QAbstractTableModel):

    HEADERS = [
        "Fréquence",
        "Bande",
        "Mode",
        "Catégorie",
        "Nom",
        "Description",
        "Favori",
        "Priorité",
        "Actif",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[Frequency] = []

    def set_frequencies(self, frequencies: list[Frequency]) -> None:
        self.beginResetModel()
        self._rows = list(frequencies)
        self.endResetModel()

    def frequency(self, row: int) -> Frequency:
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

        f = self._rows[index.row()]
        column = index.column()

        match column:
            case 0:
                return f"{f.frequency:.6f}"
            case 1:
                return f.band
            case 2:
                return f.mode
            case 3:
                return f.category
            case 4:
                return f.name
            case 5:
                return f.description
            case 6:
                return "Oui" if f.favorite else "Non"
            case 7:
                return f.priority
            case 8:
                return "Oui" if f.active else "Non"

        return None
