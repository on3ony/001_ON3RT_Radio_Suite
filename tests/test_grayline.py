"""
Tests de libraries/geo/grayline.py.

Vérifie solar_elevation_deg()/daylight_zone() par des invariants
géométriques indépendamment vérifiables : élévation exacte aux points
remarquables (subsolaire = +90°, antipodal = -90°), cohérence croisée
avec great_circle.distance_km() (élévation = 90° - distance angulaire
au point subsolaire, une identité mathématique, pas une coïncidence),
cohérence avec solar.terminator_points() (élévation ~0 sur la ligne du
terminateur déjà testée dans test_solar.py), et rejet des entrées
invalides -- y compris la délégation de validation vers solar.py
(longitude, datetime naïf), pour s'assurer qu'elle fonctionne bien de
bout en bout et pas seulement en isolation.
"""

import math
from datetime import datetime, timezone

import pytest

from libraries.geo import grayline, solar
from libraries.geo.grayline import DaylightZone
from libraries.geo.great_circle import distance_km

_EARTH_RADIUS_KM = 6371.0

_MARCH_EQUINOX = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)

_NAIVE_MOMENT = datetime(2026, 1, 1, 12, 0, 0)


def _angular_distance_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance angulaire (degrés) entre deux points, dérivée de great_circle.distance_km()."""

    return distance_km(lat1, lon1, lat2, lon2) / _EARTH_RADIUS_KM * 180.0 / math.pi


# ------------------------------------------------------------------
# solar_elevation_deg() -- points remarquables et cohérence croisée
# ------------------------------------------------------------------

def test_elevation_at_the_subsolar_point_is_ninety_degrees():
    subsolar_lat, subsolar_lon = solar.subsolar_point(_MARCH_EQUINOX)

    elevation = grayline.solar_elevation_deg(_MARCH_EQUINOX, subsolar_lat, subsolar_lon)

    assert elevation == pytest.approx(90.0, abs=1e-9)


def test_elevation_at_the_antipodal_point_is_minus_ninety_degrees():
    subsolar_lat, subsolar_lon = solar.subsolar_point(_MARCH_EQUINOX)
    antipode_lat = -subsolar_lat
    antipode_lon = ((subsolar_lon + 360.0) % 360.0) - 180.0

    elevation = grayline.solar_elevation_deg(_MARCH_EQUINOX, antipode_lat, antipode_lon)

    assert elevation == pytest.approx(-90.0, abs=1e-9)


@pytest.mark.parametrize(("latitude", "longitude"), [
    (0.0, 0.0),
    (45.0, 10.0),
    (-30.0, -60.0),
    (60.0, 120.0),
])
def test_elevation_equals_ninety_degrees_minus_angular_distance_from_subsolar_point(latitude, longitude):
    """Identité mathématique (pas une coïncidence) : sin(élévation) == cos(distance angulaire au point subsolaire)."""

    subsolar_lat, subsolar_lon = solar.subsolar_point(_MARCH_EQUINOX)
    expected = 90.0 - _angular_distance_deg(subsolar_lat, subsolar_lon, latitude, longitude)

    actual = grayline.solar_elevation_deg(_MARCH_EQUINOX, latitude, longitude)

    assert actual == pytest.approx(expected, abs=1e-6)


def test_elevation_on_terminator_points_is_close_to_zero():
    for latitude, longitude in solar.terminator_points(_MARCH_EQUINOX, num_points=36):
        assert grayline.solar_elevation_deg(_MARCH_EQUINOX, latitude, longitude) == pytest.approx(0.0, abs=1e-6)


def test_elevation_never_exceeds_physical_bounds():
    for lat in range(-90, 91, 30):
        for lon in range(-180, 181, 45):
            elevation = grayline.solar_elevation_deg(_MARCH_EQUINOX, float(lat), float(lon))
            assert -90.0 <= elevation <= 90.0


@pytest.mark.parametrize("latitude", [90.0, -90.0])
def test_elevation_accepts_boundary_latitudes(latitude):
    elevation = grayline.solar_elevation_deg(_MARCH_EQUINOX, latitude, 0.0)

    assert -90.0 <= elevation <= 90.0


@pytest.mark.parametrize("latitude", [90.1, -90.1])
def test_elevation_rejects_latitude_out_of_range(latitude):
    with pytest.raises(ValueError):
        grayline.solar_elevation_deg(_MARCH_EQUINOX, latitude, 0.0)


@pytest.mark.parametrize("longitude", [180.1, -180.1, 200.0])
def test_elevation_rejects_longitude_out_of_range_via_delegation_to_solar(longitude):
    """longitude n'est jamais revalidée dans grayline.py -- déléguée à solar.hour_angle_deg()."""

    with pytest.raises(ValueError):
        grayline.solar_elevation_deg(_MARCH_EQUINOX, 0.0, longitude)


