#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Logbook Live Data Source
=========================================================
Description :
    Fournisseur LiveDataSource pour le logbook réel de la suite
    (apps/logbook/repository.py — LogbookRepository, base SQLite
    locale). Relit périodiquement les derniers QSO et les pousse
    dans l'état partagé sous la clé "logbook" (liste de dicts
    simples), pour que LiveService et les panneaux n'aient jamais
    besoin d'importer apps.logbook eux-mêmes.

    Contrairement au CAT (poussé en continu par une connexion série
    active), le logbook est une base SQLite locale : ce fournisseur
    la relit à intervalle régulier plutôt que d'être notifié en
    direct. Toute erreur (module absent, base indisponible) se
    traduit par une liste vide — jamais par une donnée inventée.

    Portage de 001_ON3RT_live/services/data_sources/logbook_source.py,
    inchangé.
=========================================================
"""

from PySide6.QtCore import QTimer

from .base import LiveDataSource

DEFAULT_INTERVAL_MS = 5000
DEFAULT_LIMIT = 6


class LogbookLiveDataSource(LiveDataSource):
    """
    Relit les `limit` derniers QSO toutes les interval_ms et pousse
    `{"logbook": [...]}` via `updated`. Chaque QSO est un dict simple
    {qso_date, time_on, callsign, band, mode} — aucun type propre à
    apps.logbook n'est exposé en dehors de ce fournisseur.
    """

    def __init__(self, limit=DEFAULT_LIMIT, interval_ms=DEFAULT_INTERVAL_MS, parent=None):
        super().__init__(parent)

        self._limit = limit

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
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
        self.updated.emit({"logbook": self._fetch_qsos()})

    def _fetch_qsos(self):

        try:
            from apps.logbook.repository import LogbookRepository
        except ImportError:
            return []

        try:
            repo = LogbookRepository()
        except Exception:
            return []

        try:
            qsos = repo.get_all()[:self._limit]
        except Exception:
            return []
        finally:
            repo.close()

        return [
            {
                "qso_date": qso.qso_date,
                "time_on": qso.time_on,
                "callsign": qso.callsign,
                "band": qso.band,
                "mode": qso.mode,
            }
            for qso in qsos
        ]
