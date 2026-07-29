#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Data Sources
Version : 2.0.0
Auteur : ON3RT
Description :
    Paquet des fournisseurs de données ("Data Sources") pour
    LiveService. Tous partagent la même interface LiveDataSource
    (base.py) : LiveService ne connaît que cette interface, jamais
    un fournisseur concret en particulier.

    Réexporte l'interface commune et tous les fournisseurs, pour un
    import simple :

        from .data_sources import LiveDataSource, LocalFileLiveDataSource

    Opérationnels : LocalFileLiveDataSource (Radio Suite locale),
    DemoLiveDataSource (démonstration), TestLiveDataSource (tests
    automatisés), LogbookLiveDataSource (logbook réel de la suite).

    Squelettes (non implémentés, aucune communication réseau
    développée pour l'instant) : LocalNetworkRadioSuiteLiveDataSource
    (Radio Suite distante, réseau local), InternetRadioSuiteLiveDataSource
    (Radio Suite distante, Internet), ApiLiveDataSource, WebSocketLiveDataSource.
=========================================================
"""

from .api_source import ApiLiveDataSource
from .base import DEFAULT_STATE, LiveDataSource
from .demo_source import DemoLiveDataSource
from .internet_source import InternetRadioSuiteLiveDataSource
from .local_file_source import LocalFileLiveDataSource
from .local_network_source import LocalNetworkRadioSuiteLiveDataSource
from .logbook_source import LogbookLiveDataSource
from .test_source import TestLiveDataSource
from .websocket_source import WebSocketLiveDataSource

__all__ = [
    "LiveDataSource",
    "DEFAULT_STATE",
    "LocalFileLiveDataSource",
    "LocalNetworkRadioSuiteLiveDataSource",
    "InternetRadioSuiteLiveDataSource",
    "DemoLiveDataSource",
    "TestLiveDataSource",
    "LogbookLiveDataSource",
    "ApiLiveDataSource",
    "WebSocketLiveDataSource",
]
