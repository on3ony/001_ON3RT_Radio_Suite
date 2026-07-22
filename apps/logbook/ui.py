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

        filter_layout = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "Recherche (Indicatif, Nom, QTH...)"
        )

        self.search_button = QPushButton("Rechercher")
        self.add_button = QPushButton("Nouveau QSO")

        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(self.search_button)
        filter_layout.addWidget(self.add_button)

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

        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        main_layout.addWidget(title)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.table)