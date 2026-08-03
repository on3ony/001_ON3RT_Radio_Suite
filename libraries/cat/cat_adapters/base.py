#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
libraries/cat/cat_adapters/base.py -- Contrat CatAdapter
=========================================================
Description :
    Contrat commun à tout adaptateur de partage CAT, consommé par
    CatSharingService (libraries/cat/cat_sharing_service.py). Un
    adaptateur traduit un protocole concret (rigctld, WebSocket, API
    REST...) vers la surface générique exposée par CatSharingService --
    jamais l'inverse : CatSharingService ne connaît jamais le protocole
    d'un adaptateur, exactement comme MapPanel ne connaît jamais le
    contenu d'une MapLayer (apps/dashboard/map_layers/base.py) ou
    LiveService celui d'une LiveDataSource
    (apps/dashboard/data_sources/base.py).

    Ajouter un nouvel adaptateur (ex. WebSocket, plus tard) ne demande
    jamais de modifier CatSharingService ni RadioService -- seulement
    d'implémenter ce contrat et de l'enregistrer via
    CatSharingService.add_adapter().

    Un adaptateur reçoit le CatSharingService (jamais RadioService
    directement) à son constructeur -- injection, comme partout
    ailleurs dans la Suite.
=========================================================
"""

from __future__ import annotations

from PySide6.QtCore import QObject


class CatAdapter(QObject):
    """
    Classe de base pour tout adaptateur de partage CAT. Une sous-classe
    concrète (ex. RigctldAdapter, à venir) doit implémenter start() et
    stop() : ce contrat ne préjuge d'aucun protocole ni d'aucune
    technologie de transport (TCP, WebSocket...).
    """

    def start(self) -> None:
        """Démarre l'adaptateur (ouvre son transport, commence à écouter...)."""

        raise NotImplementedError

    def stop(self) -> None:
        """Arrête proprement l'adaptateur (ferme son transport...)."""

        raise NotImplementedError
