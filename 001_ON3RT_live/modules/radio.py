#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Radio Module
Version : 1.0.0
Auteur : ON3RT
Description :
    Expose l'état radio courant à partir de data/live.json.
    Ne dépend d'aucun panneau ni de dashboard.py. Utilise le
    même fichier et la même stratégie de secours que
    services/live_service.py (compatible avec LiveService).
=========================================================
"""

import json
from pathlib import Path

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
    "model": "",
    "frequency": "",
    "band": "",
    "mode": "",
    "ptt": "",
    "power": "",
    "smeter": "",
}


class RadioModule:
    """
    Lit data/live.json et expose l'état radio courant.
    """

    def __init__(self, path=None):

        self._path = Path(path) if path else LIVE_DATA_FILE

    # -----------------------------------------------------
    # État
    # -----------------------------------------------------

    def get_state(self):
        """Relit data/live.json et retourne l'état radio courant."""

        return self._read_state()

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
