#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Logbook Panel
Version : 2.0.0
Auteur : ON3RT
Description :
    Affiche les derniers QSO du logbook réel, sous forme de tableau
    à colonnes alignées (date, heure, indicatif, bande, mode),
    l'indicatif étant mis en valeur. Si le logbook est indisponible
    ou vide, affiche "Aucun QSO."

    N'accède jamais au logbook directement : reçoit une instance de
    services/live_service.py (LiveService) et s'abonne à son signal
    state_changed, en lisant uniquement la clé "logbook" de l'état
    partagé (alimentée par
    services/data_sources/logbook_source.py — LogbookLiveDataSource).
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QFrame

from .. import theme

COLUMNS = [
    ("DATE", 2),
    ("HEURE", 1),
    ("INDICATIF", 2),
    ("BANDE", 1),
    ("MODE", 1),
]

CALLSIGN_COLUMN_INDEX = 2


class LogbookPanel(QFrame):

    def __init__(self, live_service, parent=None):
        super().__init__(parent)

        theme.apply_panel_frame(self)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(0)

        layout.addWidget(theme.make_panel_title("📖 LOGBOOK"))

        body = QVBoxLayout()

        body.setContentsMargins(*theme.PANEL_CONTENT_MARGINS)

        body.setSpacing(theme.PANEL_CONTENT_SPACING)

        layout.addLayout(body)

        body.addWidget(theme.make_table_header(COLUMNS))

        self._rows_container = QVBoxLayout()

        self._rows_container.setSpacing(theme.TABLE_ROW_SPACING)

        body.addLayout(self._rows_container)

        body.addStretch()

        self._row_widgets = []

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

        self._render(qsos)

    def _render(self, qsos):

        while self._row_widgets:
            widget = self._row_widgets.pop()
            self._rows_container.removeWidget(widget)
            widget.deleteLater()

        if not qsos:
            empty = QLabel("Aucun QSO.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(theme.info_row_qss())
            self._rows_container.addWidget(empty)
            self._row_widgets.append(empty)
            return

        for qso in qsos:
            row = theme.make_table_row(
                [
                    (qso.get("qso_date") or "--", 2),
                    (qso.get("time_on") or "--", 1),
                    (qso.get("callsign") or "--", 2),
                    (qso.get("band") or "--", 1),
                    (qso.get("mode") or "--", 1),
                ],
                emphasize_index=CALLSIGN_COLUMN_INDEX,
            )

            self._rows_container.addWidget(row)
            self._row_widgets.append(row)
