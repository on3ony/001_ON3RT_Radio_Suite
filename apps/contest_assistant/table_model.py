"""
ON3RT Radio Suite
apps/contest_assistant/table_model.py

Modèles Qt pour l'affichage des messages et de l'historique en
tableau (QTableView) — même présentation que DX Cluster/Logbook
(apps/dxcluster/table_model.py), pour la même lisibilité en-tête
colonnes + lignes de hauteur fixe.

Purement des vues sur des données déjà en mémoire (MessageTemplate,
SentMessage) : aucune logique métier, aucun accès à
ContestMessageService.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from apps.contest_assistant.models import MessageTemplate, SentMessage


class MessageTemplateTableModel(QAbstractTableModel):

    HEADERS = ["Libellé", "Message"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._templates: list[MessageTemplate] = []
        self._language = "FR"

    def set_templates(self, templates: list[MessageTemplate]) -> None:
        self.beginResetModel()
        self._templates = list(templates)
        self.endResetModel()

    def set_language(self, language: str) -> None:
        if language == self._language:
            return

        self._language = language

        if self._templates:
            top_left = self.index(0, 1)
            bottom_right = self.index(len(self._templates) - 1, 1)
            self.dataChanged.emit(top_left, bottom_right)

    def template_at(self, row: int) -> MessageTemplate | None:
        if 0 <= row < len(self._templates):
            return self._templates[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._templates)

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
        if not index.isValid() or role != Qt.DisplayRole:
            return None

        template = self._templates[index.row()]

        match index.column():
            case 0:
                return template.label
            case 1:
                return template.text_en if self._language == "EN" else template.text_fr

        return None


class SentMessageTableModel(QAbstractTableModel):

    HEADERS = ["Heure", "N°", "Message"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[SentMessage] = []

    def set_entries(self, entries: list[SentMessage]) -> None:
        self.beginResetModel()
        self._entries = list(entries)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._entries)

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
        if not index.isValid() or role != Qt.DisplayRole:
            return None

        entry = self._entries[index.row()]

        match index.column():
            case 0:
                return entry.timestamp
            case 1:
                return f"{entry.serial:03d}"
            case 2:
                return entry.resolved_text

        return None
