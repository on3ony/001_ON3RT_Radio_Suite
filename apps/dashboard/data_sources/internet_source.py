#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Internet Radio Suite Live Data Source (squelette — non implémenté)
=========================================================
Description :
    Fournisseur LiveDataSource prévu pour se connecter à une autre
    installation ON3RT Radio Suite distante, hors réseau local — par
    exemple la station d'un autre radioamateur ailleurs sur
    Internet.

    Contrairement à une installation sur le même LAN, le réseau
    public ne bénéficie d'aucune confiance implicite : ce fournisseur
    prévoit donc, dès son squelette, une adresse/URL et un jeton
    d'authentification optionnel plutôt qu'un simple host/port.

    Ce squelette fixe uniquement la forme du constructeur et le
    respect du contrat LiveDataSource, afin que son implémentation
    future ne demande aucune modification de LiveService ni des
    panneaux. Aucune communication réseau n'est développée ici.

    Portage de 001_ON3RT_live/services/data_sources/internet_source.py,
    inchangé.
=========================================================
"""

from .base import LiveDataSource


class InternetRadioSuiteLiveDataSource(LiveDataSource):
    """
    Fournisseur "Radio Suite distante (Internet)" (non implémenté).
    `url` identifie l'installation à joindre ; `auth_token` est
    réservé à une authentification future ; `callsign` est un
    libellé optionnel, réservé à un usage d'affichage futur.
    """

    def __init__(self, url, auth_token=None, callsign=None, parent=None):
        super().__init__(parent)

        self.url = url
        self.auth_token = auth_token
        self.callsign = callsign

    def start(self):
        raise NotImplementedError(
            "InternetRadioSuiteLiveDataSource n'est pas encore implémenté : "
            "architecture préparée, communication réseau à venir."
        )

    def stop(self):
        raise NotImplementedError(
            "InternetRadioSuiteLiveDataSource n'est pas encore implémenté : "
            "architecture préparée, communication réseau à venir."
        )
