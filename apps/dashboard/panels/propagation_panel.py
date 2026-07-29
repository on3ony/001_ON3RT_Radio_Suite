#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Propagation Panel
=========================================================
Description :
    Affiche les indices solaires/géomagnétiques réels de la station
    (PropagationService, via LiveService) : flux solaire, nombre de
    taches, indices A/K, classe X-Ray, état géomagnétique. N'accède
    jamais à PropagationService directement : reçoit une instance de
    LiveService et lit exclusivement les clés "propagation_connected"
    / "propagation_data" de l'état partagé (alimentées par
    data_sources/propagation_source.py — PropagationLiveDataSource).

    Panneau V1 strictement descriptif : aucune interprétation, aucun
    seuil, aucune évaluation de bande, aucun calcul, aucun graphique —
    exactement les champs bruts publiés par PropagationService,
    affichés tels quels ou "--" s'ils sont absents. Aucune interaction
    utilisateur.
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QFrame


class PropagationPanel(QFrame):

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

        titre = QLabel("☀ PROPAGATION")

        font = QFont()
        font.setPointSize(15)
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
        "propagation_connected" et "propagation_data" ; toute autre
        forme se traduit par un état déconnecté et un message
        explicite, jamais par une donnée inventée.
        """

        connected = bool(state.get("propagation_connected", False)) if isinstance(state, dict) else False
        propagation = state.get("propagation_data") if isinstance(state, dict) else None

        self.connection.setText("Connecté" if connected else "Déconnecté")
        self.connection.setStyleSheet(f"""
            font-size:10pt;
            font-weight:bold;
            color:{'#00ff88' if connected else '#ffb454'};
        """)

        self._render(propagation if isinstance(propagation, dict) else None)

    def _render(self, propagation):

        while self._row_labels:
            label = self._row_labels.pop()
            self._rows_container.removeWidget(label)
            label.deleteLater()

        if propagation is None:
            empty = QLabel("Propagation indisponible.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("""
                font-size:13pt;
                color:#9beeff;
            """)
            self._rows_container.addWidget(empty)
            self._row_labels.append(empty)
            return

        for text in (
            self._format_solar_line(propagation),
            self._format_index_line(propagation),
            self._format_geomagnetic_line(propagation),
        ):
            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                font-size:12pt;
                color:#9beeff;
            """)

            self._rows_container.addWidget(label)
            self._row_labels.append(label)

    # -----------------------------------------------------
    # Mise en forme des lignes (affichage brut, aucune interprétation)
    # -----------------------------------------------------

    @staticmethod
    def _format_solar_line(propagation):
        solar_flux = propagation.get("solar_flux")
        sunspot_number = propagation.get("sunspot_number")

        flux_text = f"{solar_flux:.0f}" if isinstance(solar_flux, (int, float)) else "--"
        sunspots_text = str(sunspot_number) if isinstance(sunspot_number, int) else "--"

        return f"Flux solaire : {flux_text}   ·   Taches : {sunspots_text}"

    @staticmethod
    def _format_index_line(propagation):
        a_index = propagation.get("a_index")
        k_index = propagation.get("k_index")

        a_text = str(a_index) if isinstance(a_index, int) else "--"
        k_text = str(k_index) if isinstance(k_index, int) else "--"

        return f"A-Index : {a_text}   ·   K-Index : {k_text}"

    @staticmethod
    def _format_geomagnetic_line(propagation):
        x_ray_class = propagation.get("x_ray_class")
        geomagnetic_status = propagation.get("geomagnetic_status")

        x_ray_text = x_ray_class if x_ray_class else "--"
        geomagnetic_text = geomagnetic_status if geomagnetic_status else "--"

        return f"X-Ray : {x_ray_text}   ·   Géomagnétique : {geomagnetic_text}"
