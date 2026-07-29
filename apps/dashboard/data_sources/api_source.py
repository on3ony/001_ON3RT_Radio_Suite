#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — API Live Data Source (squelette — non implémenté)
=========================================================
Description :
    Fournisseur LiveDataSource prévu pour interroger périodiquement
    une API HTTP exposant l'état d'une station (locale ou distante).

    Ce squelette fixe uniquement la forme du constructeur et le
    respect du contrat LiveDataSource, afin que son implémentation
    future ne demande aucune modification de LiveService ni des
    panneaux. Aucune communication réseau n'est développée ici.

    Portage de 001_ON3RT_live/services/data_sources/api_source.py,
    inchangé.
=========================================================
"""

from .base import LiveDataSource

DEFAULT_POLL_INTERVAL_MS = 2000


class ApiLiveDataSource(LiveDataSource):
    """
    Fournisseur API HTTP (non implémenté). Interrogera `base_url`
    toutes les poll_interval_ms pour obtenir l'état courant.
    """

    def __init__(self, base_url, api_key=None, poll_interval_ms=DEFAULT_POLL_INTERVAL_MS, parent=None):
        super().__init__(parent)

        self.base_url = base_url
        self.api_key = api_key
        self.poll_interval_ms = poll_interval_ms

    def start(self):
        raise NotImplementedError(
            "ApiLiveDataSource n'est pas encore implémenté : "
            "architecture préparée, communication réseau à venir."
        )

    def stop(self):
        raise NotImplementedError(
            "ApiLiveDataSource n'est pas encore implémenté : "
            "architecture préparée, communication réseau à venir."
        )
