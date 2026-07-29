#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — WebSocket Live Data Source (squelette — non implémenté)
=========================================================
Description :
    Fournisseur LiveDataSource prévu pour recevoir l'état d'une
    station en direct via un flux WebSocket (poussé par le serveur,
    sans sondage périodique côté client).

    Ce squelette fixe uniquement la forme du constructeur et le
    respect du contrat LiveDataSource, afin que son implémentation
    future ne demande aucune modification de LiveService ni des
    panneaux. Aucune communication réseau n'est développée ici.

    Portage de 001_ON3RT_live/services/data_sources/websocket_source.py,
    inchangé.
=========================================================
"""

from .base import LiveDataSource


class WebSocketLiveDataSource(LiveDataSource):
    """
    Fournisseur WebSocket (non implémenté). Se connectera à `url`
    pour recevoir l'état d'une station en direct, sans sondage.
    """

    def __init__(self, url, parent=None):
        super().__init__(parent)

        self.url = url

    def start(self):
        raise NotImplementedError(
            "WebSocketLiveDataSource n'est pas encore implémenté : "
            "architecture préparée, communication réseau à venir."
        )

    def stop(self):
        raise NotImplementedError(
            "WebSocketLiveDataSource n'est pas encore implémenté : "
            "architecture préparée, communication réseau à venir."
        )