# ------------------------------------------------------------------
# DaylightZone -- valeurs documentées et export public
# ------------------------------------------------------------------

def test_daylight_zone_values_are_the_documented_strings():
    assert DaylightZone.DAY.value == "day"
    assert DaylightZone.NIGHT.value == "night"
    assert DaylightZone.TERMINATOR.value == "terminator"


def test_all_exports_exactly_the_three_public_names():
    assert grayline.__all__ == ["DaylightZone", "solar_elevation_deg", "daylight_zone"]


# ------------------------------------------------------------------
# daylight_zone() -- classification et bande TERMINATOR
# ------------------------------------------------------------------

def test_daylight_zone_is_day_at_the_subsolar_point():
    subsolar_lat, subsolar_lon = solar.subsolar_point(_MARCH_EQUINOX)

    assert grayline.daylight_zone(_MARCH_EQUINOX, subsolar_lat, subsolar_lon) == DaylightZone.DAY


def test_daylight_zone_is_night_at_the_antipodal_point():
    subsolar_lat, subsolar_lon = solar.subsolar_point(_MARCH_EQUINOX)
    antipode_lat = -subsolar_lat
    antipode_lon = ((subsolar_lon + 360.0) % 360.0) - 180.0

    assert grayline.daylight_zone(_MARCH_EQUINOX, antipode_lat, antipode_lon) == DaylightZone.NIGHT


def test_daylight_zone_is_terminator_on_a_terminator_point_with_the_default_band():
    latitude, longitude = solar.terminator_points(_MARCH_EQUINOX, num_points=4)[0]

    assert grayline.daylight_zone(_MARCH_EQUINOX, latitude, longitude) == DaylightZone.TERMINATOR


def test_daylight_zone_with_zero_half_width_practically_never_returns_terminator():
    """Une bande de largeur nulle ne peut matcher que l'égalité flottante exacte à zéro, jamais atteinte en pratique."""

    latitude, longitude = solar.terminator_points(_MARCH_EQUINOX, num_points=4)[0]

    zone = grayline.daylight_zone(_MARCH_EQUINOX, latitude, longitude, terminator_half_width_deg=0.0)

    assert zone != DaylightZone.TERMINATOR


def test_daylight_zone_default_half_width_matches_explicit_zero_point_five():
    subsolar_lat, subsolar_lon = solar.subsolar_point(_MARCH_EQUINOX)

    with_default = grayline.daylight_zone(_MARCH_EQUINOX, subsolar_lat, subsolar_lon)
    with_explicit = grayline.daylight_zone(
        _MARCH_EQUINOX, subsolar_lat, subsolar_lon, terminator_half_width_deg=0.5
    )

    assert with_default == with_explicit


@pytest.mark.parametrize("half_width", [-0.1, -10.0])
def test_daylight_zone_rejects_negative_half_width(half_width):
    with pytest.raises(ValueError):
        grayline.daylight_zone(_MARCH_EQUINOX, 0.0, 0.0, terminator_half_width_deg=half_width)


@pytest.mark.parametrize("latitude", [90.1, -90.1])
def test_daylight_zone_rejects_latitude_out_of_range_via_delegation_to_solar_elevation_deg(latitude):
    with pytest.raises(ValueError):
        grayline.daylight_zone(_MARCH_EQUINOX, latitude, 0.0)


# ------------------------------------------------------------------
# Validations communes aux deux fonctions publiques
# ------------------------------------------------------------------

@pytest.mark.parametrize("call", [
    lambda moment: grayline.solar_elevation_deg(moment, 0.0, 0.0),
    lambda moment: grayline.daylight_zone(moment, 0.0, 0.0),
], ids=["solar_elevation_deg", "daylight_zone"])
def test_every_public_function_rejects_a_naive_datetime_via_delegation(call):
    with pytest.raises(ValueError):
        call(_NAIVE_MOMENT)
