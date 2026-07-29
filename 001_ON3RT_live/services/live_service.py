#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT LIVE
Live Service
Version : 2.2.0
Auteur : ON3RT
Description :
    Couche d'abstraction unique entre ON3RT Live et n'importe quel(s)
    fournisseur(s) de données d'état station ("Data Source", voir
    data_sources/). Aucun panneau ne communique jamais directement
    avec un fournisseur : ils n'utilisent que LiveService.state() et
    le signal state_changed.

    LiveService peut combiner plusieurs fournisseurs à la fois — ex.
    le CAT (fréquence/mode/bande/PTT) et le Logbook (derniers QSO)
    simultanément : chacun ne pousse que les clés dont il est
    responsable (voir data_sources/base.py), fusionnées dans un seul
    état partagé. LiveService ne connaît lui-même aucun détail d'un
    fournisseur (fichier local, réseau, base de données...),
    seulement l'interface commune LiveDataSource : il se contente
    d'écouter leur signal `updated` et de relayer l'état fusionné.
    Pour changer ou ajouter un fournisseur — ex. brancher demain une
    autre installation ON3RT Radio Suite sur le réseau local,
    appartenant à un autre radioamateur — il suffit de l'injecter au
    constructeur ; aucune autre ligne de l'application (dashboard.py,
    panels/*.py) n'a besoin de changer.

    Par défaut, si aucun fournisseur n'est fourni, LiveService
    utilise LocalFileLiveDataSource (mode actuel : installation
    locale de la suite).
=========================================================
"""

from PySide6.QtCore import QObject, Signal

from .data_sources import DEFAULT_STATE, LocalFileLiveDataSource


class LiveService(QObject):
    """
    Diffuse l'état courant de la station (fourni par un ou plusieurs
    LiveDataSource) via le signal state_changed.
    """

    state_changed = Signal(dict)

    def __init__(self, source=None, path=None, parent=None):

        super().__init__(parent)

        self._state = dict(DEFAULT_STATE)

        if source is None:
            sources = [LocalFileLiveDataSource(path=path)]
        elif isinstance(source, (list, tuple)):
            sources = list(source)
        else:
            sources = [source]

        self._sources = sources

        for src in self._sources:
            src.setParent(self)
            src.updated.connect(self._handle_source_update)
            src.start()

    # -----------------------------------------------------
    # Relais des sources actives
    # -----------------------------------------------------

    def _handle_source_update(self, partial_state):
        """
        Slot connecté à LiveDataSource.updated. Fusionne l'état reçu
        dans l'état courant (un fournisseur ne modifie que les clés
        dont il est responsable) et diffuse le résultat aux panneaux
        via state_changed.
        """

        if isinstance(partial_state, dict):
            self._state.update(partial_state)

        self.state_changed.emit(dict(self._state))

    def state(self):
        """Retourne une copie de l'état courant (sans solliciter les sources)."""

        return dict(self._state)
