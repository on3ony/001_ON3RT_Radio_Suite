#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Dashboard
Version : 2.0.0
Auteur : ON3RT
=========================================================
"""

from datetime import datetime, timezone

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QMainWindow,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from panels.radio_panel import RadioPanel


class DashboardWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("ON3RT LIVE")
        self.resize(1600, 900)
        self.setMinimumSize(1400, 800)

        self.setStyleSheet("""

        QMainWindow{
            background:#081629;
        }

        QWidget{
            background:#081629;
            color:white;
            font-family:Segoe UI;
        }

        QLabel{
            color:white;
        }

        QFrame{
            background:#112743;
            border:2px solid #00cfff;
            border-radius:12px;
        }

        QStatusBar{
            background:#10233f;
            color:#9beeff;
        }

        """)

        self.build_ui()

        self.timer = QTimer()

        self.timer.timeout.connect(self.update_clock)

        self.timer.start(1000)

        self.update_clock()

    # -----------------------------------------------------

    def build_ui(self):

        central = QWidget()

        self.setCentralWidget(central)

        root = QVBoxLayout(central)

        root.setContentsMargins(15,15,15,15)

        root.setSpacing(15)

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

        header = QHBoxLayout()

        titre = QLabel("ON3RT LIVE")

        font = QFont()

        font.setPointSize(22)

        font.setBold(True)

        titre.setFont(font)

        titre.setStyleSheet("color:#00dfff;")

        header.addWidget(titre)

        header.addStretch()

        self.utc = QLabel()

        self.utc.setStyleSheet("""
            font-size:14pt;
            color:#8beeff;
        """)

        header.addWidget(self.utc)

        self.state = QLabel("🔴 RADIO OFFLINE")

        self.state.setStyleSheet("""
            color:#ff6666;
            font-size:14pt;
            font-weight:bold;
        """)

        header.addWidget(self.state)

        root.addLayout(header)

        # -------------------------------------------------
        # GRID
        # -------------------------------------------------

        grid = QGridLayout()

        grid.setSpacing(15)

        grid.addWidget(RadioPanel(),0,0)

        grid.addWidget(self.placeholder("🌍 CARTE"),0,1)

        grid.addWidget(self.placeholder("📡 DX CLUSTER"),0,2)

        grid.addWidget(self.placeholder("🌦 PROPAGATION"),1,0)

        grid.addWidget(self.placeholder("📖 LOGBOOK"),1,1)

        grid.addWidget(self.placeholder("🎙 WSJT-X"),1,2)

        grid.addWidget(self.placeholder("🛰 ROTOR"),2,0)

        grid.addWidget(self.placeholder("📈 STATISTIQUES"),2,1)

        grid.addWidget(self.placeholder("💬 MESSAGES"),2,2)

        grid.setColumnStretch(0,1)

        grid.setColumnStretch(1,2)

        grid.setColumnStretch(2,1)

        grid.setRowStretch(0,2)

        grid.setRowStretch(1,2)

        grid.setRowStretch(2,1)

        root.addLayout(grid)

        # -------------------------------------------------

        status = QStatusBar()

        status.showMessage("ON3RT LIVE 2.0")

        self.setStatusBar(status)

    # -----------------------------------------------------

    def placeholder(self,title):

        frame = QFrame()

        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        layout = QVBoxLayout(frame)

        lab = QLabel(title)

        font = QFont()

        font.setPointSize(14)

        font.setBold(True)

        lab.setFont(font)

        lab.setStyleSheet("color:#00dfff;")

        lab.setAlignment(
            lab.alignment().AlignCenter
        )

        txt = QLabel("En construction")

        txt.setAlignment(
            txt.alignment().AlignCenter
        )

        txt.setStyleSheet("""
            color:#9beeff;
            font-size:13pt;
        """)

        layout.addWidget(lab)

        layout.addStretch()

        layout.addWidget(txt)

        layout.addStretch()

        return frame

    # -----------------------------------------------------

    def update_clock(self):

        now = datetime.now(timezone.utc)

        self.utc.setText(

            now.strftime(

                "UTC  %d/%m/%Y   %H:%M:%S"

            )

        )