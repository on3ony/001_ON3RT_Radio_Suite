#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Local File Live Data Source
Version : 1.0.0
Auteur : ON3RT
Description :
    Fournisseur LiveDataSource pour le mode actuel : une
    installation locale de la ON3RT Radio Suite. Lit périodiquement
    data/live.json, écrit par le moteur CAT partagé de la suite
    (apps/cat_server/radio_service.py — RadioService, source unique
    de vérité CAT) à chaque poll réussi.

    C'est un fournisseur parmi d'autres possibles (voir base.py) :
    passer à un fournisseur réseau, API ou WebSocket ne demande
    aucune modification de LiveService ni des panneaux.
=========================================================
"""

import json
import time
from pathlib import Path

from PySide6.QtCore import QTimer

from .base import LiveDataSource

# ----------------------------------------------------------------------
# Emplacement des données
# ----------------------------------------------------------------------

DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "live.json"

POLL_INTERVAL_MS = 1000

# ----------------------------------------------------------------------
# Champs dont CE fournisseur est responsable
# ----------------------------------------------------------------------
#
# Volontairement distinct de DEFAULT_STATE (base.py, contrat partagé
# par tous les fournisseurs) : ne reprendre que ses propres champs
# évite qu'un poll de ce fournisseur n'écrase, avec leur valeur par
# défaut, des clés dont d'autres fournisseurs sont responsables (ex.
# "logbook" pour LogbookLiveDataSource) lorsque plusieurs fournisseurs
# sont combinés dans le même LiveService.

DEFAULT_CAT_STATE = {
    "connected": False,
    "frequency": None,
    "mode": None,
    "band": None,
    "ptt": False,
    "vfo": None,
}

# ----------------------------------------------------------------------
# Fraîcheur des données
# ----------------------------------------------------------------------
#
# apps/cat_server/radio_service.py réécrit data/live.json à chaque poll
# réussi (toutes les 250 ms) tant qu'il est réellement connecté à la
# radio et actif. Si le fichier n'a pas été rafraîchi depuis plus de
# STALE_AFTER_SECONDS, cela signifie que le pont CAT ne tourne plus (ou
# plus jamais tourné) : on préfère alors ignorer son contenu (dernière
# fréquence, "connected": true, etc.) plutôt que d'afficher une donnée
# périmée comme si elle était réelle. Cette notion de fraîcheur est
# propre à ce type de fournisseur (fichier relu périodiquement) : elle
# n'a pas à être connue de LiveService ni des autres fournisseurs.

STALE_AFTER_SECONDS = 3.0


class LocalFileLiveDataSource(LiveDataSource):
    """
    Relit data/live.json toutes les POLL_INTERVAL_MS et pousse l'état
    courant via `updated`, en repli sur DEFAULT_CAT_STATE si le
    fichier est absent, illisible, ou périmé.
    """

    def __init__(self, path=None, parent=None):
        super().__init__(parent)

        self._path = Path(path) if path else DEFAULT_PATH

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)

    # -----------------------------------------------------
    # Cycle de vie
    # -----------------------------------------------------

    def start(self):
        self._poll()
        self._timer.start()

    def stop(self):
        self._timer.stop()

    # -----------------------------------------------------
    # Sondage
    # -----------------------------------------------------

    def _poll(self):
        self.updated.emit(self._read_state())

    def _read_state(self):

        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)

        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return dict(DEFAULT_CAT_STATE)

        if not isinstance(data, dict):
            return dict(DEFAULT_CAT_STATE)

        if self._is_stale(data):
            return dict(DEFAULT_CAT_STATE)

        state = dict(DEFAULT_CAT_STATE)
        state.update(data)

        return state

    @staticmethod
    def _is_stale(data):
        """
        True si data/live.json n'a pas de timestamp exploitable ou si
        celui-ci date de plus de STALE_AFTER_SECONDS : le pont CAT
        (apps/cat_server) n'écrit plus, ses dernières valeurs ne
        doivent pas être présentées comme des données réelles.
        """

        timestamp = data.get("timestamp")

        if not isinstance(timestamp, (int, float)):
            return True

        return (time.time() - timestamp) > STALE_AFTER_SECONDS
