"""
ON3RT Radio Suite
Module Banque de fréquences
Modèle Qt pour l'affichage des fréquences.
"""

from PySide6.QtCore import QAbstractTableModel
from PySide6.QtCore import QModelIndex
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from libraries.ui import colors

from apps.frequency_bank.models import Frequency


class FrequencyTableModel(QAbstractTableModel):

    HEADERS = [
        "Fréquence",
        "Bande",
        "Mode",
        "Modulation",
        "Catégorie",
        "Nom",
        "Description",
        "Favori",
        "Priorité",
        "Actif",
    ]

    _SORT_KEYS = {
        0: lambda f: f.frequency,
        1: lambda f: f.band,
        2: lambda f: f.mode,
        3: lambda f: f.modulation,
        4: lambda f: f.category,
        5: lambda f: f.name,
        6: lambda f: f.description,
        7: lambda f: f.favorite,
        8: lambda f: f.priority,
        9: lambda f: f.active,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[Frequency] = []

    def set_frequencies(self, frequencies: list[Frequency]) -> None:
        self.beginResetModel()
        self._rows = list(frequencies)
        self.endResetModel()

    def frequency(self, row: int) -> Frequency:
        return self._rows[row]

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        key_func = self._SORT_KEYS.get(column)

        if key_func is None:
            return

        self.layoutAboutToBeChanged.emit()

        old_persistent_indexes = self.persistentIndexList()
        old_order = list(self._rows)

        self._rows.sort(key=key_func, reverse=(order == Qt.SortOrder.DescendingOrder))

        new_persistent_indexes = []
        for index in old_persistent_indexes:
            row_object = old_order[index.row()]
            new_row = next(i for i, r in enumerate(self._rows) if r is row_object)
            new_persistent_indexes.append(self.index(new_row, index.column()))

        self.changePersistentIndexList(old_persistent_indexes, new_persistent_indexes)
        self.layoutChanged.emit()

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

        f = self._rows[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            match column:
                case 0:
                    return f"{f.frequency:.6f}"
                case 1:
                    return f.band
                case 2:
                    return f.mode
                case 3:
                    return f.modulation
                case 4:
                    return f.category
                case 5:
                    return f.name
                case 6:
                    return f.description
                case 7:
                    return "★" if f.favorite else ""
                case 8:
                    return f.priority
                case 9:
                    return "Oui" if f.active else "Non"
            return None

        if role == Qt.ForegroundRole and column == 7 and f.favorite:
            return QColor(colors.ACCENT_CYAN)

        if role == Qt.TextAlignmentRole and column == 7:
            return Qt.AlignmentFlag.AlignCenter

        return None
