"""
ON3RT Radio Suite
Module Logbook
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
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
        self.search_edit.setPlaceholderText("Recherche (Indicatif, Nom, QTH...)")

        self.search_button = QPushButton("Rechercher")
        self.add_button = QPushButton("Nouveau QSO")

        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(self.search_button)
        filter_layout.addWidget(self.add_button)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            [
                "Date",
                "Heure",
                "Indicatif",
                "Bande",
                "Mode",
                "RST TX",
                "RST RX",
                "Nom",
                "QTH",
                "Commentaire",
            ]
        )

        self.table.horizontalHeader().setStretchLastSection(True)

        main_layout.addWidget(title)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.table)