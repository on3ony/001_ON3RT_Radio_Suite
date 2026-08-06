"""
ON3RT Radio Suite
apps/settings/window.py

Fenêtre du module Settings — assemble les six panneaux (Station,
Radio, Réseau, Services, CW, CAT Sharing) dans un QTabWidget. Hérite de BaseWindow,
comme Scanner/DX Cluster/Frequency Bank/Logbook/Radio Control, pour le
même socle visuel (logo, titre, barre d'état) que le reste de la
suite.

Aucune logique métier ici : cette fenêtre construit les panneaux, les
place dans des onglets, et ne fait rien d'autre. Chaque panneau gère
seul la lecture/écriture de son propre domaine (StationService,
RadioService, ou SettingsService) — voir apps/settings/panels/. Les
services sont reçus en injection, jamais créés ici, comme partout
ailleurs dans la suite.
"""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget

from libraries.ui.base_window import BaseWindow

from apps.settings.panels.station_panel import StationPanel
from apps.settings.panels.radio_panel import RadioPanel
from apps.settings.panels.network_panel import NetworkPanel
from apps.settings.panels.services_panel import ServicesPanel
from apps.settings.panels.cw_panel import CWPanel
from apps.settings.panels.cat_sharing_panel import CatSharingPanel


class SettingsWindow(BaseWindow):

    def __init__(self, station_service, settings_service, radio_service=None, parent=None):
        super().__init__(
            title="Settings",
            subtitle="Configuration de la station",
        )

        self.station_service = station_service
        self.settings_service = settings_service
        self.radio_service = radio_service

        self._build_tabs()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_tabs(self):
        self.tabs = QTabWidget()

        self.station_panel = StationPanel(self.station_service)
        self.radio_panel = RadioPanel(self.radio_service)
        self.network_panel = NetworkPanel(self.settings_service)
        self.services_panel = ServicesPanel(self.settings_service)
        self.cw_panel = CWPanel(self.settings_service)
        self.cat_sharing_panel = CatSharingPanel(self.settings_service)

        self.tabs.addTab(self.station_panel, "Station")
        self.tabs.addTab(self.radio_panel, "Radio")
        self.tabs.addTab(self.network_panel, "Réseau")
        self.tabs.addTab(self.services_panel, "Services")
        self.tabs.addTab(self.cw_panel, "CW")
        self.tabs.addTab(self.cat_sharing_panel, "CAT Sharing")

        self.content_layout.addWidget(self.tabs)
