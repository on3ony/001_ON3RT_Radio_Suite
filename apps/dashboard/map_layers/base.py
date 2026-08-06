#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Map Layers — Contrat MapLayer
=========================================================
Description :
    Contrat commun à toute couche de la Carte (apps/dashboard/panels/
    map_panel.py -- MapPanel). Duck-typé, comme tous les contrats de la
    Suite (MorseDecodeEngine, LiveDataSource...) : aucune classe de base,
    aucun isinstance()/type() nulle part.

    Une couche expose une seule méthode :

        paint(painter, projection, rect, state)

            painter    : QPainter déjà actif (MapPanel gère
                         save()/restore() autour de chaque couche --
                         une couche peut modifier pinceau/stylo/police
                         librement sans affecter les autres).
            projection : contrat Projection (libraries/geo/projection.py)
                         -- UNIQUEMENT project(lat, lon) -> (x, y) dans
                         le disque unité [-1, 1]. Une couche ne fait
                         jamais sa propre trigonométrie de projection.
            rect       : QRect/QRectF de la zone de dessin disponible
                         (le canevas de la Carte, PAS tout le panneau --
                         voir MapPanel, le titre a sa propre zone).
            state      : dict, l'état partagé courant (LiveService),
                         pour les couches qui en ont besoin (DX Cluster,
                         propagation, PSK Reporter...). Une couche qui
                         n'en a pas besoin (WorldOutlineLayer,
                         StationLayer -- alimentée par injection directe
                         de service au constructeur) l'ignore simplement.

    MapPanel ne connaît JAMAIS le contenu d'une couche : il se contente
    d'itérer une liste de MapLayer et d'appeler paint() sur chacune,
    dans l'ordre de la liste (une couche peut donc être dessinée par-
    dessus une autre -- c'est l'ordre de la liste qui fixe l'empilement,
    jamais une notion de "z-index" portée par la couche elle-même).

    disk_geometry()/unit_to_pixel() ci-dessous sont des fonctions
    utilitaires PURES partagées par toute couche ayant besoin de
    convertir une coordonnée normalisée (sortie de Projection.project())
    en un point écran réel -- centralisées ici pour que toutes les
    couches utilisent exactement la même géométrie de disque (même
    centre, même rayon, même marge), sans que cela crée de dépendance
    entre couches : une couche qui n'en a pas besoin ne les importe
    simplement pas.
=========================================================
"""

from __future__ import annotations

from PySide6.QtCore import QPointF

# Marge laissée entre le bord du widget et le bord du disque
# cartographique (0.98 = 2% de marge, ajustement demandé 2026-08-02 --
# le disque occupe volontairement presque tout le canevas), tout en
# évitant de coller strictement le tracé aux bords du panneau.
_DISK_MARGIN_RATIO = 0.98


def disk_geometry(rect) -> tuple[QPointF, float]:
    """
    Retourne (centre, rayon) du disque cartographique inscrit dans
    rect, avec une petite marge (_DISK_MARGIN_RATIO). Toute couche a
    besoin de cette même géométrie pour placer ses points -- centralisé
    ici pour que toutes les couches s'accordent exactement.
    """

    radius = min(rect.width(), rect.height()) / 2.0 * _DISK_MARGIN_RATIO
    center = QPointF(rect.center())

    return center, radius


def unit_to_pixel(x: float, y: float, center: QPointF, radius: float) -> QPointF:
    """
    Convertit une coordonnée normalisée (x, y dans le disque unité, y
    positif = nord -- voir libraries/geo/projection.py) en QPointF
    écran. L'axe y est inversé ici (jamais dans Projection) : l'écran
    croît vers le bas, le nord géographique vers le haut.
    """

    return QPointF(center.x() + x * radius, center.y() - y * radius)
