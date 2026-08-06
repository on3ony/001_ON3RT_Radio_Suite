#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_band_activity_counting.py
-------------------------------------------------
ON3RT Radio Suite - Verification en lecture seule du comptage
d'activite par bande (chantier "Tuile Activite par bande")

Ne modifie AUCUN code de production. Ouvre sa PROPRE connexion DX
Cluster (independante de celle de la Suite deja lancee, aucun conflit
possible -- DXClusterService/DXFun acceptent plusieurs clients) et
tient, en parallele de la fonction reelle de production
(band_activity_source.compute_band_counts), un comptage totalement
independant, spot par spot, pendant la duree d'ecoute -- pour prouver
empiriquement que compute_band_counts() ne perd ni ne double aucun
spot recu.

Ce script repond precisement aux 3 points demandes :
    1. tous les spots recus sont-ils pris en compte ?
    2. un filtrage involontaire elimine-t-il des spots ?
    3. les compteurs correspondent-ils aux donnees reelles de
       DXClusterService.recent_spots() ?

Usage :
    python validate_band_activity_counting.py [--duration 300]
"""

from __future__ import annotations

import argparse
from collections import Counter

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from apps.dashboard.data_sources.band_activity_source import compute_band_counts
from libraries.dxcluster.dxcluster_service import DXClusterService
from libraries.station.station_service import StationService

_DEFAULT_DURATION_S = 300.0


def _wait(seconds: float) -> None:
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifie le comptage d'activite par bande contre le flux DX Cluster reel")
    parser.add_argument("--duration", type=float, default=_DEFAULT_DURATION_S, help="Duree d'ecoute (s), defaut 300 (5 min)")
    args = parser.parse_args()

    print("=" * 70)
    print("ON3RT Radio Suite - Verification du comptage d'activite par bande")
    print("=" * 70)
    print("Lecture seule -- aucun code de production modifie.")
    print("Ouvre une connexion DX Cluster independante (aucun conflit avec")
    print("une Suite deja lancee).")
    print(f"Ecoute pendant {args.duration:.0f}s -- chaque spot recu est affiche")
    print("en direct, avec un comptage independant par bande.")
    print("=" * 70)

    app = QApplication.instance() or QApplication([])

    station_service = StationService()
    service = DXClusterService(station_service=station_service)

    independent_tally = Counter()
    all_spots_seen = []

    def _on_spot(spot: dict) -> None:
        band = spot.get("band")
        independent_tally[band] += 1
        all_spots_seen.append(spot)
        print(f"[SPOT] {spot.get('time_utc')} UTC  {spot.get('frequency_khz')} kHz  "
              f"band={band}  dx={spot.get('dx_callsign')}  spotter={spot.get('spotter')}")

    def _on_connection_changed(ok: bool) -> None:
        print(f"\n[CONNEXION] {'connecte' if ok else 'deconnecte'}\n")

    service.spot_received.connect(_on_spot)
    service.connectionChanged.connect(_on_connection_changed)

    service.connect()

    try:
        _wait(args.duration)
    except KeyboardInterrupt:
        print("\nArret demande (Ctrl+C).")
    finally:
        service.disconnect()

    print("\n" + "=" * 70)
    print("RESULTATS")
    print("=" * 70)
    print(f"Spots recus pendant l'ecoute : {len(all_spots_seen)}")
    print(f"recent_spots() contient      : {len(service.recent_spots())} spot(s)")

    if len(all_spots_seen) != len(service.recent_spots()):
        print("\nATTENTION : le nombre de spots recus (signal spot_received) ne")
        print("correspond pas au nombre de spots dans recent_spots() -- verifier")
        print("le deque MAX_SPOTS (=100) de DXClusterService : possible troncature")
        print("si plus de 100 spots sont arrives pendant l'ecoute.")

    print("\nComptage independant (spot par spot, pendant l'ecoute) vs")
    print("compute_band_counts() (fonction reelle de production, sur")
    print("recent_spots(), fenetre glissante 15 min) :\n")

    computed = compute_band_counts(service.recent_spots())

    all_bands = sorted(set(independent_tally) | set(computed))
    mismatches = []

    print(f"  {'Bande':<8} {'Independant':>12} {'compute_band_counts':>22}")
    for band in all_bands:
        independent_count = independent_tally.get(band, 0)
        computed_count = computed.get(band, {}).get("count", 0)
        flag = "" if independent_count == computed_count else "  <-- ECART"
        if flag:
            mismatches.append(band)
        print(f"  {band:<8} {independent_count:>12} {computed_count:>22}{flag}")

    print("\n" + "=" * 70)
    if not mismatches:
        print("PASS : chaque bande ayant recu un spot pendant l'ecoute est")
        print("fidelement reprise par compute_band_counts() -- aucun spot perdu,")
        print("aucun filtrage involontaire detecte sur cette fenetre d'observation.")
        return 0
    else:
        print(f"ECART detecte sur : {', '.join(mismatches)}")
        print("Cause probable si l'ecart persiste : un spot recu tres tot pendant")
        print("l'ecoute est sorti de la fenetre glissante de 15 minutes au moment")
        print("du calcul final (comportement attendu, pas un bug, si l'ecoute a")
        print("dure plus de 15 minutes) -- reduire --duration a moins de 15 min")
        print("pour eliminer cette explication et confirmer un vrai probleme.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
