#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Map Layers — World Outline Layer
=========================================================
Description :
    Couche de fond de la Carte : océan (disque plein) puis contours des
    continents, projetés via la projection courante du MapPanel (voir
    apps/dashboard/map_layers/base.py pour le contrat MapLayer et les
    utilitaires de conversion disque unité -> écran).

    Données : assets/maps/world_outline_110m.json, converti UNE FOIS
    depuis Natural Earth (naturalearthdata.com, jeu "ne_110m_land",
    échelle 1:110m, domaine public, aucune attribution requise) --
    chargé au premier paint(), jamais reconstruit ensuite, aucun accès
    réseau à l'exécution.

    Limite assumée, propre à toute projection azimutale sur l'ensemble
    du globe (pas un défaut de ce fichier) : la distorsion croît avec la
    distance au centre, et un polygone qui traverse la région antipodale
    peut apparaître visuellement étiré -- comportement normal de ce type
    de projection (WSJT-X/DX Atlas présentent la même limite), pas une
    erreur de calcul.
=========================================================
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPolygonF

from apps.dashboard.map_layers.base import disk_geometry, unit_to_pixel

_DATA_PATH = Path(__file__).resolve().parents[3] / "assets" / "maps" / "world_outline_110m.json"

_OCEAN_COLOR = QColor("#0a1122")
# Contraste renforcé (2026-08-02, ajustement demandé) contre l'océan
# très sombre -- même famille de teintes du thème, juste éclaircie.
_LAND_FILL_COLOR = QColor("#28406b")
_LAND_BORDER_COLOR = QColor("#5a8fd6")


class WorldOutlineLayer:
    """Voir docstring du module. Aucune connaissance de LiveService/StationService."""

    def __init__(self, data_path=None):
        self._path = Path(data_path) if data_path else _DATA_PATH
        self._polygons: list[list[tuple[float, float]]] | None = None

    def _ensure_loaded(self) -> None:
        if self._polygons is not None:
            return

        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            self._polygons = [
                [(point[0], point[1]) for point in polygon]
                for polygon in data.get("polygons", [])
            ]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError):
            # Fichier de contours absent/corrompu : la Carte reste
            # utilisable (océan uni, sans contour) plutôt que de
            # planter tout le panneau -- aucune donnée inventée.
            self._polygons = []

    def paint(self, painter, projection, rect, state) -> None:
        self._ensure_loaded()

        center, radius = disk_geometry(rect)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_OCEAN_COLOR)
        painter.drawEllipse(center, radius, radius)

        painter.setPen(_LAND_BORDER_COLOR)
        painter.setBrush(_LAND_FILL_COLOR)

        for polygon in self._polygons:
            points = QPolygonF()
            for lat, lon in polygon:
                x, y = projection.project(lat, lon)
                points.append(unit_to_pixel(x, y, center, radius))

            painter.drawPolygon(points)
