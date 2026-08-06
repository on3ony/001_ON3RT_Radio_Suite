#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Band Activity Live Data Source
=========================================================
Description :
    Fournisseur LiveDataSource pour la tuile "Activité par bande"
    (BandActivityPanel). Réutilise exclusivement le flux DX Cluster
    déjà partagé de la suite (libraries/dxcluster/dxcluster_service.py
    — DXClusterService, instancié une fois dans core/application.py) :
    aucune connexion, aucun sondage, aucun stockage de spot propre —
    ce fournisseur ne fait que recalculer, à chaque nouveau spot reçu
    (signal spot_received), un comptage par bande à partir de
    DXClusterService.recent_spots() (déjà tenu à jour par le service
    partagé, contrat de spot figé comprenant "band" et "received_at").

    Entièrement événementiel : aucun QTimer ici. Le comptage se
    recalcule au fil des spots reçus (n'importe quelle bande), ce qui
    rafraîchit en pratique toutes les bandes à chaque événement DX
    Cluster — pas de sondage périodique supplémentaire, conformément
    au flux déjà événementiel de DXClusterService. Limite acceptée
    explicitement (demande utilisateur : pas de polling ajouté) : si
    plus aucun spot n'arrive sur AUCUNE bande pendant un long moment,
    un compteur ne redescend pas tout seul avant le spot suivant.

    Calcul métier (fenêtre glissante + seuils de couleur) : entièrement
    ici, jamais dans BandActivityPanel (simple composant d'affichage,
    voir sa docstring). Constantes regroupées ci-dessous, modifiables
    sans toucher au reste du fichier.

    Sortie : state["bands"] = {"<nom_bande>": {"count": int, "color": "#RRGGBB"}, ...}
    pour TOUTES les bandes de BandManager.BANDS (jamais filtré par
    classe de licence ici : ce fournisseur ne connaît pas
    StationService — le filtrage par classe de licence reste
    exclusivement la responsabilité de BandActivityPanel, via
    libraries/radio/license_privileges.py). Une bande sans spot récent
    obtient count=0, color=COLOR_NONE (jamais absente du dict dès que
    ce fournisseur a émis au moins une fois).
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from libraries.radio.band_manager import BandManager

from .base import LiveDataSource

# ----------------------------------------------------------------------
# Constantes ajustables -- fenêtre glissante et seuils de couleur.
# Regroupées ici volontairement (demande explicite de l'utilisateur) :
# c'est le seul endroit à modifier pour affiner ces valeurs plus tard.
# ----------------------------------------------------------------------

WINDOW_MINUTES = 15

THRESHOLD_LOW_MAX = 3       # 1 à 3 spots   -> COLOR_LOW
THRESHOLD_MEDIUM_MAX = 8    # 4 à 8 spots   -> COLOR_MEDIUM
                             # 9 et plus     -> COLOR_HIGH

COLOR_NONE = "#5f6e8a"      # gris  -- 0 spot (aucune activité)
COLOR_LOW = "#2ed17e"       # vert  -- 1 à 3 spots (activité faible)
COLOR_MEDIUM = "#e8a63d"    # jaune -- 4 à 8 spots (activité moyenne)
COLOR_HIGH = "#f0464f"      # rouge -- 9 spots et plus (activité forte)


def color_for_spot_count(count: int) -> str:
    """Couleur associée à un nombre de spots sur la fenêtre glissante (voir seuils ci-dessus)."""

    if count <= 0:
        return COLOR_NONE
    if count <= THRESHOLD_LOW_MAX:
        return COLOR_LOW
    if count <= THRESHOLD_MEDIUM_MAX:
        return COLOR_MEDIUM
    return COLOR_HIGH


def _parse_received_at(value):
    """Parse le timestamp ISO 8601 UTC de DXClusterService (voir son contrat, suffixe 'Z'). None si absent/invalide."""

    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def compute_band_counts(spots, *, window_minutes: int = WINDOW_MINUTES, now=None) -> dict:
    """
    Calcule {"<bande>": {"count": int, "color": "#RRGGBB"}, ...} pour
    TOUTES les bandes de BandManager.BANDS, à partir de `spots` (liste
    de dicts conformes au contrat DXClusterService — champs "band" et
    "received_at" utilisés ici). Un spot sans "band" exploitable ou
    hors fenêtre glissante est ignoré silencieusement (jamais de
    plantage sur une donnée incomplète).
    """

    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=window_minutes)

    counts = {band.name: 0 for band in BandManager.BANDS}

    for spot in spots:
        band = spot.get("band")
        if band not in counts:
            continue

        received_at = _parse_received_at(spot.get("received_at"))
        if received_at is None or received_at < cutoff:
            continue

        counts[band] += 1

    return {
        band: {"count": count, "color": color_for_spot_count(count)}
        for band, count in counts.items()
    }


class BandActivityLiveDataSource(LiveDataSource):
    """
    Adaptateur entre DXClusterService (service Suite partagé) et
    LiveService : agrège les spots récents par bande (fenêtre
    glissante WINDOW_MINUTES) à chaque nouveau spot reçu. N'ouvre
    aucune connexion, ne stocke aucun spot propre — recent_spots()
    de DXClusterService reste l'unique source des spots (aucun
    doublon de données).
    """

    def __init__(self, dxcluster_service, parent=None):
        super().__init__(parent)

        self._service = dxcluster_service

    # -----------------------------------------------------
    # Cycle de vie
    # -----------------------------------------------------

    def start(self):
        self._service.spot_received.connect(self._on_spot_received)
        self._emit_current_state()

    def stop(self):
        self._service.spot_received.disconnect(self._on_spot_received)

    # -----------------------------------------------------
    # Relais agrégé de DXClusterService
    # -----------------------------------------------------

    def _on_spot_received(self, _spot):
        self._emit_current_state()

    def _emit_current_state(self):
        self.updated.emit({"bands": compute_band_counts(self._service.recent_spots())})
