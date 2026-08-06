"""
ON3RT Radio Suite
libraries/geo/great_circle.py

Distance et azimut initial entre deux points géographiques, sur une
Terre modélisée comme une sphère parfaite (formules du grand cercle --
haversine pour la distance, formule standard de relèvement initial pour
l'azimut). Indépendant de tout autre module de la Suite.

Rayon terrestre moyen : 6371.0 km (valeur standard IUGG, la même que
celle utilisée par la quasi-totalité des outils radioamateur de calcul
de distance/azimut). Précision suffisante pour un usage radioamateur
(l'écart entre un modèle sphérique et un modèle ellipsoïdal plus exact
reste de l'ordre de 0.3% au maximum, négligeable face à l'incertitude
de position d'une station DX).

Formules : haversine (distance) et relèvement initial (azimut) --
formules standard, largement documentées (ex. Aviation Formulary,
Ed Williams ; www.movable-type.co.uk/scripts/latlong.html).
"""

from __future__ import annotations

import math

_EARTH_RADIUS_KM = 6371.0


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance du grand cercle (km) entre deux points -- formule haversine."""

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return _EARTH_RADIUS_KM * c


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Azimut initial (degrés, 0-360, 0=Nord/sens horaire) du point 1 vers
    le point 2 -- le cap à suivre en quittant le point 1, jamais
    constant le long du grand cercle sauf cas particuliers (mêmes
    formules que pour la distance).
    """

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    x = math.sin(delta_lambda) * math.cos(phi2)
    y = (
        math.cos(phi1) * math.sin(phi2)
        - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    )

    theta = math.atan2(x, y)

    return (math.degrees(theta) + 360.0) % 360.0
