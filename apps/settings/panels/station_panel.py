"""
ON3RT Radio Suite
apps/settings/panels/station_panel.py

Panneau "Station" de l'écran Settings.

StationService (libraries/station/station_service.py) est l'unique
source et l'unique destination des données de ce panneau : à la
construction, les champs sont peuplés depuis l'instance reçue ; au
clic sur "Enregistrer", les valeurs saisies sont réécrites dans cette
même instance puis persistées via StationService.save(). Ce panneau ne
lit ni n'écrit jamais config/station.json directement, et ne crée
jamais sa propre instance de StationService (reçue en injection,
comme le reste de la suite).

Seuls les 8 champs identité/position/licence de la station sont
exposés ici (indicatif, nom de l'opérateur, locator, QTH, latitude,
longitude, altitude, classe de licence) : antennas/interfaces/timezone
existent sur StationService mais ne font pas partie du périmètre de ce
panneau — ils restent inchangés sur l'instance et sont donc réécrits
tels quels par StationService.save() (aucune perte de donnée).

Classe de licence (combo_license) : ce panneau ne connaît AUCUNE règle
de privilège (quelles bandes une classe autorise, etc.) — il se
contente de lister les classes disponibles via
license_privileges.available_license_classes() (chantier "Tuile
Activité par bande") pour peupler la liste déroulante, et d'écrire
l'identifiant choisi tel quel dans StationService.license_class.
Toute logique de privilèges reste exclusivement dans
libraries/radio/license_privileges.py ; les modules consommateurs (ex.
BandActivityPanel) lisent StationService.license_class sans jamais
passer par ce panneau.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from libraries.radio.license_privileges import available_license_classes


class StationPanel(QWidget):

    def __init__(self, station_service, parent=None):
        super().__init__(parent)

        self.station_service = station_service

        self._build_ui()
        self._load_from_service()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)

        group = QGroupBox("Station")
        form = QFormLayout(group)

        self.edit_callsign = QLineEdit()
        self.edit_operator_name = QLineEdit()
        self.edit_locator = QLineEdit()
        self.edit_qth = QLineEdit()

        self.spin_latitude = QDoubleSpinBox()
        self.spin_latitude.setDecimals(6)
        self.spin_latitude.setRange(-90.0, 90.0)
        self.spin_latitude.setSuffix(" °")

        self.spin_longitude = QDoubleSpinBox()
        self.spin_longitude.setDecimals(6)
        self.spin_longitude.setRange(-180.0, 180.0)
        self.spin_longitude.setSuffix(" °")

        self.spin_altitude = QSpinBox()
        self.spin_altitude.setRange(-500, 9000)
        self.spin_altitude.setSuffix(" m")

        self.combo_license = QComboBox()
        for class_id, label in available_license_classes():
            self.combo_license.addItem(label, class_id)

        form.addRow("Indicatif", self.edit_callsign)
        form.addRow("Nom de l'opérateur", self.edit_operator_name)
        form.addRow("Locator", self.edit_locator)
        form.addRow("QTH", self.edit_qth)
        form.addRow("Latitude", self.spin_latitude)
        form.addRow("Longitude", self.spin_longitude)
        form.addRow("Altitude", self.spin_altitude)
        form.addRow("Classe de licence", self.combo_license)

        self.btn_save = QPushButton("Enregistrer")
        form.addRow(self.btn_save)

        outer.addWidget(group)
        outer.addStretch(1)

    def _connect_signals(self):
        self.btn_save.clicked.connect(self._on_save_clicked)

    # ------------------------------------------------------------------
    # StationService -> champs
    # ------------------------------------------------------------------

    def _load_from_service(self):
        self.edit_callsign.setText(self.station_service.callsign)
        self.edit_operator_name.setText(self.station_service.operator_name)
        self.edit_locator.setText(self.station_service.locator)
        self.edit_qth.setText(self.station_service.qth)

        self.spin_latitude.setValue(self.station_service.latitude or 0.0)
        self.spin_longitude.setValue(self.station_service.longitude or 0.0)
        self.spin_altitude.setValue(self.station_service.altitude or 0)

        index = self.combo_license.findData(self.station_service.license_class)
        self.combo_license.setCurrentIndex(index if index >= 0 else 0)

    # ------------------------------------------------------------------
    # Champs -> StationService
    # ------------------------------------------------------------------

    def _on_save_clicked(self):
        self.station_service.callsign = self.edit_callsign.text().strip()
        self.station_service.operator_name = self.edit_operator_name.text().strip()
        self.station_service.locator = self.edit_locator.text().strip()
        self.station_service.qth = self.edit_qth.text().strip()

        self.station_service.latitude = self.spin_latitude.value()
        self.station_service.longitude = self.spin_longitude.value()
        self.station_service.altitude = self.spin_altitude.value()

        self.station_service.license_class = self.combo_license.currentData()

        self.station_service.save()
