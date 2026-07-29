#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Dashboard
Version : 2.0.0
Auteur : ON3RT
Description :
    Assemble les composants graphiques fournis par theme.py en
    fenêtre principale. Ne définit aucun style : couleurs, polices,
    tailles, ombres et widgets réutilisables vivent tous dans
    theme.py.
=========================================================
"""

from datetime import datetime, timezone

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QGridLayout,
    QMainWindow,
    QScrollArea,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .panels.radio_panel import RadioPanel
from .panels.band_activity_panel import BandActivityPanel
from .panels.logbook_panel import LogbookPanel
from .panels.weather_panel import WeatherPanel
from .services.data_sources import LocalFileLiveDataSource, LogbookLiveDataSource
from .services.live_service import LiveService

VERSION_LABEL = "v2.0.0"


class DashboardWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("ON3RT LIVE")
        self.setMinimumSize(1100, 650)
        self._apply_initial_geometry()

        self.setStyleSheet(theme.main_window_qss())

        self.live_service = LiveService(
            source=[LocalFileLiveDataSource(), LogbookLiveDataSource()],
            parent=self,
        )

        self.build_ui()

        self.timer = QTimer()

        self.timer.timeout.connect(self.update_clock)

        self.timer.start(1000)

        self.update_clock()

    # -----------------------------------------------------

    def _apply_initial_geometry(self):

        screen = self.screen() or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()

        margin = 60

        width = min(1600, avail.width() - margin)
        height = min(900, avail.height() - margin)

        width = max(width, self.minimumWidth())
        height = max(height, self.minimumHeight())

        self.resize(width, height)

        x = avail.x() + (avail.width() - width) // 2
        y = avail.y() + (avail.height() - height) // 2

        self.move(x, y)

    # -----------------------------------------------------

    def build_ui(self):

        central = QWidget()

        self.setCentralWidget(central)

        root = QVBoxLayout(central)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(0)

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

        root.addWidget(self._build_header())

        self.live_service.state_changed.connect(self.update_connection_state)
        self.update_connection_state(self.live_service.state())

        # -------------------------------------------------
        # CORPS (grille de panneaux)
        # -------------------------------------------------

        body = QWidget()

        body_layout = QVBoxLayout(body)

        body_layout.setContentsMargins(
            theme.SPACING_LG, theme.SPACING_LG, theme.SPACING_LG, theme.SPACING_LG
        )

        body_layout.setSpacing(theme.SPACING_LG)

        root.addWidget(body, 1)

        # -------------------------------------------------
        # GRID
        # -------------------------------------------------

        grid = QGridLayout()

        grid.setSpacing(theme.SPACING_MD)

        grid.addWidget(RadioPanel(self.live_service),0,0)

        grid.addWidget(theme.build_info_card("🌍 CARTE", pattern=True),0,1)

        grid.addWidget(theme.build_info_card(
            "📡 DX CLUSTER", "DX Cluster déconnecté", theme.STATE_AMBER,
            columns=[("HEURE", 1), ("INDICATIF", 2), ("FRÉQUENCE", 1), ("MODE", 1)],
        ),0,2)

        grid.addWidget(theme.build_info_card("🌦 PROPAGATION"),1,0)

        grid.addWidget(LogbookPanel(self.live_service),1,1)

        grid.addWidget(theme.build_info_card(
            "🎙 WSJT-X", "WSJT-X non connecté", theme.STATE_AMBER,
            columns=[("HEURE", 1), ("INDICATIF", 2), ("REPORT", 1), ("MODE", 1)],
        ),1,2)

        grid.addWidget(WeatherPanel(),2,0)

        grid.addWidget(BandActivityPanel(self.live_service),2,1)

        grid.addWidget(theme.build_info_card("💬 MESSAGES"),2,2)

        grid.setColumnStretch(0,1)

        grid.setColumnStretch(1,2)

        grid.setColumnStretch(2,1)

        grid.setRowStretch(0,2)

        grid.setRowStretch(1,2)

        grid.setRowStretch(2,1)

        grid_container = QWidget()
        grid_container.setLayout(grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grid_container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        body_layout.addWidget(scroll)

        # -------------------------------------------------

        status = QStatusBar()

        status.showMessage("ON3RT LIVE 2.0")

        self.setStatusBar(status)

    # -----------------------------------------------------
    # En-tête
    # -----------------------------------------------------

    def _build_header(self):

        header, layout = theme.make_header_frame()

        # ---- Logo + signature -------------------------------------------

        layout.addWidget(theme.make_header_logo())

        layout.addSpacing(theme.SPACING_MD)

        layout.addWidget(theme.make_brand_title("LIVE"))

        layout.addStretch()

        # ---- Voyants réservés, regroupés (futures intégrations) -----------

        layout.addWidget(theme.make_status_group([
            ("CAT", "inactive"),
            ("DX CLUSTER", "inactive"),
            ("WSJT-X", "inactive"),
            ("INTERNET", "inactive"),
        ]))

        layout.addWidget(theme.make_separator())

        # ---- État radio -----------------------------------------------------

        self.state = theme.make_state_pill(active=False)

        layout.addWidget(self.state)

        layout.addWidget(theme.make_separator())

        # ---- Horloge UTC ----------------------------------------------------

        self.utc = theme.make_clock_label()

        layout.addWidget(self.utc)

        layout.addWidget(theme.make_separator())

        # ---- Version ----------------------------------------------------

        layout.addWidget(theme.make_caption_label(VERSION_LABEL))

        return header

    # -----------------------------------------------------

    def update_connection_state(self,state):

        connected = bool(state.get("connected", False)) if isinstance(state,dict) else False

        self.state.setText("🟢 RADIO ONLINE" if connected else "🔴 RADIO OFFLINE")

        self.state.setStyleSheet(theme.state_pill_qss(connected))

    # -----------------------------------------------------

    def update_clock(self):

        now = datetime.now(timezone.utc)

        self.utc.setText(

            now.strftime(

                "UTC  %d/%m/%Y   %H:%M:%S"

            )

        )
