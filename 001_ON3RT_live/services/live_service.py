#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Live Service
Version : 1.0.0
Auteur : ON3RT
Description :
    Service de lecture périodique de data/live.json, exposé
    via le signal state_changed. Ne dépend d'aucun panneau ni
    de dashboard.py.
=========================================================
"""

import json
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

# ----------------------------------------------------------------------
# Emplacement des données
# ----------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
LIVE_DATA_FILE = BASE_DIR / "data" / "live.json"

# ----------------------------------------------------------------------
# État par défaut
# ----------------------------------------------------------------------

DEFAULT_STATE = {
    "connected": False,
}


class LiveService(QObject):
    """
    Lit périodiquement data/live.json (toutes les 1000 ms) et
    diffuse l'état courant via le signal state_changed.
    """

    state_changed = Signal(dict)

    def __init__(self, path=None, parent=None):

        super().__init__(parent)

        self._path = Path(path) if path else LIVE_DATA_FILE
        self._state = dict(DEFAULT_STATE)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

        self.refresh()

    # -----------------------------------------------------
    # Rafraîchissement
    # -----------------------------------------------------

    def refresh(self):
        """
        Relit data/live.json, met à jour l'état courant et
        émet state_changed avec le nouvel état.
        """

        self._state = self._read_state()
        self.state_changed.emit(self._state)

        return self._state

    def state(self):
        """Retourne une copie de l'état courant (sans relire le fichier)."""

        return dict(self._state)

    # -----------------------------------------------------
    # Lecture du fichier
    # -----------------------------------------------------

    def _read_state(self):

        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)

        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return dict(DEFAULT_STATE)

        if not isinstance(data, dict):
            return dict(DEFAULT_STATE)

        state = dict(DEFAULT_STATE)
        state.update(data)

        return state
