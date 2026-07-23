"""
ON3RT Radio Suite
Module Logbook
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)


class LogbookUI(QWidget):

    def __init__(self):
        super().__init__()

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        title = QLabel("ON3RT Radio Suite - Logbook")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        toolbar = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "Recherche (Indicatif, Nom, QTH...)"
        )

        self.search_button = QPushButton("Rechercher")

        self.add_button = QPushButton("Nouveau QSO")

        self.import_button = QPushButton("Importer ADIF")

        self.export_button = QPushButton("Exporter ADIF")

        self.edit_button = QPushButton("Modifier")

        self.delete_button = QPushButton("Supprimer")

        toolbar.addWidget(self.search_edit, 1)
        toolbar.addWidget(self.search_button)
        toolbar.addWidget(self.add_button)
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.export_button)
        toolbar.addWidget(self.edit_button)
        toolbar.addWidget(self.delete_button)

        self.table = QTableView()

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.table.setAlternatingRowColors(True)

        self.table.setSortingEnabled(True)

        self.table.verticalHeader().setVisible(False)

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        header = self.table.horizontalHeader()

        header.setStretchLastSection(True)

        header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        main_layout.addWidget(title)
        main_layout.addLayout(toolbar)
        main_layout.addWidget(self.table)
