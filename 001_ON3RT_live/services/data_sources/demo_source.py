#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Demo Live Data Source
Version : 1.0.0
Auteur : ON3RT
Description :
    Fournisseur LiveDataSource de démonstration : produit localement
    un état plausible (fréquence, mode, bande, PTT) en cyclant sur
    une petite liste fixe, sans matériel ni réseau. Aucune donnée
    n'est présentée comme réelle : "connected" reflète simplement le
    fonctionnement du générateur, pas une véritable connexion CAT.

    Utile pour développer ou faire la démonstration de l'interface
    indépendamment de tout fournisseur réel (fichier local, réseau,
    API...). Ne doit jamais être le fournisseur par défaut d'une
    installation réelle — LiveService continue d'utiliser
    LocalFileLiveDataSource sauf injection explicite d'une autre
    source.
=========================================================
"""

from PySide6.QtCore import QTimer

from .base import LiveDataSource

DEFAULT_INTERVAL_MS = 1500

# Champs dont CE fournisseur est responsable — volontairement
# distinct de DEFAULT_STATE (base.py, contrat partagé par tous les
# fournisseurs) : voir la mise en garde dans base.py. Émettre le
# contrat complet à chaque tick écraserait, avec des valeurs par
# défaut, les clés dont d'autres fournisseurs sont responsables (ex.
# "logbook") si ce fournisseur est un jour combiné avec un autre.
DEFAULT_CAT_STATE = {
    "connected": False,
    "frequency": None,
    "mode": None,
    "band": None,
    "ptt": False,
    "vfo": None,
}

# Petite rotation de relevés plausibles — purement illustrative.
DEMO_READINGS = (
    {"frequency": 14250000, "band": "20m", "mode": "USB"},
    {"frequency": 7100000, "band": "40m", "mode": "CW"},
    {"frequency": 3650000, "band": "80m", "mode": "LSB"},
    {"frequency": 21050000, "band": "15m", "mode": "FT8"},
)


class DemoLiveDataSource(LiveDataSource):
    """
    Cycle sur DEMO_READINGS toutes les interval_ms et pousse l'état
    correspondant via `updated`. PTT bascule brièvement à True une
    fois sur deux, pour illustrer les deux états à l'écran.
    """

    def __init__(self, interval_ms=DEFAULT_INTERVAL_MS, parent=None):
        super().__init__(parent)

        self._index = 0

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)

    # -----------------------------------------------------
    # Cycle de vie
    # -----------------------------------------------------

    def start(self):
        self._tick()
        self._timer.start()

    def stop(self):
        self._timer.stop()

    # -----------------------------------------------------
    # Génération
    # -----------------------------------------------------

    def _tick(self):

        reading = DEMO_READINGS[self._index % len(DEMO_READINGS)]

        state = dict(DEFAULT_CAT_STATE)
        state.update(reading)
        state["connected"] = True
        state["ptt"] = bool(self._index % 2)

        self._index += 1

        self.updated.emit(state)
