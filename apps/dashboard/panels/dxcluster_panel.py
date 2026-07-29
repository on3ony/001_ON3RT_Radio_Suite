#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — DX Cluster Panel
=========================================================
Description :
    Affiche les derniers spots DX Cluster (6 maximum, le plus récent
    en premier), fournis par DXClusterLiveDataSource via LiveService.
    N'accède jamais à DXClusterService directement : reçoit une
    instance de LiveService et lit exclusivement les clés
    "dxcluster_connected" / "dxcluster_spots" de l'état partagé.

    Panneau V1 strictement informatif, périmètre figé :
        - aucune interaction utilisateur (pas de clic, pas de menu
          contextuel) ;
        - aucun QSY ;
        - aucun indicateur "déjà travaillé" (nécessiterait de faire
          évoluer LogbookLiveDataSource, volontairement reporté) ;
        - mode/dxcc/locator non affichés tant qu'ils restent à None
          dans le contrat de spot (aucune donnée inventée).
    Ces points sont reportés à une V2, avec les enrichissements DXCC/
    LoTW/eQSL.

    L'indicatif spotté (champ le plus important pour l'opérateur) est
    seul mis en valeur visuellement. Les champs libres (commentaire,
    indicatif, spotter — texte reçu d'un tiers via le réseau DX
    Cluster) sont systématiquement échappés avant tout rendu HTML.
=========================================================
"""

import html

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QFrame

MAX_SPOTS = 6
MAX_COMMENT_LENGTH = 40


class DXClusterPanel(QFrame):

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

        titre = QLabel("📡 DX CLUSTER")

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

        self.connection = QLabel("Connexion inconnue")
        self.connection.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection.setStyleSheet("""
            font-size:10pt;
            color:#9beeff;
        """)
        layout.addWidget(self.connection)

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
        Slot connecté à LiveService.state_changed. Lit uniquement
        "dxcluster_connected" et "dxcluster_spots" ; toute autre forme
        se traduit par un état déconnecté et une liste vide, jamais
        par une donnée inventée.
        """

        connected = bool(state.get("dxcluster_connected", False)) if isinstance(state, dict) else False
        spots = state.get("dxcluster_spots", []) if isinstance(state, dict) else []

        if not isinstance(spots, list):
            spots = []

        self.connection.setText("Connecté" if connected else "Déconnecté")
        self.connection.setStyleSheet(f"""
            font-size:10pt;
            font-weight:bold;
            color:{'#00ff88' if connected else '#ffb454'};
        """)

        self._render(spots[-MAX_SPOTS:])

    def _render(self, spots):

        while self._row_labels:
            label = self._row_labels.pop()
            self._rows_container.removeWidget(label)
            label.deleteLater()

        if not spots:
            empty = QLabel("Aucun spot.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("""
                font-size:13pt;
                color:#9beeff;
            """)
            self._rows_container.addWidget(empty)
            self._row_labels.append(empty)
            return

        # Le plus récent en premier.
        for spot in reversed(spots):
            label = QLabel(self._format_spot(spot))
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                font-size:10pt;
                color:#9beeff;
            """)

            self._rows_container.addWidget(label)
            self._row_labels.append(label)

    @staticmethod
    def _format_spot(spot):
        """
        Construit une ligne HTML compacte pour un spot. Les champs
        libres (indicatif, spotter, commentaire) proviennent d'un
        tiers via le réseau DX Cluster : systématiquement échappés
        avant insertion dans le texte riche.
        """

        time_utc = spot.get("time_utc") or "--"

        frequency_khz = spot.get("frequency_khz")
        frequency_text = f"{frequency_khz:.1f}" if isinstance(frequency_khz, (int, float)) else "--"

        band = spot.get("band") or "--"

        dx_callsign = html.escape(str(spot.get("dx_callsign") or "--"))
        spotter = html.escape(str(spot.get("spotter") or "--"))

        comment = str(spot.get("comment") or "")
        if len(comment) > MAX_COMMENT_LENGTH:
            comment = comment[:MAX_COMMENT_LENGTH].rstrip() + "…"
        comment = html.escape(comment)

        text = (
            f"{time_utc} &nbsp;&middot;&nbsp; {frequency_text} kHz ({band}) &nbsp;&middot;&nbsp; "
            f'<b style="color:#ffffff;">{dx_callsign}</b> '
            f'<span style="color:#6f93b8;">&lt;{spotter}&gt;</span>'
        )

        if comment:
            text += f' &nbsp;&middot;&nbsp; <span style="color:#6f93b8;">{comment}</span>'

        return text
