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
from apps.dashboard.data_sources.dxcluster_source import DXClusterLiveDataSource
from apps.dashboard.data_sources.propagation_source import PropagationLiveDataSource
from apps.dashboard.data_sources.weather_source import WeatherLiveDataSource
from apps.dashboard.live_service import LiveService
from apps.dashboard.panels.radio_panel import RadioPanel
from apps.dashboard.panels.band_activity_panel import BandActivityPanel
from apps.dashboard.panels.dxcluster_panel import DXClusterPanel
from apps.dashboard.panels.logbook_panel import LogbookPanel
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

    def __init__(self, dxcluster_service=None, weather_service=None, propagation_service=None, parent=None):
        super().__init__(parent)

        sources = [LocalFileLiveDataSource(), LogbookLiveDataSource()]

        # DXClusterService / WeatherService / PropagationService
        # (services Suite partagés) : optionnels, pour que DashboardPage
        # reste utilisable sans eux (tests, lancement isolé) —
        # exactement le même principe que radio_service/station_service
        # pour les autres modules de la suite.
        if dxcluster_service is not None:
            sources.append(DXClusterLiveDataSource(dxcluster_service))

        if weather_service is not None:
            sources.append(WeatherLiveDataSource(weather_service))

        if propagation_service is not None:
            sources.append(PropagationLiveDataSource(propagation_service))

        self.live_service = LiveService(source=sources, parent=self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        grid = QGridLayout()
        grid.setSpacing(15)

        grid.addWidget(RadioPanel(self.live_service), 0, 0)
        grid.addWidget(self._placeholder("🌍 CARTE"), 0, 1)
        grid.addWidget(DXClusterPanel(self.live_service), 0, 2)

        grid.addWidget(self._placeholder("🌦 PROPAGATION"), 1, 0)
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
