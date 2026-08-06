#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
libraries/cat/cat_sharing_service.py
=========================================================
Description :
    Service de partage CAT générique et protocole-agnostique. Expose à
    des adaptateurs (contrat CatAdapter, voir
    libraries/cat/cat_adapters/base.py) un sous-ensemble volontairement
    réduit de RadioService (apps/cat_server/radio_service.py) --
    fréquence, mode, PTT, état de connexion -- jamais les capacités
    internes de la Suite (CW, S-mètre, VFO...).

    RadioService reste l'unique propriétaire du port physique et n'est
    en rien modifié par ce service : CatSharingService ne fait que
    déléguer à son API déjà publique (propriétés connected/frequency/
    mode, méthodes set_frequency()/set_mode()/set_ptt() déjà
    existantes). Reçu par injection au constructeur, jamais construit
    ici -- même convention que tout autre service partagé de la Suite.

    Aucune communication réseau ici, aucun protocole concret : ce
    fichier ne connaît ni rigctld, ni WebSocket, ni aucune autre
    technologie de transport -- voir libraries/cat/cat_adapters/ pour
    les implémentations concrètes, ajoutées une par une sans jamais
    modifier ce service ni RadioService. Même principe que MapPanel/
    MapLayer (apps/dashboard/map_layers/base.py) : un moteur générique
    qui itère une liste d'objets à contrat fixe, sans jamais connaître
    leur contenu.
=========================================================
"""

from __future__ import annotations

from PySide6.QtCore import QObject


class CatSharingService(QObject):
    """
    Façade générique + registre d'adaptateurs autour de RadioService.
    Ne connaît jamais le contenu d'un adaptateur (voir CatAdapter) --
    se contente d'appeler start()/stop() sur chacun, dans l'ordre
    d'ajout.
    """

    def __init__(self, radio_service, parent=None):
        super().__init__(parent)

        self._radio_service = radio_service
        self._adapters = []

    # ------------------------------------------------------------------
    # Registre d'adaptateurs
    # ------------------------------------------------------------------

    def add_adapter(self, adapter) -> None:
        """Enregistre un adaptateur (contrat CatAdapter), sans le démarrer."""

        self._adapters.append(adapter)

    def start_all(self) -> None:
        """Démarre tous les adaptateurs enregistrés, dans l'ordre d'ajout."""

        for adapter in self._adapters:
            adapter.start()

    def stop_all(self) -> None:
        """Arrête tous les adaptateurs enregistrés, dans l'ordre d'ajout."""

        for adapter in self._adapters:
            adapter.stop()

    # ------------------------------------------------------------------
    # Surface générique exposée aux adaptateurs -- volontairement
    # réduite à la fréquence/mode/PTT/état de connexion (jamais CW,
    # S-mètre, VFO : ces capacités restent internes à la Suite).
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._radio_service.connected

    def get_frequency_hz(self):
        return self._radio_service.frequency

    def set_frequency_hz(self, frequency_hz: int) -> bool:
        return self._radio_service.set_frequency(frequency_hz)

    def get_mode(self):
        return self._radio_service.mode

    def set_mode(self, mode: str) -> bool:
        return self._radio_service.set_mode(mode)

    def get_ptt(self) -> bool:
        return bool(self._radio_service.status.ptt)

    def set_ptt(self, state: bool) -> bool:
        return self._radio_service.set_ptt(state)

    def get_data_mode(self) -> bool:
        return self._radio_service.data_mode

    def set_data_mode(self, enabled: bool) -> bool:
        return self._radio_service.set_data_mode(enabled)
