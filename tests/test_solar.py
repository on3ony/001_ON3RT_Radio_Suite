"""
Tests de libraries/geo/solar.py.

Vérifie les six fonctions publiques par des faits astronomiques
indépendamment vérifiables (obliquité de l'écliptique ~23.44° aux
solstices, déclinaison ~0° aux équinoxes, extrema connus de l'équation
du temps ~+16.4/-14.2 min), par des invariants géométriques
(cohérence croisée entre subsolar_point()/hour_angle_deg()/
sunrise_sunset_utc(), terminateur toujours à exactement 90° du point
subsolaire via great_circle.distance_km()), et par le rejet des entrées
invalides (datetime naïf, coordonnées hors plage) -- volontairement PAS
d'heures de lever/coucher "communément citées" pour une ville, qui ne
peuvent pas être vérifiées de façon indépendante ici (voir
test_great_circle.py pour la même politique).
"""

from datetime import datetime, timezone

import pytest

from libraries.geo import solar
from libraries.geo.great_circle import distance_km

_EARTH_RADIUS_KM = 6371.0
_QUARTER_CIRCUMFERENCE_KM = (2 * 3.141592653589793 * _EARTH_RADIUS_KM) / 4

_EARTH_AXIAL_TILT_DEG = 23.44

# Bruxelles -- même coordonnées que test_great_circle.py/test_maidenhead.py.
_BRUSSELS_LAT = 50.85
_BRUSSELS_LON = 4.35

# Tromsø (69.6N) -- bien au-delà du cercle polaire arctique (66.56N),
# nuit polaire garantie en décembre et soleil de minuit garanti en juin.
_TROMSO_LAT = 69.6
_TROMSO_LON = 18.9

_JUNE_SOLSTICE = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
_DEC_SOLSTICE = datetime(2026, 12, 21, 12, 0, 0, tzinfo=timezone.utc)
_MARCH_EQUINOX = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
_SEPT_EQUINOX = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
_EOT_MAX_AROUND_NOV_3 = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
_EOT_MIN_AROUND_FEB_11 = datetime(2026, 2, 11, 12, 0, 0, tzinfo=timezone.utc)

_NAIVE_MOMENT = datetime(2026, 1, 1, 12, 0, 0)


# ------------------------------------------------------------------
# solar_declination_deg() -- faits astronomiques connus
# ------------------------------------------------------------------

def test_declination_near_june_solstice_is_close_to_the_axial_tilt():
    assert solar.solar_declination_deg(_JUNE_SOLSTICE) == pytest.approx(_EARTH_AXIAL_TILT_DEG, abs=0.05)


def test_declination_near_december_solstice_is_close_to_minus_the_axial_tilt():
    assert solar.solar_declination_deg(_DEC_SOLSTICE) == pytest.approx(-_EARTH_AXIAL_TILT_DEG, abs=0.05)


def test_declination_near_march_equinox_is_close_to_zero():
    assert solar.solar_declination_deg(_MARCH_EQUINOX) == pytest.approx(0.0, abs=0.5)


def test_declination_near_september_equinox_is_close_to_zero():
    assert solar.solar_declination_deg(_SEPT_EQUINOX) == pytest.approx(0.0, abs=0.5)


