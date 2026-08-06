#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Band Activity Panel
=========================================================
Description :
    Affiche l'activité par bande. Ne lit jamais data/live.json
    directement : reçoit une instance de live_service.py
    (LiveService) et s'abonne à son signal state_changed.

    Construction dynamique (chantier "Tuile Activité par bande",
    2026-08-05) : aucune bande n'est codée en dur ici. Les lignes de
    la grille sont construites une seule fois, à l'ouverture, à partir
    de deux sources externes uniquement :
        - libraries/radio/band_manager.py::BandManager.BANDS pour le
          nom et l'ORDRE des bandes (seule source de vérité, jamais
          une liste indépendante) ;
        - libraries/radio/license_privileges.py::allowed_bands() pour
          filtrer selon station_service.license_class -- ce panneau
          ne connaît AUCUNE règle de privilège lui-même (quelles
          bandes une classe autorise), il se contente d'interroger le
          registre. Une classe ON3 ne voit que 5 lignes (80/40/20/15/
          10m) ; une classe HAREC (ou toute future classe ajoutée au
          registre) voit automatiquement plus ou moins de lignes,
          sans aucune modification de ce fichier.

    La classe de licence est lue une seule fois, à la construction
    (même convention que Réglages → Partage CAT : un changement de
    classe de licence dans Réglages → Station nécessite un
    redémarrage de la Radio Suite pour être pris en compte ici).

    Le nombre de lignes suit donc directement le nombre de bandes
    autorisées : pas de lignes vides pour des bandes masquées (elles
    ne sont simplement jamais construites), et addStretch() en fin de
    mise en page maintient les lignes groupées en haut plutôt que
    dispersées sur toute la hauteur disponible.

    AUCUN calcul métier ici (calcul de comptage/seuils -- demande
    explicite, étape 4 du chantier) : fenêtre glissante, seuils de
    couleur et comptage vivent exclusivement dans
    apps/dashboard/data_sources/band_activity_source.py
    (BandActivityLiveDataSource). Ce panneau lit
    state["bands"] = {"20m": {"count": int, "color": "#RRGGBB"}, ...}
    et affiche tel quel le compte et la couleur fournis.

    Bargraph (étape 5, demande explicite de l'utilisateur) : chaque
    ligne combine une barre horizontale ET le chiffre, dans la même
    couleur -- jamais l'un sans l'autre. La LARGEUR de la barre reste
    une pure mise à l'échelle graphique (valeur ÷ maximum observé
    parmi les bandes actuellement affichées), pas une règle métier :
    calculée ici, dans update_state(), à partir des comptes déjà
    fournis. Quand toutes les bandes sont à 0, chaque barre reste
    vide (aucune division par zéro : le maximum utilisé pour l'échelle
    est toujours au moins 1). Style volontairement sobre : couleur
    plate, sans dégradé ni animation, mêmes couleurs de piste que le
    reste du Dashboard (SMeterBar, badges RadioPanel).

    Repris à l'origine de 001_ON3RT_live/panels/band_activity_panel.py,
    puis entièrement dynamisé lors de ce chantier.
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
)

from libraries.radio.band_manager import BandManager
from libraries.radio.license_privileges import allowed_bands

# Couleur/texte tant qu'aucune donnée n'a encore été reçue de
# LiveService pour une bande donnée -- pur style d'attente, pas une
# interprétation de seuil (voir band_activity_source.py pour ça).
NEUTRAL_COLOR = "#5f6e8a"
DEMO_VALUE = "—"

# Piste de la barre -- mêmes couleurs que le reste du Dashboard
# (SMeterBar._TRACK_COLOR/_BORDER_COLOR, RadioPanel._ROW_BOX_STYLE).
BAR_TRACK_COLOR = "#0d1a32"
BAR_BORDER_COLOR = "#1a2c4d"

# Barre volontairement épaisse pour rester visible d'un coup d'œil
# (ajustement demandé par l'utilisateur, 2026-08-05).
BAR_HEIGHT = 16
BAR_RADIUS = BAR_HEIGHT // 2

_BAND_LABEL_WIDTH = 40
_VALUE_LABEL_WIDTH = 22


def resolve_displayed_bands(station_service) -> list:
    """
    Retourne la liste ordonnée des noms de bandes à afficher pour la
    classe de licence de `station_service`, dans l'ordre de
    BandManager.BANDS. `station_service` absent ou sans license_class
    exploitable retombe sur le comportement par défaut de
    allowed_bands() (classe non restreinte) -- jamais de bande
    inventée, jamais d'exception.
    """

    license_class = getattr(station_service, "license_class", "") if station_service is not None else ""
    allowed = allowed_bands(license_class)

    return [band.name for band in BandManager.BANDS if band.name in allowed]


def _bar_stylesheet(color: str) -> str:
    """Style plat -- piste sombre commune au Dashboard + remplissage uni de `color`, sans dégradé ni animation."""

    return f"""
        QProgressBar{{
            background:{BAR_TRACK_COLOR};
            border:1px solid {BAR_BORDER_COLOR};
            border-radius:{BAR_RADIUS}px;
        }}
        QProgressBar::chunk{{
            background:{color};
            border-radius:{BAR_RADIUS}px;
        }}
    """


