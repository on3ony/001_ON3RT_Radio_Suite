"""
Tests de libraries/geo/projection.py (AzimuthalEquidistantProjection).

Vérifie des cas exactement calculables à la main (voir docstring du
module pour la formule de Snyder) : le centre se projette toujours sur
(0,0), un point antipodal tombe exactement sur le bord du disque unité,
un quart de tour donne une magnitude de 0.5, et deux points simples
(est/nord purs depuis un centre à l'équateur) donnent des coordonnées
exactes vérifiables par le calcul.
"""

import math

import pytest

from libraries.geo.projection import AzimuthalEquidistantProjection


def test_center_projects_to_origin_regardless_of_where_it_is():
    projection = AzimuthalEquidistantProjection(50.85, 4.35)

    x, y = projection.project(50.85, 4.35)

    assert x == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(0.0, abs=1e-9)


def test_antipodal_point_lands_exactly_on_the_unit_circle_edge():
    projection = AzimuthalEquidistantProjection(0.0, 0.0)

    x, y = projection.project(0.0, 180.0)

    magnitude = math.hypot(x, y)
    assert magnitude == pytest.approx(1.0, rel=1e-6)


def test_quarter_way_around_gives_half_magnitude():
    """Un point à un quart de la circonférence (90° d'angle) doit tomber à mi-chemin du bord (magnitude 0.5)."""

    projection = AzimuthalEquidistantProjection(0.0, 0.0)

    x, y = projection.project(0.0, 90.0)

    assert math.hypot(x, y) == pytest.approx(0.5, rel=1e-6)


def test_due_east_point_from_equator_center_projects_along_positive_x():
    """Centre à (0,0), point à (0,90) (est pur) -- calcul à la main : (x,y) = (0.5, 0.0)."""

    projection = AzimuthalEquidistantProjection(0.0, 0.0)

    x, y = projection.project(0.0, 90.0)

    assert x == pytest.approx(0.5, abs=1e-6)
    assert y == pytest.approx(0.0, abs=1e-6)


def test_due_north_point_from_equator_center_projects_along_positive_y():
    """Centre à (0,0), point à (90,0) (nord pur, pôle) -- calcul à la main : (x,y) = (0.0, 0.5)."""

    projection = AzimuthalEquidistantProjection(0.0, 0.0)

    x, y = projection.project(90.0, 0.0)

    assert x == pytest.approx(0.0, abs=1e-6)
    assert y == pytest.approx(0.5, abs=1e-6)


def test_projection_never_exceeds_the_unit_disk():
    """Aucun point réel ne peut dépasser le point antipodal -- magnitude toujours <= 1.0."""

    projection = AzimuthalEquidistantProjection(50.85, 4.35)

    for lat in range(-90, 91, 15):
        for lon in range(-180, 181, 30):
            x, y = projection.project(float(lat), float(lon))
            assert math.hypot(x, y) <= 1.0 + 1e-9


def test_opposite_points_around_the_center_are_symmetric():
    """Deux points à la même distance angulaire du centre, dans des directions opposées, doivent être symétriques."""

    projection = AzimuthalEquidistantProjection(0.0, 0.0)

    x1, y1 = projection.project(0.0, 30.0)
    x2, y2 = projection.project(0.0, -30.0)

    assert x1 == pytest.approx(-x2, rel=1e-9)
    assert y1 == pytest.approx(y2, rel=1e-9)
