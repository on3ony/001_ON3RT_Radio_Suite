#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Local Network Radio Suite Live Data Source (squelette — non implémenté)
Version : 0.1.0
Auteur : ON3RT
Description :
    Fournisseur LiveDataSource prévu pour se connecter à une autre
    installation ON3RT Radio Suite présente sur le même réseau local
    (LAN) — par exemple celle d'un autre radioamateur sur le même
    réseau, ou une seconde installation personnelle dans un autre
    bâtiment/pièce.

    Un LAN bénéficie d'une confiance implicite (réseau privé, pas
    d'exposition publique) : ce fournisseur n'a donc besoin, à terme,
    que d'une adresse et d'un port, sans authentification obligatoire.

    Ce squelette fixe uniquement la forme du constructeur et le
    respect du contrat LiveDataSource, afin que son implémentation
    future ne demande aucune modification de LiveService ni des
    panneaux. Aucune communication réseau n'est développée ici.
=========================================================
"""

from .base import LiveDataSource


class LocalNetworkRadioSuiteLiveDataSource(LiveDataSource):
    """
    Fournisseur "Radio Suite distante (réseau local)" (non
    implémenté). `host`/`port` identifient l'installation à joindre
    sur le LAN ; `callsign` est un libellé optionnel, réservé à un
    usage d'affichage futur.
    """

    def __init__(self, host, port, callsign=None, parent=None):
        super().__init__(parent)

        self.host = host
        self.port = port
        self.callsign = callsign

    def start(self):
        raise NotImplementedError(
            "LocalNetworkRadioSuiteLiveDataSource n'est pas encore implémenté : "
            "architecture préparée, communication réseau à venir."
        )

    def stop(self):
        raise NotImplementedError(
            "LocalNetworkRadioSuiteLiveDataSource n'est pas encore implémenté : "
            "architecture préparée, communication réseau à venir."
        )
