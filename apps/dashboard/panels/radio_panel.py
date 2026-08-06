#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Radio Panel
=========================================================
Description :
    Rafraîchissement visuel (2026-08-02) : la fréquence reste
    l'information hero du panneau ; Bande/Mode/RX-TX apparaissent
    juste en dessous comme trois badges de même poids visuel (demande
    explicite de l'utilisateur, validée sur maquette) -- le badge
    RX/TX bascule vert/rouge selon le PTT réel (convention documentée
    dans assets/themes/on3rt_dark.qss : vert = connecté/actif/RX/OK,
    rouge = TX/erreur/alarme), Bande et Mode restent dans les
    couleurs neutres du thème (cyan/gris), jamais colorés.

    VFO, Puissance et Antenne ont été retirés : audit CI-V du
    2026-08-02 (IC-7300MK2 CI-V Reference Guide officiel, lu
    intégralement) -- la commande 0x07 (VFO) n'a aucune forme de
    lecture, et aucune commande de sélection de port d'antenne
    n'existe pour ce modèle. Aucune donnée honnête ne pourra jamais
    alimenter ces trois champs sur cet IC-7300 ; les afficher en
    permanence à "--" allait à l'encontre de la préférence explicite
    de l'utilisateur (masquer plutôt qu'afficher du vide). La
    puissance instantanée (Po mètre, TX seulement) est reportée à un
    futur panneau "Mesures"/"Instrumentation" dédié, avec le SWR.

    S-mètre : widget graphique (2026-08-02, SMeterBar) -- consomme
    directement state["smeter_level"] (entier brut 0-255, la donnée de
    référence, voir apps/cat_server/radio_service.py et
    libraries/cat/smeter.py), jamais state["smeter"] (le texte "S9"
    etc.), qui reste une simple étiquette affichée à côté de la barre.
    Heure UTC ajoutée : donnée déjà disponible dans l'état partagé
    (UTCManager, indépendante de la radio), coût nul.
=========================================================
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
)

from apps.dashboard.widgets.smeter_bar import SMeterBar

_BADGE_BASE_STYLE = """
    font-size:13pt;
    font-weight:600;
    padding:5px 14px;
    border-radius:8px;
"""

_BADGE_NEUTRAL_STYLE = _BADGE_BASE_STYLE + """
    background:#0f1c36;
    border:1px solid #2c4a78;
    color:#9beeff;
"""

_BADGE_RX_STYLE = _BADGE_BASE_STYLE + """
    background:rgba(0,255,136,0.14);
    border:1px solid #00ff88;
    color:#00ff88;
"""

_BADGE_TX_STYLE = _BADGE_BASE_STYLE + """
    background:rgba(255,102,102,0.14);
    border:1px solid #ff6666;
    color:#ff6666;
"""

_ROW_BOX_STYLE = """
    background:#0d1a32;
    border:1px solid #1a2c4d;
    border-radius:8px;
"""

_ROW_LABEL_STYLE = "font-size:11pt; color:#9beeff;"
_ROW_VALUE_STYLE = "font-size:13pt; font-weight:600; color:#edf2fb;"


