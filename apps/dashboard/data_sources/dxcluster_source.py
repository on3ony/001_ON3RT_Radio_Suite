#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — DX Cluster Live Data Source
=========================================================
Description :
    Fournisseur LiveDataSource pour le DX Cluster partagé de la
    suite (libraries/dxcluster/dxcluster_service.py — DXClusterService,
    connexion Telnet unique vers DXFun, instanciée une fois dans
    core/application.py).

    Se contente d'écouter les signaux spot_received/connectionChanged
    de l'instance partagée et de relayer l'état courant sous les clés
    "dxcluster_connected" et "dxcluster_spots" (liste de dicts
    conformes au contrat de spot figé de DXClusterService).

    Aucune logique de connexion ni de parsing ici : DXClusterService
    reste seul responsable de ces aspects. Ce fournisseur n'est qu'un
    adaptateur entre le service partagé et LiveService, exactement
    comme LogbookLiveDataSource ne fait que relayer LogbookRepository
    sans jamais réimplémenter sa logique.
=========================================================
"""

from .base import LiveDataSource

# Champs dont CE fournisseur est responsable — volontairement
# distinct de DEFAULT_STATE (base.py, contrat partagé par tous les
# fournisseurs) : voir la mise en garde dans base.py, déjà rencontrée
# avec le CAT et le Logbook. Émettre le contrat complet à chaque
# relais écraserait, avec des valeurs par défaut, les clés dont
# d'autres fournisseurs sont responsables (ex. "logbook", "connected").
DEFAULT_DXCLUSTER_STATE = {
    "dxcluster_connected": False,
    "dxcluster_spots": [],
}


class DXClusterLiveDataSource(LiveDataSource):
    """
    Adaptateur entre DXClusterService (service Suite partagé) et
    LiveService. N'ouvre aucune connexion, ne parse aucune ligne, ne
    maintient aucun état propre : relaie systématiquement l'état
    déjà produit par le service (source unique de vérité).
    """

    def __init__(self, dxcluster_service, parent=None):
        super().__init__(parent)

        self._service = dxcluster_service

    # -----------------------------------------------------
    # Cycle de vie
    # -----------------------------------------------------

    def start(self):
        self._service.spot_received.connect(self._on_spot_received)
        self._service.connectionChanged.connect(self._on_connection_changed)
        self._emit_current_state()

    def stop(self):
        self._service.spot_received.disconnect(self._on_spot_received)
        self._service.connectionChanged.disconnect(self._on_connection_changed)

    # -----------------------------------------------------
    # Relais de DXClusterService
    # -----------------------------------------------------

    def _on_spot_received(self, _spot):
        self._emit_current_state()

    def _on_connection_changed(self, _connected):
        self._emit_current_state()

    def _emit_current_state(self):
        state = dict(DEFAULT_DXCLUSTER_STATE)
        state["dxcluster_connected"] = self._service.connected
        state["dxcluster_spots"] = self._service.recent_spots()

        self.updated.emit(state)
