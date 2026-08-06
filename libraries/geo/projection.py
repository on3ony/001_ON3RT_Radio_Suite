"""
ON3RT Radio Suite
libraries/geo/projection.py

Projection azimutale équidistante oblique (centrée sur un point
arbitraire, ici la station), sur une Terre sphérique -- formule
standard de John P. Snyder, "Map Projections: A Working Manual", USGS
Professional Paper 1395 (chapitre 25, cas sphérique oblique) :

    cos(c)  = sin(phi1)*sin(phi) + cos(phi1)*cos(phi)*cos(lambda-lambda0)
    k'      = c / sin(c)
    x       = k' * cos(phi) * sin(lambda - lambda0)
    y       = k' * (cos(phi1)*sin(phi) - sin(phi1)*cos(phi)*cos(lambda-lambda0))

où (phi1, lambda0) est le centre de la projection (la station) et
(phi, lambda) le point à projeter. c est la distance angulaire (en
radians) entre les deux points -- la même valeur que celle utilisée par
great_circle.distance_km() (à la conversion en km près).

Sortie normalisée : project() retourne (x, y) dans le disque unité
(distance <= 1.0 signifie distance <= la demi-circonférence terrestre,
soit le point antipodal exact) -- jamais des pixels. C'est au
consommateur (le futur moteur de rendu de la Carte) d'appliquer sa
propre mise à l'échelle vers la taille réelle du widget, et
d'inverser l'axe y si nécessaire pour la convention écran (y croissant
vers le bas) -- cette classe reste purement cartographique/mathématique,
aucune connaissance de Qt ni d'un quelconque système de coordonnées
écran.

Deux cas dégénérés, gérés explicitement (la formule seule produit une
division par zéro ou un résultat indéfini) :
    - c == 0 (le point EST le centre, ex. la station se projetant sur
      elle-même) : retourne (0.0, 0.0) directement.
    - c == pi (point antipodal exact) : la projection azimutale
      équidistante n'a mathématiquement PAS un azimut défini pour ce
      point précis (tout azimut mène également à l'antipode) -- retourne
      un point à distance 1.0 (bord du disque) selon une direction
      arbitraire mais déterministe (0°), documenté comme tel plutôt que
      de lever une exception pour un cas géographiquement réel bien que
      rarissime en pratique.
"""

from __future__ import annotations

import math

_ANTIPODAL_EPSILON = 1e-9


class AzimuthalEquidistantProjection:
    """Voir docstring du module pour la formule et les cas dégénérés."""

    def __init__(self, center_latitude: float, center_longitude: float):
        self.center_latitude = center_latitude
        self.center_longitude = center_longitude

    def project(self, latitude: float, longitude: float) -> tuple[float, float]:
        """Voir docstring du module -- retourne (x, y) dans le disque unité, jamais des pixels."""

        phi1 = math.radians(self.center_latitude)
        lambda0 = math.radians(self.center_longitude)
        phi = math.radians(latitude)
        lam = math.radians(longitude)

        delta_lambda = lam - lambda0

        cos_c = math.sin(phi1) * math.sin(phi) + math.cos(phi1) * math.cos(phi) * math.cos(delta_lambda)
        cos_c = max(-1.0, min(1.0, cos_c))  # protège des dépassements d'arrondi flottant
        c = math.acos(cos_c)

        if c < _ANTIPODAL_EPSILON:
            return 0.0, 0.0

        if math.pi - c < _ANTIPODAL_EPSILON:
            # Point antipodal exact -- azimut indéfini, voir docstring du module.
            return 1.0, 0.0

        k_prime = c / math.sin(c)

        x = k_prime * math.cos(phi) * math.sin(delta_lambda)
        y = k_prime * (math.cos(phi1) * math.sin(phi) - math.sin(phi1) * math.cos(phi) * math.cos(delta_lambda))

        return x / math.pi, y / math.pi