def test_declination_never_exceeds_earths_axial_tilt():
    """Invariant sur une année entière -- la déclinaison ne peut physiquement pas dépasser l'obliquité."""

    for month in range(1, 13):
        moment = datetime(2026, month, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert abs(solar.solar_declination_deg(moment)) <= _EARTH_AXIAL_TILT_DEG + 0.1


# ------------------------------------------------------------------
# equation_of_time_minutes() -- extrema connus
# ------------------------------------------------------------------

def test_equation_of_time_reaches_its_known_maximum_near_early_november():
    assert solar.equation_of_time_minutes(_EOT_MAX_AROUND_NOV_3) == pytest.approx(16.4, abs=0.3)


def test_equation_of_time_reaches_its_known_minimum_near_mid_february():
    assert solar.equation_of_time_minutes(_EOT_MIN_AROUND_FEB_11) == pytest.approx(-14.2, abs=0.3)


# ------------------------------------------------------------------
# subsolar_point() -- cohérence avec solar_declination_deg() et bornes
# ------------------------------------------------------------------

def test_subsolar_latitude_matches_solar_declination():
    declination = solar.solar_declination_deg(_MARCH_EQUINOX)
    latitude, _ = solar.subsolar_point(_MARCH_EQUINOX)

    assert latitude == pytest.approx(declination, abs=1e-9)


def test_subsolar_longitude_at_noon_utc_on_equinox_is_near_greenwich():
    """À midi UTC, le point subsolaire est proche du méridien de Greenwich (écart borné par l'équation du temps, quelques degrés au plus)."""

    _, longitude = solar.subsolar_point(_MARCH_EQUINOX)

    assert longitude == pytest.approx(0.0, abs=3.0)


def test_subsolar_longitude_stays_within_documented_range():
    for hour in range(0, 24, 3):
        moment = datetime(2026, 3, 20, hour, 0, 0, tzinfo=timezone.utc)
        _, longitude = solar.subsolar_point(moment)

        assert -180.0 <= longitude <= 180.0


# ------------------------------------------------------------------
# hour_angle_deg() -- angle nul au point subsolaire, taux de 15°/heure
# ------------------------------------------------------------------

def test_hour_angle_is_zero_at_the_current_subsolar_longitude():
    _, subsolar_longitude = solar.subsolar_point(_MARCH_EQUINOX)

    assert solar.hour_angle_deg(_MARCH_EQUINOX, subsolar_longitude) == pytest.approx(0.0, abs=1e-6)


def test_hour_angle_grows_by_fifteen_degrees_per_hour():
    """L'angle horaire croît de 15°/heure (360°/24h) -- l'équation du temps varie trop lentement pour perturber ce taux sur 1h."""

    earlier = solar.hour_angle_deg(_MARCH_EQUINOX, _BRUSSELS_LON)
    later = solar.hour_angle_deg(_MARCH_EQUINOX.replace(hour=13), _BRUSSELS_LON)

    assert later - earlier == pytest.approx(15.0, abs=0.1)


@pytest.mark.parametrize("longitude", [-180.0, -90.0, 0.0, 90.0, 180.0])
def test_hour_angle_stays_within_documented_range(longitude):
    assert -180.0 <= solar.hour_angle_deg(_MARCH_EQUINOX, longitude) <= 180.0


@pytest.mark.parametrize("longitude", [180.1, -180.1, 200.0, -400.0])
def test_hour_angle_rejects_longitude_out_of_range(longitude):
    with pytest.raises(ValueError):
        solar.hour_angle_deg(_MARCH_EQUINOX, longitude)


# ------------------------------------------------------------------
# sunrise_sunset_utc() -- cas nominal, cohérence croisée, cas polaires
# ------------------------------------------------------------------

def test_sunrise_is_before_sunset_at_brussels_on_equinox():
    sunrise, sunset = solar.sunrise_sunset_utc(_MARCH_EQUINOX, _BRUSSELS_LAT, _BRUSSELS_LON)

    assert sunrise is not None
    assert sunset is not None
    assert sunrise < sunset


def test_day_length_near_the_equator_on_equinox_is_close_to_twelve_hours():
    """Fait astronomique connu : au équateur, la journée dure très légèrement plus de 12h (réfraction), quelle que soit la date."""

    sunrise, sunset = solar.sunrise_sunset_utc(_MARCH_EQUINOX, 0.0, 0.0)
    day_length_hours = (sunset - sunrise).total_seconds() / 3600.0

    assert day_length_hours == pytest.approx(12.0, abs=0.3)


def test_solar_noon_is_the_midpoint_of_sunrise_and_sunset():
    """Vérification croisée avec hour_angle_deg() : le milieu de lever/coucher doit être l'instant où l'angle horaire est nul."""

    sunrise, sunset = solar.sunrise_sunset_utc(_MARCH_EQUINOX, _BRUSSELS_LAT, _BRUSSELS_LON)
    midpoint = sunrise + (sunset - sunrise) / 2

    assert solar.hour_angle_deg(midpoint, _BRUSSELS_LON) == pytest.approx(0.0, abs=0.05)


def test_sunrise_and_sunset_hour_angles_are_symmetric_around_solar_noon():
    """Vérification croisée avec hour_angle_deg() : lever et coucher sont à des angles horaires opposés."""

    sunrise, sunset = solar.sunrise_sunset_utc(_MARCH_EQUINOX, _BRUSSELS_LAT, _BRUSSELS_LON)

    hour_angle_at_sunrise = solar.hour_angle_deg(sunrise, _BRUSSELS_LON)
    hour_angle_at_sunset = solar.hour_angle_deg(sunset, _BRUSSELS_LON)

    assert hour_angle_at_sunrise == pytest.approx(-hour_angle_at_sunset, abs=0.05)


def test_sunrise_sunset_uses_the_calendar_date_of_moment_regardless_of_time_of_day():
    """La date calendaire (UTC) de moment fixe le jour calculé -- l'heure exacte passée dans moment n'a pas d'influence."""

    from_morning = solar.sunrise_sunset_utc(_MARCH_EQUINOX.replace(hour=2), _BRUSSELS_LAT, _BRUSSELS_LON)
    from_evening = solar.sunrise_sunset_utc(_MARCH_EQUINOX.replace(hour=23), _BRUSSELS_LAT, _BRUSSELS_LON)

    assert abs((from_morning[0] - from_evening[0]).total_seconds()) < 1.0
    assert abs((from_morning[1] - from_evening[1]).total_seconds()) < 1.0


def test_polar_night_in_december_at_tromso_has_no_sunrise_or_sunset():
    assert solar.sunrise_sunset_utc(_DEC_SOLSTICE, _TROMSO_LAT, _TROMSO_LON) == (None, None)


def test_midnight_sun_in_june_at_tromso_has_no_sunrise_or_sunset():
    assert solar.sunrise_sunset_utc(_JUNE_SOLSTICE, _TROMSO_LAT, _TROMSO_LON) == (None, None)


def test_sunrise_sunset_at_exact_poles_returns_none_without_raising():
    assert solar.sunrise_sunset_utc(_MARCH_EQUINOX, 90.0, 0.0) == (None, None)
    assert solar.sunrise_sunset_utc(_MARCH_EQUINOX, -90.0, 0.0) == (None, None)


@pytest.mark.parametrize("longitude", [180.0, -180.0])
def test_sunrise_sunset_accepts_boundary_longitudes(longitude):
    sunrise, sunset = solar.sunrise_sunset_utc(_MARCH_EQUINOX, _BRUSSELS_LAT, longitude)

    assert sunrise is not None
    assert sunset is not None


@pytest.mark.parametrize(("latitude", "longitude"), [
    (90.1, 0.0),
    (-90.1, 0.0),
    (0.0, 180.1),
    (0.0, -180.1),
])
def test_sunrise_sunset_rejects_coordinates_out_of_range(latitude, longitude):
    with pytest.raises(ValueError):
        solar.sunrise_sunset_utc(_MARCH_EQUINOX, latitude, longitude)


# ------------------------------------------------------------------
# terminator_points() -- toujours à 90° exact du point subsolaire
# ------------------------------------------------------------------

@pytest.mark.parametrize("moment", [_MARCH_EQUINOX, _JUNE_SOLSTICE, _DEC_SOLSTICE])
def test_every_terminator_point_is_a_quarter_circumference_from_the_subsolar_point(moment):
    subsolar_lat, subsolar_lon = solar.subsolar_point(moment)
    points = solar.terminator_points(moment, num_points=36)

    deviations = [
        abs(distance_km(subsolar_lat, subsolar_lon, lat, lon) - _QUARTER_CIRCUMFERENCE_KM)
        for lat, lon in points
    ]

    assert max(deviations) < 1e-6


def test_terminator_points_default_count_is_one_hundred_eighty():
    assert len(solar.terminator_points(_MARCH_EQUINOX)) == 180


@pytest.mark.parametrize("num_points", [3, 36, 720])
def test_terminator_points_respects_requested_count(num_points):
    assert len(solar.terminator_points(_MARCH_EQUINOX, num_points=num_points)) == num_points


def test_terminator_crosses_both_poles_when_subsolar_point_is_on_the_equator():
    """Fait géométrique connu : un cercle de rayon angulaire 90° autour d'un point équatorial passe par les deux pôles."""

    points = solar.terminator_points(_MARCH_EQUINOX, num_points=36)
    latitudes = [lat for lat, _ in points]

    assert max(latitudes) == pytest.approx(90.0, abs=1.0)
    assert min(latitudes) == pytest.approx(-90.0, abs=1.0)


def test_terminator_longitudes_stay_within_documented_range():
    for _, longitude in solar.terminator_points(_JUNE_SOLSTICE, num_points=36):
        assert -180.0 <= longitude <= 180.0


@pytest.mark.parametrize("num_points", [0, 1, 2, -5])
def test_terminator_points_rejects_too_few_points(num_points):
    with pytest.raises(ValueError):
        solar.terminator_points(_MARCH_EQUINOX, num_points=num_points)


# ------------------------------------------------------------------
# Validations communes à toutes les fonctions publiques
# ------------------------------------------------------------------

@pytest.mark.parametrize("call", [
    lambda moment: solar.solar_declination_deg(moment),
    lambda moment: solar.equation_of_time_minutes(moment),
    lambda moment: solar.subsolar_point(moment),
    lambda moment: solar.hour_angle_deg(moment, 0.0),
    lambda moment: solar.sunrise_sunset_utc(moment, 0.0, 0.0),
    lambda moment: solar.terminator_points(moment),
], ids=[
    "solar_declination_deg",
    "equation_of_time_minutes",
    "subsolar_point",
    "hour_angle_deg",
    "sunrise_sunset_utc",
    "terminator_points",
])
def test_every_public_function_rejects_a_naive_datetime(call):
    with pytest.raises(ValueError):
        call(_NAIVE_MOMENT)


def test_all_exports_exactly_the_six_public_functions():
    assert solar.__all__ == [
        "solar_declination_deg",
        "equation_of_time_minutes",
        "subsolar_point",
        "hour_angle_deg",
        "sunrise_sunset_utc",
        "terminator_points",
    ]