class BandActivityPanel(QWidget):
    """
    Panneau d'activité par bande, piloté par LiveService pour les
    valeurs et par StationService (classe de licence) pour le choix
    des lignes affichées. N'effectue lui-même aucun calcul métier :
    affiche tel quel ce que lui fournit state["bands"], la largeur de
    la barre n'étant qu'une mise à l'échelle graphique locale.
    """

    def __init__(self, station_service, live_service=None, parent=None):

        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._live_service = live_service
        self._value_labels = {}
        self._bars = {}
        self._bands = resolve_displayed_bands(station_service)

        self.setStyleSheet("""
            BandActivityPanel{
                background:#112743;
                border:2px solid #00cfff;
                border-radius:12px;
            }

            QLabel{
                color:white;
                border:none;
            }
        """)

        self.build_ui()

        if self._live_service is not None:
            self._live_service.state_changed.connect(self.update_state)
            self.update_state(self._live_service.state())

    # -----------------------------------------------------
    # Construction de l'interface
    # -----------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        # ------------------------------------------------

        titre = QLabel("📊 ACTIVITÉ PAR BANDE")

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

        # ------------------------------------------------
        # Une ligne par bande AUTORISÉE uniquement (self._bands) --
        # jamais une ligne pour une bande masquée par la classe de
        # licence active : elle n'est simplement pas construite ici.
        # Chaque ligne : nom de bande, barre, chiffre (même couleur).
        # ------------------------------------------------

        rows_layout = QVBoxLayout()
        rows_layout.setSpacing(8)

        for band in self._bands:

            row = QHBoxLayout()
            row.setSpacing(10)

            band_label = QLabel(band)
            band_label.setFixedWidth(_BAND_LABEL_WIDTH)
            band_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            band_label.setStyleSheet("""
                font-size:11.5pt;
                color:#9beeff;
            """)

            bar = QProgressBar()
            bar.setRange(0, 1)
            bar.setValue(0)
            bar.setFixedHeight(BAR_HEIGHT)
            bar.setTextVisible(False)
            bar.setStyleSheet(_bar_stylesheet(NEUTRAL_COLOR))

            value_label = QLabel(DEMO_VALUE)
            value_label.setFixedWidth(_VALUE_LABEL_WIDTH)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            value_label.setStyleSheet(f"""
                font-size:11.5pt;
                font-weight:bold;
                color:{NEUTRAL_COLOR};
            """)

            row.addWidget(band_label)
            row.addWidget(bar, 1)
            row.addWidget(value_label)

            rows_layout.addLayout(row)

            self._value_labels[band] = value_label
            self._bars[band] = bar

        layout.addLayout(rows_layout)
        layout.addStretch()

    # -----------------------------------------------------
    # Mise à jour depuis LiveService
    # -----------------------------------------------------

    def update_state(self, state):
        """
        Slot connecté à LiveService.state_changed.

        Attend un dict optionnel state["bands"] de la forme
        {"20m": {"count": int, "color": "#RRGGBB"}, ...} (voir
        BandActivityLiveDataSource, seule responsable du calcul).
        Seules les bandes déjà affichées (self._bands, fixées à la
        construction selon la classe de licence) sont mises à jour ;
        toute autre clé de state["bands"] est ignorée sans erreur.
        Une entrée absente ou malformée retombe sur l'affichage
        neutre, jamais une valeur devinée.

        Largeur de barre : count / max(comptes affichés, 1) -- pure
        mise à l'échelle graphique locale, jamais une règle métier
        (voir docstring du module).
        """

        bands_data = state.get("bands", {}) if isinstance(state, dict) else {}

        if not isinstance(bands_data, dict):
            bands_data = {}

        counts = {}
        colors = {}

        for band in self._bands:
            entry = bands_data.get(band)
            if isinstance(entry, dict) and "count" in entry:
                counts[band] = entry["count"]
                colors[band] = entry.get("color", NEUTRAL_COLOR)

        max_count = max(counts.values(), default=0)
        scale_max = max(max_count, 1)

        for band in self._bands:

            value_label = self._value_labels[band]
            bar = self._bars[band]

            if band not in counts:
                value_label.setText(DEMO_VALUE)
                value_label.setStyleSheet(f"""
                    font-size:11.5pt;
                    font-weight:bold;
                    color:{NEUTRAL_COLOR};
                """)
                bar.setRange(0, 1)
                bar.setValue(0)
                bar.setStyleSheet(_bar_stylesheet(NEUTRAL_COLOR))
                continue

            count = counts[band]
            color = colors[band]

            value_label.setText(str(count))
            value_label.setStyleSheet(f"""
                font-size:11.5pt;
                font-weight:bold;
                color:{color};
            """)

            bar.setRange(0, scale_max)
            bar.setValue(max(0, count))
            bar.setStyleSheet(_bar_stylesheet(color))
