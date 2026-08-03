"""
ON3RT Radio Suite
libraries/geo/grayline.py

Classification jour/nuit/terminateur d'un point du globe -- brique de
libraries/geo/, construite exclusivement sur libraries/geo/solar.py
(déclinaison + angle horaire), sans réimplémenter aucun calcul
astronomique. Indépendante de tout le reste de la Suite : aucune
connaissance de Qt, de la Carte, d'une projection, ni d'aucun autre
module (même limite que solar.py/great_circle.py/projection.py).

Formule : transformation de coordonnées horaires -> horizontales (Jean
Meeus, "Astronomical Algorithms", 2e édition, Willmann-Bell, 1998,
chapitre 13, équation 13.6) :

    sin(élévation) = sin(latitude)*sin(déclinaison)
                    + cos(latitude)*cos(déclinaison)*cos(angle horaire)

Convention géométrique (élévation nulle = terminateur), volontairement
la MÊME que celle de solar.terminator_points() -- PAS la convention
corrigée de la réfraction atmosphérique (-0.8333°) utilisée par
solar.sunrise_sunset_utc() pour le lever/coucher visible. Les deux
conventions sont légitimes mais répondent à des besoins différents
(terminateur cartographique théorique ici, horizon visible réel
là-bas) ; ce module reste cohérent avec la ligne déjà tracée par
solar.terminator_points().
"""

from __future__ import annotations

import math
from datetime import datetime
from enum import Enum

from libraries.geo.solar import hour_angle_deg, solar_declination_deg

__all__ = [
    "DaylightZone",
    "solar_elevation_deg",
    "daylight_zone",
]

# Demi-largeur par défaut (degrés d'élévation) de la bande TERMINATOR
# autour de l'élévation nulle -- le terminateur géométrique exact est un
# ensemble de mesure nulle (une ligne), inatteignable en pratique pour
# une latitude/longitude quelconques ; cette bande le rend utilisable
# par un consommateur réel (ex. la future GraylineLayer, qui a besoin
# d'une zone de transition visuelle, pas d'un unique point infiniment
# fin).
_DEFAULT_TERMINATOR_HALF_WIDTH_DEG = 0.5


class DaylightZone(Enum):
    """Classification jour/nuit/terminateur d'un point du globe -- voir daylight_zone()."""

    DAY = "day"
    NIGHT = "night"
    TERMINATOR = "terminator"


def solar_elevation_deg(moment: datetime, latitude: float, longitude: float) -> float:
    """
    Élévation du Soleil (degrés) au-dessus de l'horizon géométrique
    (sans réfraction atmosphérique) au point (latitude, longitude), à
    l'instant moment. Positive de jour, négative de nuit, nulle
    exactement sur le terminateur -- voir docstring du module pour la
    formule et la convention.

    Lève ValueError si latitude est hors plage [-90, 90], ou si moment/
    longitude sont invalides (délégué à solar.solar_declination_deg()/
    solar.hour_angle_deg(), voir libraries/geo/solar.py).
    """

    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"latitude hors plage ({latitude}, plage valide -90..90)")

    declination_deg = solar_declination_deg(moment)
    hour_angle = hour_angle_deg(moment, longitude)

    phi = math.radians(latitude)
    delta = math.radians(declination_deg)
    h = math.radians(hour_angle)

    sin_elevation = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(h)
    sin_elevation = max(-1.0, min(1.0, sin_elevation))  # protège des dépassements d'arrondi flottant

    return math.degrees(math.asin(sin_elevation))


def daylight_zone(
    moment: datetime,
    latitude: float,
    longitude: float,
    terminator_half_width_deg: float = _DEFAULT_TERMINATOR_HALF_WIDTH_DEG,
) -> DaylightZone:
    """
    Classifie le point (latitude, longitude) à l'instant moment :
    DaylightZone.DAY si le Soleil est au-dessus de l'horizon
    géométrique de plus de terminator_half_width_deg, DaylightZone.NIGHT
    s'il est en dessous de plus de terminator_half_width_deg,
    DaylightZone.TERMINATOR entre les deux (voir _DEFAULT_TERMINATOR_
    HALF_WIDTH_DEG pour la justification de cette bande).

    Lève ValueError si terminator_half_width_deg est négatif, ou si
    latitude/longitude/moment sont invalides (voir solar_elevation_deg()).
    """

    if terminator_half_width_deg < 0.0:
        raise ValueError(f"terminator_half_width_deg doit être >= 0 ({terminator_half_width_deg})")

    elevation_deg = solar_elevation_deg(moment, latitude, longitude)

    if elevation_deg > terminator_half_width_deg:
        return DaylightZone.DAY
    if elevation_deg < -terminator_half_width_deg:
        return DaylightZone.NIGHT

    return DaylightZone.TERMINATOR
