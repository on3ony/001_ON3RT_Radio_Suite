"""
ON3RT Radio Suite
Module Banque de fréquences
Fenêtre du module.
"""

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
)

from libraries.ui.base_window import BaseWindow

from apps.frequency_bank.frequency_dialog import FrequencyDialog
from apps.frequency_bank.frequency_service import FrequencyService
from apps.frequency_bank.models import Frequency
from apps.frequency_bank.table_model import FrequencyTableModel


class FrequencyBankWindow(BaseWindow):

    def __init__(self, frequency_service: FrequencyService = None):
        super().__init__(
            title="Banque de fréquences",
            subtitle="Fréquences de référence, plan de bandes, favoris",
        )

        # FrequencyService est un service partagé de la Suite (injecté
        # depuis core/application.py). Si aucun n'est fourni (lancement
        # autonome), la fenêtre crée le sien et en reste responsable —
        # elle seule le fermera alors à la fermeture (voir closeEvent).
        self._owns_service = frequency_service is None
        self.service = frequency_service or FrequencyService()

        self.model = FrequencyTableModel()

        self._build_content()

        self.add_button.clicked.connect(self.new_frequency)
        self.edit_button.clicked.connect(self.edit_frequency)
        self.delete_button.clicked.connect(self.delete_frequency)
        self.search_button.clicked.connect(self.search_frequency)
        self.refresh_button.clicked.connect(self.load_frequencies)
        self.table.doubleClicked.connect(self.edit_frequency)

        self.load_frequencies()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_content(self):
        toolbar = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Recherche (nom, description, bande, mode...)")

        self.search_button = QPushButton("Rechercher")
        self.add_button = QPushButton("Ajouter")
        self.edit_button = QPushButton("Modifier")
        self.delete_button = QPushButton("Supprimer")
        self.refresh_button = QPushButton("Actualiser")

        toolbar.addWidget(self.search_edit, 1)
        toolbar.addWidget(self.search_button)
        toolbar.addWidget(self.add_button)
        toolbar.addWidget(self.edit_button)
        toolbar.addWidget(self.delete_button)
        toolbar.addWidget(self.refresh_button)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.content_layout.addLayout(toolbar)
        self.content_layout.addWidget(self.table)

    # ------------------------------------------------------------------
    # Chargement / recherche
    # ------------------------------------------------------------------

    def load_frequencies(self):
        frequencies = self.service.get_all()
        self.model.set_frequencies(frequencies)
        self.statusBar().showMessage(f"{len(frequencies)} fréquence(s)")

    def search_frequency(self):
        text = self.search_edit.text().strip()

        if not text:
            self.load_frequencies()
            return

        results = self.service.search(text)
        self.model.set_frequencies(results)
        self.statusBar().showMessage(f"{len(results)} résultat(s)")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def new_frequency(self):
        dialog = FrequencyDialog(parent=self)

        if dialog.exec():
            frequency = self._build_frequency(dialog.get_data())
            self.service.add(frequency)
            self.load_frequencies()

    def edit_frequency(self):
        frequency = self._selected_frequency()

        if frequency is None:
            return

        dialog = FrequencyDialog(frequency=frequency, parent=self)

        if dialog.exec():
            updated = self._build_frequency(dialog.get_data(), existing=frequency)
            self.service.update(updated)
            self.load_frequencies()

    def delete_frequency(self):
        frequency = self._selected_frequency()

        if frequency is None:
            return

        answer = QMessageBox.question(
            self,
            "Supprimer",
            f"Supprimer la fréquence {frequency.name or frequency.frequency} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.service.delete(frequency.id)
        self.load_frequencies()

    def _selected_frequency(self):
        index = self.table.currentIndex()

        if not index.isValid():
            return None

        return self.model.frequency(index.row())

    def _build_frequency(self, data: dict, existing: Frequency = None) -> Frequency:
        frequency = Frequency()

        if existing is not None:
            frequency.id = existing.id
            frequency.start_frequency = existing.start_frequency
            frequency.end_frequency = existing.end_frequency
        else:
            frequency.start_frequency = data["frequency"]
            frequency.end_frequency = data["frequency"]

        frequency.frequency = data["frequency"]
        frequency.band = data["band"]
        frequency.mode = data["mode"]
        frequency.category = data["category"]
        frequency.step = data["step"]
        frequency.modulation = data["modulation"]
        frequency.service = data["service"]
        frequency.name = data["name"]
        frequency.description = data["description"]
        frequency.country = data["country"]
        frequency.region = data["region"]
        frequency.source = data["source"]
        frequency.favorite = data["favorite"]
        frequency.priority = data["priority"]
        frequency.active = data["active"]
        frequency.color = data["color"]

        return frequency

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self._owns_service:
            self.service.close()
        super().closeEvent(event)
