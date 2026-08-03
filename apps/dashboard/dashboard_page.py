#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Page
=========================================================
Description :
    Page "Dashboard" de la fenêtre principale : assemble les
    panneaux réels déjà validés (Radio/CAT, Logbook, Activité
    par bande) avec les cartes météo/propagation/DX Cluster/
    WSJT-X (données temporaires ou messages honnêtes tant que
    ces modules ne sont pas connectés).

    Repris de 001_ON3RT_live/dashboard.py (grille + logique),
    sans l'en-tête ni l'horloge : ceux-ci sont désormais fournis
    par le SuiteHeader commun à toute la suite.

    Ne construit plus son propre LiveService : le reçoit en
    paramètre, construit une seule fois par Application
    (core/application.py) à partir des mêmes services partagés
    (dxcluster_service/weather_service/propagation_service) —
    afin qu'un futur service de diffusion réseau (LiveServer)
    puisse s'abonner à exactement le même état que celui affiché
    ici, sans sondages dupliqués. Si aucun n'est fourni (usage
    isolé, tests), une instance par défaut est construite (mêmes
    sources qu'avant : CAT + Logbook uniquement, sans DX
    Cluster/météo/propagation).
=========================================================
"""

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from apps.dashboard.data_sources import LocalFileLiveDataSource, LogbookLiveDataSource
from apps.dashboard.live_service import LiveService
from apps.dashboard.map_layers.grayline_layer import GraylineLayer, GraylineStyle
from apps.dashboard.map_layers.station_layer import StationLayer
from apps.dashboard.map_layers.world_outline_layer import WorldOutlineLayer
from apps.dashboard.panels.radio_panel import RadioPanel
from apps.dashboard.panels.band_activity_panel import BandActivityPanel
from apps.dashboard.panels.dxcluster_panel import DXClusterPanel
from apps.dashboard.panels.logbook_panel import LogbookPanel
from apps.dashboard.panels.map_panel import MapPanel
from apps.dashboard.panels.propagation_panel import PropagationPanel
from apps.dashboard.panels.weather_panel import WeatherPanel

# Style local à cette page : reproduit les cartes cyan/navy déjà
# validées dans 001_ON3RT_live, sans affecter le reste de la suite.
# QLabel hérite de QFrame en Qt : sans la règle QLabel{border:none},
# la bordure des cartes se propagerait à chaque texte (bug identifié
# et corrigé lors de la phase QA de ON3RT Live).
_PAGE_STYLE = """
    QFrame{
        background:#112743;
        border:2px solid #00cfff;
        border-radius:12px;
    }

    QLabel{
        color:white;
        background:transparent;
        border:none;
    }
"""


class DashboardPage(QWidget):
    """Page Dashboard : état de la station en temps réel."""

    def __init__(self, live_service=None, station_service=None, settings_service=None, parent=None):
        super().__init__(parent)

        # station_service : reçu depuis Application (comme live_service
        # ci-dessous), pour le panneau CARTE (MapPanel) -- la position
        # de la station est une donnée statique de configuration,
        # jamais une clé de l'état partagé LiveService (voir docstring
        # de apps/dashboard/map_layers/station_layer.py). Si absent
        # (usage isolé, tests), une instance par défaut est construite
        # (station non configurée -- MapPanel n'affiche alors aucun
        # marqueur de station, voir StationLayer).
        if station_service is None:
            from libraries.station.station_service import StationService
            station_service = StationService()

        self.station_service = station_service

        # live_service : reçu depuis Application (voir docstring plus
        # haut), pour partager exactement le même état que celui d'un
        # éventuel futur LiveServer. Si absent (usage isolé, tests), on
        # retombe sur une instance par défaut équivalente au
        # comportement historique de cette page seule : CAT + Logbook,
        # sans DX Cluster/météo/propagation.
        if live_service is None:
            live_service = LiveService(
                source=[LocalFileLiveDataSource(), LogbookLiveDataSource()],
                parent=self,
            )

        self.live_service = live_service

        # settings_service : reçu depuis Application (comme les deux
        # services ci-dessus), pour le style de GraylineLayer
        # (section map.grayline, voir apps/settings/settings_service.py)
        # -- seule cette section est lue ici, aucune autre. Si absent
        # (usage isolé, tests, ON3RT Live Viewer -- voir apps/live_viewer/
        # window.py), une instance par défaut est construite, mêmes
        # valeurs par défaut que GraylineStyle() tant que
        # config/settings.json n'a jamais été modifié depuis l'écran
        # Settings.
        if settings_service is None:
            from apps.settings.settings_service import SettingsService
            settings_service = SettingsService()

        self.settings_service = settings_service

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        grid = QGridLayout()
        grid.setSpacing(15)

        # Style de GraylineLayer construit depuis settings_service.map
        # ["grayline"] (section ajoutée en amont de tout câblage, voir
        # apps/settings/settings_service.py) -- tuples reconvertis
        # depuis les listes JSON (dataclass GraylineStyle, jamais
        # importée par SettingsService). Tant que config/settings.json
        # garde ses valeurs par défaut, ce style est strictement
        # identique à GraylineStyle().
        grayline_settings = self.settings_service.map["grayline"]
        grayline_style = GraylineStyle(
            line_color_rgb=tuple(grayline_settings["line_color_rgb"]),
            line_opacity=grayline_settings["line_opacity"],
            line_width_px=grayline_settings["line_width_px"],
            night_fill_color_rgb=tuple(grayline_settings["night_fill_color_rgb"]),
            night_fill_opacity=grayline_settings["night_fill_opacity"],
        )

        # Ordre explicite des couches de la Carte (fixe l'empilement
        # visuel, voir apps/dashboard/panels/map_panel.py) : fond
        # (océan/continents), puis grayline par-dessus, puis le
        # marqueur de la station tout en haut, jamais masqué par la
        # ligne du terminateur.
        map_layers = [
            WorldOutlineLayer(),
            GraylineLayer(style=grayline_style),
            StationLayer(self.station_service),
        ]

        grid.addWidget(RadioPanel(self.live_service), 0, 0)
        grid.addWidget(
            MapPanel(self.station_service, live_service=self.live_service, layers=map_layers), 0, 1
        )
        grid.addWidget(DXClusterPanel(self.live_service), 0, 2)

        grid.addWidget(PropagationPanel(self.live_service), 1, 0)
        grid.addWidget(LogbookPanel(self.live_service), 1, 1)
        grid.addWidget(self._placeholder("🎙 WSJT-X", "WSJT-X non connecté", "#ffb454"), 1, 2)

        grid.addWidget(WeatherPanel(self.live_service), 2, 0)
        grid.addWidget(BandActivityPanel(self.live_service), 2, 1)
        grid.addWidget(self._placeholder("💬 MESSAGES"), 2, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        grid.setRowStretch(0, 2)
        grid.setRowStretch(1, 2)
        grid.setRowStretch(2, 1)

        container = QWidget()
        container.setStyleSheet(_PAGE_STYLE)
        container.setLayout(grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        scroll.setWidget(container)

        outer.addWidget(scroll)

    # -----------------------------------------------------

    @staticmethod
    def _placeholder(title, text="En construction", text_color="#9beeff"):

        frame = QFrame()
        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(frame)

        lab = QLabel(title)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        lab.setFont(font)
        lab.setStyleSheet("color:#00dfff;")
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)

        txt = QLabel(text)
        txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt.setStyleSheet(f"color:{text_color}; font-size:13pt;")

        layout.addWidget(lab)
        layout.addStretch()
        layout.addWidget(txt)
        layout.addStretch()

        return frame
