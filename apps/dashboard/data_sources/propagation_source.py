#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Propagation Live Data Source
=========================================================
Description :
    Fournisseur LiveDataSource pour le service de propagation partagé
    de la suite (libraries/propagation/propagation_service.py —
    PropagationService, HamQSL, instancié une fois dans
    core/application.py).

    Se contente d'écouter les signaux propagation_updated/
    connectionChanged de l'instance partagée et de relayer l'état
    courant sous les clés "propagation_connected" et
    "propagation_data" (dict conforme au contrat figé de
    PropagationService, ou None tant qu'aucune donnée n'a encore été
    reçue).

    Aucune logique réseau, XML ou HamQSL ici : PropagationService
    reste seul responsable de ces aspects. Ce fournisseur n'est qu'un
    adaptateur entre le service partagé et LiveService, exactement
    comme WeatherLiveDataSource pour WeatherService.
=========================================================
"""

from .base import LiveDataSource

# Champs dont CE fournisseur est responsable — volontairement
# distinct de DEFAULT_STATE (base.py, contrat partagé par tous les
# fournisseurs) : voir la mise en garde dans base.py, déjà rencontrée
# avec le CAT, le Logbook, le DX Cluster et la météo.
DEFAULT_PROPAGATION_STATE = {
    "propagation_connected": False,
    "propagation_data": None,
}


class PropagationLiveDataSource(LiveDataSource):
    """
    Adaptateur entre PropagationService (service Suite partagé) et
    LiveService. N'effectue aucune requête réseau, ne parse aucun
    XML, ne maintient qu'une simple copie du dernier relevé reçu
    (pour pouvoir la retransmettre lors d'un changement de connexion
    sans avoir à interroger PropagationService) : relaie
    systématiquement l'état déjà produit par le service, jamais une
    donnée recalculée.
    """

    def __init__(self, propagation_service, parent=None):
        super().__init__(parent)

        self._service = propagation_service
        self._last_propagation = None

    # -----------------------------------------------------
    # Cycle de vie
    # -----------------------------------------------------

    def start(self):
        self._service.propagation_updated.connect(self._on_propagation_updated)
        self._service.connectionChanged.connect(self._on_connection_changed)
        self._emit_current_state()

    def stop(self):
        self._service.propagation_updated.disconnect(self._on_propagation_updated)
        self._service.connectionChanged.disconnect(self._on_connection_changed)

    # -----------------------------------------------------
    # Relais de PropagationService
    # -----------------------------------------------------

    def _on_propagation_updated(self, propagation):
        self._last_propagation = propagation
        self._emit_current_state()

    def _on_connection_changed(self, _connected):
        self._emit_current_state()

    def _emit_current_state(self):
        state = dict(DEFAULT_PROPAGATION_STATE)
        state["propagation_connected"] = self._service.connected
        state["propagation_data"] = self._last_propagation

        self.updated.emit(state)