class RadioPanel(QFrame):

    def __init__(self, live_service=None):
        super().__init__()

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

        # ------------------------------------------------

        titre = QLabel("📻 RADIO")

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
        # État de connexion
        # ------------------------------------------------

        self.connection = QLabel("Connexion inconnue")
        self.connection.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection.setStyleSheet("font-size:11pt; font-weight:bold; color:#9beeff;")
        layout.addWidget(self.connection)

        # ------------------------------------------------
        # Fréquence -- information hero du panneau
        # ------------------------------------------------

        self.frequency = QLabel("--")
        self.frequency.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frequency.setStyleSheet("""
            font-size:24pt;
            font-weight:600;
            color:#ffffff;
            padding:10px 0 4px;
        """)
        layout.addWidget(self.frequency)

        # ------------------------------------------------
        # Bande / Mode / RX-TX -- trois badges de même poids
        # visuel, juste sous la fréquence (demande explicite,
        # validée sur maquette -- voir docstring du module).
        # ------------------------------------------------

        badges_row = QHBoxLayout()
        badges_row.setSpacing(8)

        self.band = QLabel("--")
        self.mode = QLabel("--")
        self.ptt = QLabel("RX")

        self.band.setStyleSheet(_BADGE_NEUTRAL_STYLE)
        self.mode.setStyleSheet(_BADGE_NEUTRAL_STYLE)
        self.ptt.setStyleSheet(_BADGE_RX_STYLE)

        for badge in (self.band, self.mode, self.ptt):
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badges_row.addWidget(badge)

        badges_row.setContentsMargins(0, 4, 0, 14)
        layout.addLayout(badges_row)

        # ------------------------------------------------
        # S-mètre -- widget graphique (barre animée + texte), voir
        # docstring du module : la barre consomme smeter_level
        # (référence), le texte consomme smeter (représentation).
        # ------------------------------------------------

        self.smeter = QLabel("--")
        self.smeter_bar = SMeterBar()
        layout.addWidget(self._build_smeter_row())

        # ------------------------------------------------
        # UTC -- ligne label-à-gauche / valeur-à-droite
        # ------------------------------------------------

        self.utc = QLabel("--")
        layout.addWidget(self._build_info_row("🕒 UTC", self.utc))

        # ------------------------------------------------
        # Pied de panneau -- informations secondaires (modèle,
        # port, vitesse), regroupées en une seule ligne discrète
        # plutôt que trois lignes de même poids que le reste.
        # ------------------------------------------------

        self.footer = QLabel("--")
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer.setStyleSheet("""
            font-size:9pt;
            color:#5f6e8a;
            padding-top:8px;
            border-top:1px solid #1a2c4d;
            margin-top:4px;
        """)
        layout.addWidget(self.footer)

        layout.addStretch()

        # ------------------------------------------------
        # LiveService (optionnel) : si fourni, prend le relais
        # pour la mise à jour automatique depuis data/live.json
        # (alimenté par apps/cat_server/radio_service.py).
        # ------------------------------------------------

        self._live_service = live_service

        if self._live_service is not None:
            self._live_service.state_changed.connect(self.update_from_state)
            self.update_from_state(self._live_service.state())

    # --------------------------------------------------

    @staticmethod
    def _build_info_row(label_text, value_widget):
        """Ligne encadrée label-à-gauche / valeur-à-droite (S-mètre, UTC)."""

        row = QFrame()
        row.setStyleSheet("QFrame{" + _ROW_BOX_STYLE + "}")

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(14, 6, 14, 6)

        label = QLabel(label_text)
        label.setStyleSheet(_ROW_LABEL_STYLE)

        value_widget.setStyleSheet(_ROW_VALUE_STYLE)
        value_widget.setAlignment(Qt.AlignmentFlag.AlignRight)

        row_layout.addWidget(label)
        row_layout.addStretch()
        row_layout.addWidget(value_widget)

        return row

    # --------------------------------------------------

    def _build_smeter_row(self):
        """
        Ligne encadrée S-mètre : icône/label, barre animée (self.smeter_bar,
        consomme smeter_level), valeur texte à droite (self.smeter,
        consomme smeter) -- voir docstring du module.
        """

        row = QFrame()
        row.setStyleSheet("QFrame{" + _ROW_BOX_STYLE + "}")

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(14, 8, 14, 8)
        # Espacement volontairement resserré (voir docstring du module) :
        # la valeur doit être perçue comme faisant corps avec la barre,
        # jamais comme une donnée séparée -- seul l'écart icône/barre
        # reste respirant (addSpacing ci-dessous).
        row_layout.setSpacing(6)

        label = QLabel("📶")
        label.setStyleSheet(_ROW_LABEL_STYLE)

        self.smeter.setStyleSheet(_ROW_VALUE_STYLE)
        self.smeter.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.smeter.setMinimumWidth(36)

        row_layout.addWidget(label)
        row_layout.addSpacing(6)
        row_layout.addWidget(self.smeter_bar, stretch=1)
        row_layout.addWidget(self.smeter)

        return row

    # --------------------------------------------------

    @staticmethod
    def _text_or_dash(value):
        if value in (None, "", "{}"):
            return "--"

        return str(value)

    # --------------------------------------------------

    def update_from_state(self, state):
        """
        Slot connecté à LiveService.state_changed. Alimente le
        panneau avec l'état réel provenant du moteur CAT (via
        data/live.json). smeter reste "--" tant que le moteur CAT ne
        le fournit pas (aucune valeur inventée).
        """

        if not isinstance(state, dict):
            return

        connected = bool(state.get("connected", False))

        self.connection.setText(
            ("● Connecté" if connected else "● Déconnecté")
        )
        self.connection.setStyleSheet(f"""
            font-size:11pt;
            font-weight:bold;
            color:{'#00ff88' if connected else '#ff6666'};
        """)

        frequency = state.get("frequency")
        self.frequency.setText(
            (f"{int(frequency):,} Hz".replace(",", ".") if frequency else "--")
        )

        self.band.setText(self._text_or_dash(state.get("band")))
        self.mode.setText(self._text_or_dash(state.get("mode")))

        ptt = bool(state.get("ptt"))
        self.ptt.setText("TX" if ptt else "RX")
        self.ptt.setStyleSheet(_BADGE_TX_STYLE if ptt else _BADGE_RX_STYLE)

        self.smeter.setText(self._text_or_dash(state.get("smeter")))
        self.smeter_bar.set_target_level(state.get("smeter_level"))

        self.utc.setText(self._text_or_dash(state.get("utc_time")))

        model = self._text_or_dash(state.get("model"))
        port = self._text_or_dash(state.get("port"))
        baudrate = state.get("baudrate")
        baudrate_text = f"{baudrate} bauds" if baudrate else "--"

        self.footer.setText(f"{model}  ·  {port}  ·  {baudrate_text}")
