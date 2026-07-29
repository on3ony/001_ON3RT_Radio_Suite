#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Logbook Panel
=========================================================
Description :
    Affiche les derniers QSO du logbook réel. Si le logbook est
    indisponible ou vide, affiche "Aucun QSO."

    N'accède jamais au logbook directement : reçoit une instance de
    live_service.py (LiveService) et s'abonne à son signal
    state_changed, en lisant uniquement la clé "logbook" de l'état
    partagé (alimentée par data_sources/logbook_source.py —
    LogbookLiveDataSource, enregistrée dans dashboard_page.py).
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QFrame

MAX_QSO = 6


class LogbookPanel(QFrame):

    def __init__(self, live_service, parent=None):
        super().__init__(parent)

        self.setStyleSheet("""
            QFrame{
                background:#112743;
                border:2px solid #00cfff;
                border-radius:12px;
            }

            QLabel{
                color:white;
                border:none;
            }
        """)

        layout = QVBoxLayout(self)

        titre = QLabel("📖 LOGBOOK")

        font = QFont()
        font.setPointSize(14)
        font.setBold(True)

        titre.setFont(font)
        titre.setAlignment(Qt.AlignmentFlag.AlignCenter)

        titre.setStyleSheet("""
            color:#00dfff;
            padding:8px;
        """)

        layout.addWidget(titre)

        self._rows_container = QVBoxLayout()
        layout.addLayout(self._rows_container)
        layout.addStretch()

        self._row_labels = []

        # ------------------------------------------------
        # LiveService : seule source d'information de ce panneau.
        # ------------------------------------------------

        self._live_service = live_service
        self._live_service.state_changed.connect(self.update_state)
        self.update_state(self._live_service.state())

    # -----------------------------------------------------
    # Mise à jour depuis LiveService
    # -----------------------------------------------------

    def update_state(self, state):
        """
        Slot connecté à LiveService.state_changed. Lit uniquement la
        clé "logbook" (liste de dicts qso_date/time_on/callsign/band/
        mode) ; toute autre forme se traduit par une liste vide,
        jamais par une donnée inventée.
        """

        qsos = state.get("logbook", []) if isinstance(state, dict) else []

        if not isinstance(qsos, list):
            qsos = []

        self._render(qsos[:MAX_QSO])

    def _render(self, qsos):

        while self._row_labels:
            label = self._row_labels.pop()
            self._rows_container.removeWidget(label)
            label.deleteLater()

        if not qsos:
            empty = QLabel("Aucun QSO.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("""
                font-size:13pt;
                color:#9beeff;
            """)
            self._rows_container.addWidget(empty)
            self._row_labels.append(empty)
            return

        for qso in qsos:
            text = (
                f"{qso.get('qso_date') or '--'} {qso.get('time_on') or '--'}  "
                f"{qso.get('callsign') or '--'}  {qso.get('band') or '--'}  {qso.get('mode') or '--'}"
            )

            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                font-size:11pt;
                color:#9beeff;
            """)

            self._rows_container.addWidget(label)
            self._row_labels.append(label)
