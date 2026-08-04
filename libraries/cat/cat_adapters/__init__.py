#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
libraries/cat/cat_adapters/
=========================================================
Description :
    Paquet des adaptateurs de partage CAT (contrat CatAdapter, voir
    base.py), consommés par CatSharingService
    (libraries/cat/cat_sharing_service.py). Réexporte le contrat commun
    pour un import simple :

        from libraries.cat.cat_adapters import CatAdapter

    RigctldAdapter (protocole rigctld/Hamlib) est le premier adaptateur
    concret -- encore en mode diagnostic uniquement à ce stade (voir sa
    docstring) : journalise le trafic réel de WSJT-X sans encore
    implémenter la moindre commande du protocole.
=========================================================
"""

from .base import CatAdapter
from .rigctld_adapter import RigctldAdapter

__all__ = [
    "CatAdapter",
    "RigctldAdapter",
]
