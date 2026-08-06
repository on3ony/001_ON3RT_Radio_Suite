#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Map Panel
=========================================================
Description :
    Panneau CARTE : moteur de rendu totalement indépendant des couches
    (voir apps/dashboard/map_layers/base.py pour le contrat MapLayer).
    MapPanel ne connaît ni DX Cluster, ni PSK Reporter, ni grayline, ni
    aucune autre notion métier -- il possède une Projection (contrat
    libraries/geo/projection.py) et une liste ordonnée de MapLayer,
    et se contente d'appeler layer.paint(painter, projection, rect,
    state) pour chacune, dans l'ordre (l'ordre de la liste fixe
    l'empilement visuel). Ajouter une future couche (Grayline, DX
    Cluster, PSK Reporter, satellites, propagation, balises...) ne
    demande jamais de modifier ce fichier -- seulement d'ajouter la
    couche à la liste construite par l'appelant (core/application.py à
    terme), jamais de toucher MapPanel lui-même.

    Projection centrée sur la station (StationService.latitude/
    longitude), construite une seule fois à l'initialisation. Si la
    station n'est pas encore configurée (latitude/longitude à None),
    la projection est centrée sur (0, 0) par repli -- StationLayer
    n'affichera alors simplement aucun marqueur (voir sa docstring),
    mais WorldOutlineLayer reste utilisable.

    Structure : QFrame (même habillage que les autres panneaux du
    Dashboard -- titre "🌍 CARTE", bordure/fond du thème ON3RT Dark)
    contenant un canevas dédié (_MapCanvas, QWidget) où tout le rendu
    des couches a lieu -- jamais directement dans le QFrame, pour ne
    jamais mélanger le style Qt (QSS, bordure arrondie) avec la
    peinture manuelle des couches.
=========================================================
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from apps.dashboard.map_layers.station_layer import StationLayer
from apps.dashboard.map_layers.world_outline_layer import WorldOutlineLayer
from libraries.geo.projection import AzimuthalEquidistantProjection


class _MapCanvas(QWidget):
    """
    Surface de dessin dédiée : itère uniquement les couches fournies,
    ne connaît jamais leur contenu -- voir docstring du module.
    """

    def __init__(self, layers, projection, live_service=None, parent=None):
        super().__init__(parent)

        self._layers = layers
        self._projection = projection
        self._live_service = live_service

        if self._live_service is not None:
            self._live_service.state_changed.connect(lambda _state: self.update())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        state = self._live_service.state() if self._live_service is not None else {}

        for layer in self._layers:
            painter.save()
            layer.paint(painter, self._projection, rect, state)
            painter.restore()


class MapPanel(QFrame):

    def __init__(self, station_service, live_service=None, layers=None, parent=None):
        super().__init__(parent)

        self.setStyleSheet("""
            QFrame{
                background:#112743;
                border:2px solid #00cfff;
                border-radius:12px;
            }

            QLabel{
                color:white;
                border:none;
            }
        """)

        layout = QVBoxLayout(self)

        titre = QLabel("🌍 CARTE")

        font = QFont()
        font.setPointSize(15)
        font.setBold(True)

        titre.setFont(font)
        titre.setAlignment(Qt.AlignmentFlag.AlignCenter)

        titre.setStyleSheet("""
            color:#00dfff;
            padding:8px;
        """)

        layout.addWidget(titre)

        center_latitude = station_service.latitude if station_service.latitude is not None else 0.0
        center_longitude = station_service.longitude if station_service.longitude is not None else 0.0
        projection = AzimuthalEquidistantProjection(center_latitude, center_longitude)

        if layers is None:
            layers = [WorldOutlineLayer(), StationLayer(station_service)]

        self.canvas = _MapCanvas(layers, projection, live_service=live_service)
        layout.addWidget(self.canvas, stretch=1)
