"""
ON3RT Radio Suite
Module DX Cluster
Modèle Qt pour l'affichage des spots.

Chaque ligne est un dict conforme au contrat de spot figé de
DXClusterService (libraries/dxcluster/dxcluster_service.py) — ce
modèle ne réinterprète jamais un champ, il l'affiche tel quel ou
l'omet s'il vaut None (jamais de donnée inventée).
"""

from PySide6.QtCore import QAbstractTableModel
from PySide6.QtCore import QModelIndex
from PySide6.QtCore import Qt


class DXClusterTableModel(QAbstractTableModel):

    HEADERS = [
        "Heure",
        "Fréquence (kHz)",
        "Bande",
        "Indicatif DX",
        "Spotter",
        "Commentaire",
    ]

    _SORT_KEYS = {
        0: lambda s: s.get("time_utc") or "",
        1: lambda s: s.get("frequency_khz") or 0.0,
        2: lambda s: s.get("band") or "",
        3: lambda s: s.get("dx_callsign") or "",
        4: lambda s: s.get("spotter") or "",
        5: lambda s: s.get("comment") or "",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []

    def set_spots(self, spots: list[dict]) -> None:
        self.beginResetModel()
        self._rows = list(spots)
        self.endResetModel()

    def add_spot(self, spot: dict) -> None:
        row = len(self._rows)
        self.beginInsertRows(QModelIndex(), row, row)
        self._rows.append(spot)
        self.endInsertRows()

    def spot(self, row: int) -> dict:
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

        if role != Qt.DisplayRole:
            return None

        spot = self._rows[index.row()]
        column = index.column()

        match column:
            case 0:
                return spot.get("time_utc") or "--"
            case 1:
                frequency_khz = spot.get("frequency_khz")
                return f"{frequency_khz:.1f}" if isinstance(frequency_khz, (int, float)) else "--"
            case 2:
                return spot.get("band") or "--"
            case 3:
                return spot.get("dx_callsign") or "--"
            case 4:
                return spot.get("spotter") or "--"
            case 5:
                return spot.get("comment") or ""

        return None
