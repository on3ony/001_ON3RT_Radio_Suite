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

    Aucun adaptateur concret n'existe encore -- RigctldAdapter (premier
    adaptateur concret, protocole rigctld/Hamlib) est la prochaine
    étape de ce chantier, pas encore construite.
=========================================================
"""

from .base import CatAdapter

__all__ = [
    "CatAdapter",
]
