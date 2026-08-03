#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Map Layers — Grayline Layer
=========================================================
Description :
    Trace la ligne du terminateur jour/nuit (grayline) sur la Carte,
    projetée via la projection courante du MapPanel (voir
    apps/dashboard/map_layers/base.py pour le contrat MapLayer et les
    utilitaires de conversion disque unité -> écran).

    AUCUN calcul astronomique ici : les points du terminateur viennent
    exclusivement de libraries/geo/solar.py (terminator_points()) --
    cette couche ne fait que projeter et dessiner, exactement comme
    WorldOutlineLayer ne fait que projeter et dessiner les contours des
    continents, jamais de la géométrie sphérique elle-même. La
    classification jour/nuit/terminateur d'un point (libraries/geo/
    grayline.py, daylight_zone()/DaylightZone) n'est PAS encore
    utilisée ici : elle sera le point d'entrée naturel d'un futur
    remplissage jour/nuit (voir plus bas), volontairement pas encore
    implémenté à cette étape.

    Rafraîchissement (recalcul sans travail inutile) : le terminateur
    ne se déplace que d'environ 0.25°/minute (360° en 24h) -- un
    recalcul à chaque paint() serait un pur gaspillage, alors que
    paint() peut être appelé très fréquemment (state_changed de
    LiveService fait redessiner tout le canevas, voir _MapCanvas dans
    apps/dashboard/panels/map_panel.py, sans rapport avec l'heure).
    Le terminateur est donc mis en cache et recalculé au plus une fois
    par _RECOMPUTE_INTERVAL_SECONDS, jamais à chaque appel de paint().

    Support futur du remplissage jour/nuit (pas encore implémenté,
    volontairement -- voir contrainte du chantier) : le tracé est déjà
    dessiné comme un polygone fermé (painter.drawPolygon(), avec une
    brosse explicitement NoBrush) plutôt qu'une simple polyligne
    ouverte -- exactement la structure dont une future étape aurait
    besoin pour remplir l'hémisphère nocturne (il suffira alors de
    changer la brosse et de s'appuyer sur grayline.daylight_zone()),
    sans qu'aucun code de remplissage n'existe pour l'instant.
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPen, QPolygonF

from apps.dashboard.map_layers.base import disk_geometry, unit_to_pixel
from libraries.geo.solar import terminator_points

# Ambré -- évoque la limite jour/nuit, distinct du bleu de
# WorldOutlineLayer et du cyan de StationLayer.
_LINE_COLOR = QColor(255, 204, 51, 220)
_LINE_WIDTH_PX = 1.6

# Voir docstring du module (paragraphe "Rafraîchissement").
_RECOMPUTE_INTERVAL_SECONDS = 60.0


class GraylineLayer:
    """Voir docstring du module. Aucune connaissance de LiveService/StationService/DX Cluster."""

    def __init__(self, now_func: Callable[[], datetime] | None = None):
        # now_func injectable (tests) -- par défaut l'heure UTC réelle,
        # jamais un datetime naïf (voir libraries/geo/solar.py).
        self._now_func = now_func or (lambda: datetime.now(timezone.utc))

        self._cached_moment: datetime | None = None
        self._cached_points: list[tuple[float, float]] | None = None

    def _refresh_terminator_if_stale(self) -> None:
        """Recalcule le terminateur seulement si le cache est absent ou plus vieux que _RECOMPUTE_INTERVAL_SECONDS."""

        now = self._now_func()

        if (
            self._cached_points is not None
            and self._cached_moment is not None
            and (now - self._cached_moment).total_seconds() < _RECOMPUTE_INTERVAL_SECONDS
        ):
            return

        self._cached_moment = now
        self._cached_points = terminator_points(now)

    def paint(self, painter, projection, rect, state) -> None:
        self._refresh_terminator_if_stale()

        center, radius = disk_geometry(rect)

        polygon = QPolygonF()
        for latitude, longitude in self._cached_points:
            x, y = projection.project(latitude, longitude)
            polygon.append(unit_to_pixel(x, y, center, radius))

        painter.setPen(QPen(_LINE_COLOR, _LINE_WIDTH_PX))
        painter.setBrush(Qt.BrushStyle.NoBrush)  # remplissage jour/nuit : brique future, voir docstring du module
        painter.drawPolygon(polygon)
