"""
Tests de libraries/geo/great_circle.py.

Vérifie distance_km()/initial_bearing_deg() contre des cas
mathématiquement vérifiables par le calcul (quart et demi de la
circonférence terrestre, points cardinaux purs sur l'équateur/un
méridien) -- volontairement PAS des distances de villes "communément
citées" qui ne peuvent pas être vérifiées de façon indépendante ici.
"""

import math

import pytest

from libraries.geo.great_circle import distance_km, initial_bearing_deg

_EARTH_RADIUS_KM = 6371.0
_QUARTER_CIRCUMFERENCE_KM = (2 * math.pi * _EARTH_RADIUS_KM) / 4
_HALF_CIRCUMFERENCE_KM = math.pi * _EARTH_RADIUS_KM


# ------------------------------------------------------------------
# distance_km() -- cas vérifiables par le calcul pur
# ------------------------------------------------------------------

def test_distance_to_self_is_zero():
    assert distance_km(50.85, 4.35, 50.85, 4.35) == pytest.approx(0.0, abs=1e-6)


def test_distance_quarter_way_around_equator_is_a_quarter_circumference():
    """(0,0) -> (0,90) : un quart de tour exact le long de l'équateur."""

    assert distance_km(0.0, 0.0, 0.0, 90.0) == pytest.approx(_QUARTER_CIRCUMFERENCE_KM, rel=1e-6)


def test_distance_to_antipode_is_half_circumference():
    """(0,0) -> (0,180) : point antipodal exact, demi-circonférence."""

    assert distance_km(0.0, 0.0, 0.0, 180.0) == pytest.approx(_HALF_CIRCUMFERENCE_KM, rel=1e-6)


def test_distance_pole_to_pole_is_half_circumference():
    assert distance_km(90.0, 0.0, -90.0, 0.0) == pytest.approx(_HALF_CIRCUMFERENCE_KM, rel=1e-6)


def test_distance_is_symmetric():
    a_to_b = distance_km(50.85, 4.35, 40.71, -74.01)
    b_to_a = distance_km(40.71, -74.01, 50.85, 4.35)

    assert a_to_b == pytest.approx(b_to_a, rel=1e-9)


# ------------------------------------------------------------------
# initial_bearing_deg() -- points cardinaux purs (vérifiables à l'oeil)
# ------------------------------------------------------------------

def test_bearing_due_east_along_equator_is_90_degrees():
    assert initial_bearing_deg(0.0, 0.0, 0.0, 10.0) == pytest.approx(90.0, abs=1e-6)


def test_bearing_due_west_along_equator_is_270_degrees():
    assert initial_bearing_deg(0.0, 0.0, 0.0, -10.0) == pytest.approx(270.0, abs=1e-6)


def test_bearing_due_north_along_meridian_is_0_degrees():
    assert initial_bearing_deg(0.0, 0.0, 10.0, 0.0) == pytest.approx(0.0, abs=1e-6)


def test_bearing_due_south_along_meridian_is_180_degrees():
    assert initial_bearing_deg(0.0, 0.0, -10.0, 0.0) == pytest.approx(180.0, abs=1e-6)


def test_bearing_is_always_in_0_360_range():
    bearing = initial_bearing_deg(50.85, 4.35, 40.71, -74.01)

    assert 0.0 <= bearing < 360.0
