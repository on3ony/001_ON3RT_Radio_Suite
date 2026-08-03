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
    exclusivement de libraries/geo/solar.py (terminator_points()), et
    la classification jour/nuit exclusivement de libraries/geo/
    grayline.py (daylight_zone()/DaylightZone) -- cette couche ne fait
    que projeter et dessiner, exactement comme WorldOutlineLayer ne
    fait que projeter et dessiner les contours des continents, jamais
    de la géométrie sphérique elle-même.

    Rafraîchissement (recalcul sans travail inutile) : le terminateur
    ne se déplace que d'environ 0.25°/minute (360° en 24h) -- un
    recalcul à chaque paint() serait un pur gaspillage, alors que
    paint() peut être appelé très fréquemment (state_changed de
    LiveService fait redessiner tout le canevas, voir _MapCanvas dans
    apps/dashboard/panels/map_panel.py, sans rapport avec l'heure).
    Le terminateur est donc mis en cache et recalculé au plus une fois
    par _RECOMPUTE_INTERVAL_SECONDS, jamais à chaque appel de paint().
    La classification jour/nuit du centre de la carte (voir plus bas)
    reste en revanche recalculée à chaque paint() : un unique appel à
    daylight_zone() est négligeable (quelques sin/cos), et elle dépend
    du centre de projection courant -- jamais mise en cache pour rester
    correcte même si ce centre venait à changer entre deux appels.

    Remplissage jour/nuit : le tracé du terminateur (terminator_points())
    est un grand cercle fermé -- projeté, il délimite donc exactement
    deux régions du disque cartographique, l'une couvrant l'hémisphère
    diurne, l'autre l'hémisphère nocturne (théorème de la courbe de
    Jordan ; vrai pour toute projection continue, y compris l'azimutale
    équidistante utilisée ici). Reste à savoir laquelle des deux est la
    nuit : le centre de la carte (projection.center_latitude/
    center_longitude) est classifié une fois via grayline.daylight_zone()
    -- s'il est nocturne, on remplit l'intérieur du polygone du
    terminateur ; sinon (jour ou bande TERMINATOR, traitée comme le
    jour), on remplit son complément dans le disque (QPainterPath en
    règle pair-impair, ellipse du disque moins le polygone). Voir
    _paint_night_fill().
=========================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainterPath, QPen, QPolygonF

from apps.dashboard.map_layers.base import disk_geometry, unit_to_pixel
from libraries.geo.grayline import DaylightZone, daylight_zone
from libraries.geo.solar import terminator_points


@dataclass(frozen=True, slots=True)
class GraylineStyle:
    """
    Regroupe tous les paramètres visuels de GraylineLayer -- injectable
    au constructeur (GraylineLayer(style=...), voir _DEFAULT_STYLE plus
    bas pour la valeur par défaut) pour permettre une personnalisation
    programmatique (tests, futurs styles alternatifs). Toujours aucune
    préférence utilisateur ni paramètre persisté à cette étape : aucune
    lecture de configuration, aucune UI de réglage -- juste le point
    d'entrée que cette future étape utilisera.

    Couleur et opacité restent deux champs séparés (plutôt qu'une seule
    QColor opaque) pour rester ajustables indépendamment ; line_color/
    night_fill_color reconstruisent la QColor correspondante à la
    demande, jamais mise en cache ici (construction QColor négligeable).

    Ligne du terminateur : ambré (famille des accents chauds déjà
    utilisés ailleurs dans le Dashboard, ex. apps/dashboard/widgets/
    smeter_bar.py #ffe066/#ffb454) -- volontairement distinct du bleu
    de WorldOutlineLayer (#5a8fd6) et du cyan de StationLayer
    (#00dfff), pour se distinguer clairement du fond de carte comme du
    marqueur de station, tout en restant dans la palette sombre de la
    Suite.

    Remplissage nocturne : voile sombre semi-transparent, dans la même
    famille que l'océan de WorldOutlineLayer (#0a1122) -- suffisamment
    opaque pour assombrir nettement la nuit, mais assez transparent
    pour laisser deviner le fond de carte en dessous (l'objectif est
    d'assombrir, pas de masquer).
    """

    line_color_rgb: tuple[int, int, int] = (255, 204, 51)
    line_opacity: int = 220  # 0-255 -- légère transparence, jamais un trait plein dur
    line_width_px: float = 1.6

    night_fill_color_rgb: tuple[int, int, int] = (5, 10, 25)
    night_fill_opacity: int = 110  # 0-255

    @property
    def line_color(self) -> QColor:
        return QColor(*self.line_color_rgb, self.line_opacity)

    @property
    def night_fill_color(self) -> QColor:
        return QColor(*self.night_fill_color_rgb, self.night_fill_opacity)


_DEFAULT_STYLE = GraylineStyle()

# Voir docstring du module (paragraphe "Rafraîchissement").
_RECOMPUTE_INTERVAL_SECONDS = 60.0


class GraylineLayer:
    """Voir docstring du module. Aucune connaissance de LiveService/StationService/DX Cluster."""

    def __init__(
        self,
        style: GraylineStyle | None = None,
        now_func: Callable[[], datetime] | None = None,
    ):
        # style injectable -- par défaut _DEFAULT_STYLE (voir docstring
        # de GraylineStyle), rendu strictement identique tant qu'aucun
        # style personnalisé n'est fourni.
        self._style = style or _DEFAULT_STYLE

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

    def _paint_night_fill(self, painter, polygon: QPolygonF, center, radius, projection) -> None:
        """Remplit l'hémisphère nocturne -- voir docstring du module (paragraphe "Remplissage jour/nuit")."""

        center_zone = daylight_zone(self._cached_moment, projection.center_latitude, projection.center_longitude)

        path = QPainterPath()
        if center_zone == DaylightZone.NIGHT:
            path.addPolygon(polygon)
        else:
            path.setFillRule(Qt.FillRule.OddEvenFill)
            path.addEllipse(center, radius, radius)
            path.addPolygon(polygon)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._style.night_fill_color)
        painter.drawPath(path)

    def paint(self, painter, projection, rect, state) -> None:
        self._refresh_terminator_if_stale()

        center, radius = disk_geometry(rect)

        polygon = QPolygonF()
        for latitude, longitude in self._cached_points:
            x, y = projection.project(latitude, longitude)
            polygon.append(unit_to_pixel(x, y, center, radius))

        self._paint_night_fill(painter, polygon, center, radius, projection)

        painter.setPen(QPen(self._style.line_color, self._style.line_width_px))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(polygon)
