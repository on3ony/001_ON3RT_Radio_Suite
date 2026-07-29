#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Test Live Data Source
=========================================================
Description :
    Fournisseur LiveDataSource entièrement piloté par le code
    appelant : ne minute rien lui-même, ne lit aucun fichier,
    n'ouvre aucune connexion. Destiné aux tests automatisés de
    LiveService et des panneaux, pour simuler des états précis de
    façon synchrone et déterministe, sans dépendre d'un timer, d'un
    fichier ou d'un matériel réel.

    Différence avec DemoLiveDataSource : Demo minute lui-même une
    rotation d'états plausibles pour montrer l'interface ; Test ne
    minute rien et n'émet que ce que le code appelant lui demande
    explicitement d'émettre, au moment choisi par ce code — c'est le
    fournisseur à utiliser dans une suite de tests.

    Portage de 001_ON3RT_live/services/data_sources/test_source.py,
    inchangé.
=========================================================
"""

from .base import LiveDataSource


class TestLiveDataSource(LiveDataSource):
    """
    Fournisseur de test. `push_state(**overrides)` simule un nouvel
    état (fusionné sur le dernier état connu) et émet `updated`
    immédiatement.

    N'émet jamais que les clés explicitement données au constructeur
    ou à push_state() — jamais le contrat DEFAULT_STATE complet
    (voir la mise en garde dans base.py) : LiveService fournit déjà
    ses propres valeurs par défaut pour toute clé qu'aucune source
    n'a encore renseignée, et ce fournisseur ne doit pas écraser les
    clés dont d'autres sources seraient responsables si on le combine
    à l'une d'elles dans un test.
    """

    def __init__(self, initial_state=None, parent=None):
        super().__init__(parent)

        self._started = False
        self._state = dict(initial_state) if initial_state else {}

    # -----------------------------------------------------
    # Cycle de vie
    # -----------------------------------------------------

    def start(self):
        self._started = True
        self.updated.emit(dict(self._state))

    def stop(self):
        self._started = False

    @property
    def started(self):
        """Utilisable dans les assertions de test."""

        return self._started

    # -----------------------------------------------------
    # Contrôle depuis un test
    # -----------------------------------------------------

    def push_state(self, **overrides):
        """
        Simule un nouvel état : part du dernier état connu, applique
        les valeurs fournies, et émet `updated` immédiatement.
        Utilisable avant même start(), pour préparer un état initial.
        """

        self._state.update(overrides)
        self.updated.emit(dict(self._state))

    def reset(self):
        """Réinitialise l'état interne (entre deux tests)."""

        self._state = {}
