#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Data Sources — contrat commun (LiveDataSource)
Version : 1.0.0
Auteur : ON3RT
Description :
    Interface commune à tout fournisseur de données d'état station
    ("Data Source") utilisable par LiveService.

    ON3RT Live ne doit jamais dépendre d'un chemin local ni d'un
    projet spécifique : toute donnée transite par cette interface,
    jamais par un accès direct à un fichier, un moteur CAT ou un
    réseau depuis LiveService ou (a fortiori) depuis un panneau.
    LiveService ne connaît que LiveDataSource ; les panneaux ne
    connaissent que LiveService.

    Fournisseurs de ce paquet — architecture figée, cette liste est
    appelée à grandir mais LiveService n'a jamais besoin d'être
    modifié pour cela :

        - LocalFileLiveDataSource (local_file_source.py) — opérationnel.
          "Radio Suite locale" : lit data/live.json, écrit par le
          moteur CAT partagé de la suite (apps/cat_server/radio_service.py).
          C'est la source par défaut de LiveService.
        - LocalNetworkRadioSuiteLiveDataSource (local_network_source.py)
          — squelette, non implémenté. "Radio Suite distante (réseau
          local)" : une autre installation de la suite sur le même LAN.
        - InternetRadioSuiteLiveDataSource (internet_source.py) —
          squelette, non implémenté. "Radio Suite distante (Internet)" :
          une autre installation de la suite hors réseau local, ex. la
          station d'un autre radioamateur.
        - DemoLiveDataSource (demo_source.py) — opérationnel. Génère
          une rotation d'états plausibles en local, sans matériel ni
          réseau ; utile pour montrer l'interface.
        - TestLiveDataSource (test_source.py) — opérationnel.
          Entièrement piloté par le code appelant (push_state()) ;
          destiné aux tests automatisés de LiveService et des
          panneaux, sans timer ni fichier.
        - LogbookLiveDataSource (logbook_source.py) — opérationnel.
          Relit périodiquement le logbook réel de la suite
          (apps/logbook/repository.py — LogbookRepository, SQLite) et
          alimente la clé "logbook" de l'état partagé.
        - ApiLiveDataSource (api_source.py) — squelette, non implémenté.
        - WebSocketLiveDataSource (websocket_source.py) — squelette,
          non implémenté.

    LiveService peut combiner plusieurs fournisseurs à la fois (ex.
    CAT + Logbook) : chacun ne contribue que les clés dont il est
    responsable, sans jamais connaître les autres.

    Les fournisseurs "squelette" ci-dessus fixent uniquement la forme
    de leur constructeur et le respect du contrat LiveDataSource :
    aucune communication réseau n'est développée à ce stade. Le jour
    où l'un d'eux sera implémenté, ni LiveService ni les panneaux
    n'auront besoin d'être modifiés — seul le fournisseur évolue.

    Chaque source pousse son état via le signal `updated`, que sa
    donnée provienne d'un sondage interne (timer, requête HTTP...)
    ou d'une notification réseau reçue en direct (WebSocket...).
=========================================================
"""

from PySide6.QtCore import QObject, Signal

# ----------------------------------------------------------------------
# Contrat de champs
# ----------------------------------------------------------------------
#
# Forme commune à tout fournisseur, quelle que soit son origine :
# c'est ce qui permet à LiveService et aux panneaux de ne jamais
# savoir d'où vient réellement la donnée. Un fournisseur qui ne peut
# pas obtenir un champ (ex. le VFO, voir local_file_source.py) le
# laisse à sa valeur par défaut plutôt que d'en inventer une.
#
# "logbook" : liste de dicts {qso_date, time_on, callsign, band, mode}
# — vide tant qu'aucun fournisseur de type Logbook n'est attaché à
# LiveService (voir logbook_source.py).
#
# ATTENTION — piège déjà rencontré et corrigé : DEFAULT_STATE est la
# base de référence que LiveService utilise pour SON PROPRE état
# initial (une fois, à la construction). Un fournisseur concret ne
# doit JAMAIS copier tout DEFAULT_STATE comme repli à chaque sondage :
# cela réémettrait, à chaque poll, les clés dont d'autres fournisseurs
# sont responsables (ex. "logbook") avec leur valeur par défaut,
# écrasant silencieusement leur contribution dès le sondage suivant.
# Un fournisseur ne doit émettre que les clés dont IL est responsable
# (voir local_file_source.py, demo_source.py : chacun définit son
# propre petit dict de repli, limité à ses propres champs).

DEFAULT_STATE = {
    "connected": False,
    "frequency": None,
    "mode": None,
    "band": None,
    "ptt": False,
    "vfo": None,
    "logbook": [],
}


class LiveDataSource(QObject):
    """
    Classe de base abstraite pour tout fournisseur de données
    consommé par LiveService. Une sous-classe concrète doit
    implémenter start() et stop(), et émettre `updated` avec un dict
    conforme au contrat DEFAULT_STATE chaque fois qu'un nouvel état
    est disponible.
    """

    updated = Signal(dict)

    def start(self):
        """Démarre la production de données (timer, connexion réseau...)."""

        raise NotImplementedError

    def stop(self):
        """Arrête proprement le fournisseur (timer, connexion réseau...)."""

        raise NotImplementedError
