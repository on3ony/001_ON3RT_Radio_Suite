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
    taches, indices A/K, classe X-Ray, état géomagnétique, puis les
    conditions HF par bande calculées par HamQSL lui-même. N'accède
    jamais à PropagationService directement : reçoit une instance de
    LiveService et lit exclusivement les clés "propagation_connected"
    / "propagation_data" de l'état partagé (alimentées par
    data_sources/propagation_source.py — PropagationLiveDataSource).

    Panneau strictement descriptif : aucune interprétation, aucun
    seuil, aucun calcul, aucune traduction des valeurs — exactement
    les champs bruts publiés par PropagationService, affichés tels
    quels ou "--"/pastille grise s'ils sont absents. Aucune
    interaction utilisateur.

    Conditions HF : PropagationService expose "band_conditions" tel
    que HamQSL le calcule (bloc "calculatedconditions" du flux), sans
    aucun retraitement de sa part. C'est ce panneau, et lui seul, qui
    choisit d'afficher exactement les quatre groupes 80m/40m, 30m/20m,
    17m/15m, 12m/10m, dans cet ordre, sous forme compacte (pastille
    colorée + Jour/Nuit) — un choix de présentation, jamais une
    donnée recalculée. La couleur de chaque pastille est une simple
    correspondance directe avec le texte fourni par HamQSL
    (Good/Fair/Poor -> vert/jaune/rouge, tout le reste -> gris),
    jamais un seuil ou une évaluation inventée par ce panneau. 160m et
    6m ne sont pas traités ici (absents du bloc HamQSL, non demandés
    pour cette évolution).
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QFrame, QWidget


class PropagationPanel(QFrame):

    # Groupes de bandes HF affichés, dans cet ordre — décision de
    # présentation de ce panneau. La clé (à gauche) est le nom de paire
    # tel que publié par PropagationService/HamQSL ; le libellé (à
    # droite) n'en est qu'une reformulation d'affichage ("-" -> " / "),
    # jamais une transformation de la valeur d'état elle-même.
    BAND_GROUPS = (
        ("80m-40m", "80m / 40m"),
        ("30m-20m", "30m / 20m"),
        ("17m-15m", "17m / 15m"),
        ("12m-10m", "12m / 10m"),
    )

    # Correspondance directe texte HamQSL -> pastille colorée. Toute
    # valeur absente ou non reconnue (ex. future variante "Very Poor")
    # retombe honnêtement sur la pastille grise — jamais reclassée
    # dans l'une des trois couleurs connues.
    _STATE_DOTS = {
        "good": "🟢",
        "fair": "🟡",
        "poor": "🔴",
    }
    _UNKNOWN_DOT = "⚪"

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

        self._row_labels = []

        # ------------------------------------------------
        # Section Conditions HF : légende + tableau compact,
        # widgets persistants (créés une seule fois, mis à jour en
        # place à chaque relevé — les 4 groupes sont fixes).
        # ------------------------------------------------

        self._band_section = QWidget()
        # Le thème global de la Suite (assets/themes/on3rt_dark.qss)
        # applique "QWidget { background-color: #050911; }" à TOUT
        # QWidget nu — sans cette ligne, ce conteneur hérite ce fond
        # presque noir, visible à travers chaque interstice du
        # tableau (espacement entre les cellules) et perçu comme des
        # "traits noirs" de grille. Le rendre transparent laisse voir
        # le fond bleu nuit du panneau (#112743) sans aucune ligne.
        self._band_section.setStyleSheet("background: transparent;")

        band_section_layout = QVBoxLayout(self._band_section)
        band_section_layout.setContentsMargins(0, 8, 0, 0)
        band_section_layout.setSpacing(10)

        self._legend_label = QLabel("🟢 Good    🟡 Fair    🔴 Poor")
        self._legend_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._legend_label.setStyleSheet("font-size:10pt; color:#9beeff; background:transparent;")
        band_section_layout.addWidget(self._legend_label)

        self._band_grid = QGridLayout()
        self._band_grid.setHorizontalSpacing(32)
        self._band_grid.setVerticalSpacing(9)
        self._band_grid.setColumnMinimumWidth(1, 64)
        self._band_grid.setColumnMinimumWidth(2, 64)
        self._band_grid.setColumnStretch(0, 1)
        band_section_layout.addLayout(self._band_grid)

        self._band_row_widgets = {}

        for row, (key, display_name) in enumerate(self.BAND_GROUPS):
            name_label = QLabel(display_name)
            name_label.setStyleSheet("font-size:11pt; font-weight:bold; color:#9beeff; background:transparent;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            day_label = QLabel()
            day_label.setStyleSheet("font-size:11pt; color:#9beeff; background:transparent;")
            day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            night_label = QLabel()
            night_label.setStyleSheet("font-size:11pt; color:#9beeff; background:transparent;")
            night_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self._band_grid.addWidget(name_label, row, 0)
            self._band_grid.addWidget(day_label, row, 1)
            self._band_grid.addWidget(night_label, row, 2)

            self._band_row_widgets[key] = (day_label, night_label)

        layout.addWidget(self._band_section)
        layout.addStretch()

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
            self._band_section.setVisible(False)
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

        self._band_section.setVisible(True)
        self._update_band_grid(propagation)

    def _update_band_grid(self, propagation):
        band_conditions = propagation.get("band_conditions")

        if not isinstance(band_conditions, dict):
            band_conditions = {}

        for key, _display_name in self.BAND_GROUPS:
            day_label, night_label = self._band_row_widgets[key]
            pair = band_conditions.get(key)

            if not isinstance(pair, dict):
                pair = {}

            day_label.setText(self._format_pastille("Jour", pair.get("day")))
            night_label.setText(self._format_pastille("Nuit", pair.get("night")))

    @classmethod
    def _format_pastille(cls, period_label, state):
        normalized = state.strip().lower() if isinstance(state, str) else None
        dot = cls._STATE_DOTS.get(normalized, cls._UNKNOWN_DOT)

        return f"{dot} {period_label}"

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
