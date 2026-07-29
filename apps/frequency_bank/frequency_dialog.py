"""
ON3RT Radio Suite
Module Banque de fréquences
Formulaire d'ajout/édition d'une fréquence.

La liste des bandes est construite depuis BandManager
(libraries/radio/band_manager.py), seule référence des bandes de
toute la Suite — lu ici en lecture seule, sans aucune modification de
ce fichier.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from libraries.radio.band_manager import BandManager


class FrequencyDialog(QDialog):

    MODES = [
        "AM", "FM", "NFM", "WFM", "SSB", "LSB", "USB", "CW",
        "RTTY", "PSK31", "PSK63", "FT8", "FT4", "JT65", "JT9", "JS8",
        "WSPR", "SSTV", "FAX", "DMR", "D-STAR", "C4FM", "FreeDV", "M17", "Autre",
    ]

    CATEGORIES = [
        "HF", "VHF", "UHF", "SHF", "Digital", "Phone", "Image", "Analogique",
        "Répéteur", "Satellite", "Aviation", "Marine", "PMR", "NOAA", "Personnel",
    ]

    def __init__(self, frequency=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Fréquence")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # ----- Fréquence -----
        form.addRow(QLabel("<b>Fréquence</b>"))

        self.frequency = QDoubleSpinBox()
        self.frequency.setDecimals(6)
        self.frequency.setRange(0.000001, 100000.000000)
        self.frequency.setSingleStep(0.001)
        self.frequency.setSuffix(" MHz")
        form.addRow("Fréquence", self.frequency)

        # ----- Classification -----
        form.addRow(QLabel("<b>Classification</b>"))

        self.band = QComboBox()
        self.band.addItems([b.name for b in BandManager.BANDS])
        form.addRow("Bande", self.band)

        self.mode = QComboBox()
        self.mode.addItems(self.MODES)
        form.addRow("Mode", self.mode)

        self.category = QComboBox()
        self.category.addItems(self.CATEGORIES)
        form.addRow("Catégorie", self.category)

        # ----- Paramètres radio -----
        form.addRow(QLabel("<b>Paramètres radio</b>"))

        self.step = QSpinBox()
        self.step.setRange(0, 1_000_000)
        self.step.setSuffix(" Hz")
        form.addRow("Pas", self.step)

        self.modulation = QLineEdit()
        form.addRow("Modulation", self.modulation)

        self.service = QLineEdit()
        form.addRow("Service", self.service)

        # ----- Description -----
        form.addRow(QLabel("<b>Description</b>"))

        self.name = QLineEdit()
        form.addRow("Nom", self.name)

        self.description = QTextEdit()
        self.description.setFixedHeight(80)
        form.addRow("Description", self.description)

        # ----- Provenance -----
        form.addRow(QLabel("<b>Provenance</b>"))

        self.country = QLineEdit()
        form.addRow("Pays", self.country)

        self.region = QLineEdit()
        form.addRow("Région", self.region)

        self.source = QLineEdit()
        form.addRow("Source", self.source)

        # ----- Options -----
        form.addRow(QLabel("<b>Options</b>"))

        self.favorite = QCheckBox("Favori")
        form.addRow(self.favorite)

        self.priority = QSpinBox()
        self.priority.setRange(0, 1000)
        form.addRow("Priorité", self.priority)

        self.active = QCheckBox("Actif")
        self.active.setChecked(True)
        form.addRow(self.active)

        self.color = QLineEdit()
        self.color.setPlaceholderText("#RRGGBB")
        form.addRow("Couleur", self.color)

        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        if frequency is not None:
            self.set_frequency(frequency)

    def set_frequency(self, frequency):
        self.frequency.setValue(float(frequency.frequency))

        index = self.band.findText(frequency.band)
        if index >= 0:
            self.band.setCurrentIndex(index)

        index = self.mode.findText(frequency.mode)
        if index >= 0:
            self.mode.setCurrentIndex(index)

        index = self.category.findText(frequency.category)
        if index >= 0:
            self.category.setCurrentIndex(index)

        self.step.setValue(int(frequency.step))
        self.modulation.setText(frequency.modulation)
        self.service.setText(frequency.service)

        self.name.setText(frequency.name)
        self.description.setPlainText(frequency.description)

        self.country.setText(frequency.country)
        self.region.setText(frequency.region)
        self.source.setText(frequency.source)

        self.favorite.setChecked(bool(frequency.favorite))
        self.priority.setValue(int(frequency.priority))
        self.active.setChecked(bool(frequency.active))
        self.color.setText(frequency.color)

    def get_data(self) -> dict:
        return {
            "frequency": self.frequency.value(),
            "band": self.band.currentText(),
            "mode": self.mode.currentText(),
            "category": self.category.currentText(),
            "step": self.step.value(),
            "modulation": self.modulation.text().strip(),
            "service": self.service.text().strip(),
            "name": self.name.text().strip(),
            "description": self.description.toPlainText().strip(),
            "country": self.country.text().strip(),
            "region": self.region.text().strip(),
            "source": self.source.text().strip(),
            "favorite": self.favorite.isChecked(),
            "priority": self.priority.value(),
            "active": self.active.isChecked(),
            "color": self.color.text().strip(),
        }


if __name__ == "__main__":
    app = QApplication([])
    dlg = FrequencyDialog()
    if dlg.exec():
        print(dlg.get_data())
    app.exec()
