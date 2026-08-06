#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Map Layers — Station Layer
=========================================================
Description :
    Dessine la position de la station elle-même, lue directement depuis
    StationService (injecté au constructeur, jamais construit ici -- même
    convention que RadioPanel/live_service). Position STATIQUE (change
    seulement si l'opérateur modifie les paramètres Station), donc lue
    par injection directe plutôt que via l'état partagé "state" de
    paint() -- voir le contrat MapLayer (base.py) : state reste pour les
    couches dont la donnée change en direct (DX Cluster, propagation...).

    N'affiche RIEN tant que latitude/longitude ne sont pas configurées
    sur StationService (None) : aucune position inventée. locator N'EST
    PAS recalculé ici -- lit StationService.locator tel quel (le
    correctif "locator dérivé de lat/lon" est une étape ultérieure
    volontairement différée, voir project_dashboard_radio_panel /
    project_map_panel_architecture).
=========================================================
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from apps.dashboard.map_layers.base import disk_geometry, unit_to_pixel

_MARKER_COLOR = QColor("#00dfff")
_MARKER_BORDER_COLOR = QColor("#052033")
_HALO_COLOR = QColor(0, 223, 255, 60)
_LABEL_COLOR = QColor("#edf2fb")
_MARKER_RADIUS_PX = 6.5
_HALO_RADIUS_PX = 13.0


class StationLayer:
    """Voir docstring du module. Aucune connaissance de LiveService/DX Cluster/etc."""

    def __init__(self, station_service):
        self._station_service = station_service

        self._label_font = QFont()
        self._label_font.setPointSize(9)
        self._label_font.setBold(True)

    def paint(self, painter, projection, rect, state) -> None:
        latitude = self._station_service.latitude
        longitude = self._station_service.longitude

        if latitude is None or longitude is None:
            return

        center, radius = disk_geometry(rect)

        x, y = projection.project(latitude, longitude)
        point = unit_to_pixel(x, y, center, radius)

        # Halo discret (2026-08-02, ajustement demandé) -- rend le
        # marqueur plus visible sans dominer la carte.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_HALO_COLOR)
        painter.drawEllipse(point, _HALO_RADIUS_PX, _HALO_RADIUS_PX)

        painter.setPen(_MARKER_BORDER_COLOR)
        painter.setBrush(_MARKER_COLOR)
        painter.drawEllipse(point, _MARKER_RADIUS_PX, _MARKER_RADIUS_PX)

        callsign = self._station_service.callsign
        if callsign:
            painter.setFont(self._label_font)
            painter.setPen(_LABEL_COLOR)
            painter.drawText(point.x() + _MARKER_RADIUS_PX + 5, point.y() + 4, callsign)
