"""
Tests de libraries/geo/maidenhead.py.

Vérifie to_locator()/from_locator() : formats connus, cohérence
géographique (JO20 doit retomber en Belgique -- fait géographique
public, pas une supposition), aller-retour encodage/décodage avec la
tolérance attendue (la moitié d'un sous-carré, voir docstring du
module -- from_locator() retourne un CENTRE, jamais le point d'origine
exact), et rejet des entrées invalides.
"""

import pytest

from libraries.geo.maidenhead import from_locator, to_locator

_SUBSQUARE_LON_TOLERANCE = (2.0 / 24.0) / 2.0  # moitié d'un sous-carré, voir docstring du module
_SUBSQUARE_LAT_TOLERANCE = (1.0 / 24.0) / 2.0


# ------------------------------------------------------------------
# to_locator() -- cohérence géographique connue
# ------------------------------------------------------------------

def test_belgium_coordinates_encode_to_jo_field():
    """Bruxelles (~50.85N, ~4.35E) doit retomber dans le champ JO (Belgique/Pays-Bas), fait géographique public."""

    locator = to_locator(50.85, 4.35)

    assert locator.startswith("JO")


def test_to_locator_produces_six_uppercase_characters():
    locator = to_locator(50.85, 4.35)

    assert len(locator) == 6
    assert locator == locator.upper()


def test_to_locator_rejects_latitude_out_of_range():
    with pytest.raises(ValueError):
        to_locator(91.0, 0.0)

    with pytest.raises(ValueError):
        to_locator(-91.0, 0.0)


def test_to_locator_rejects_longitude_out_of_range():
    with pytest.raises(ValueError):
        to_locator(0.0, 181.0)

    with pytest.raises(ValueError):
        to_locator(0.0, -181.0)


def test_to_locator_handles_extreme_north_pole_without_raising():
    locator = to_locator(90.0, 0.0)

    assert len(locator) == 6


def test_to_locator_handles_extreme_date_line_without_raising():
    locator = to_locator(0.0, 180.0)

    assert len(locator) == 6


# ------------------------------------------------------------------
# from_locator() -- décodage, format, erreurs
# ------------------------------------------------------------------

def test_from_locator_is_case_insensitive():
    upper = from_locator("JO20EU")
    lower = from_locator("jo20eu")

    assert upper == lower


def test_from_locator_rejects_wrong_length():
    with pytest.raises(ValueError):
        from_locator("JO20E")

    with pytest.raises(ValueError):
        from_locator("JO20EUX")


def test_from_locator_rejects_invalid_field_letter():
    with pytest.raises(ValueError):
        from_locator("ZZ20EU")  # Z hors plage A-R pour le champ


def test_from_locator_rejects_invalid_square_digit():
    with pytest.raises(ValueError):
        from_locator("JOXXEU")


def test_from_locator_rejects_invalid_subsquare_letter():
    with pytest.raises(ValueError):
        from_locator("JO20ZZ")  # Z hors plage A-X pour le sous-carré


def test_from_locator_returns_latitude_longitude_tuple_within_documented_ranges():
    lat, lon = from_locator("JO20EU")

    assert -90.0 <= lat <= 90.0
    assert -180.0 <= lon <= 180.0


# ------------------------------------------------------------------
# Aller-retour : encode -> decode retombe dans la tolérance documentée
# (la moitié d'un sous-carré, jamais un point exact -- voir docstring)
# ------------------------------------------------------------------

@pytest.mark.parametrize("lat, lon", [
    (50.8503, 4.3517),      # Bruxelles
    (0.0, 0.0),             # origine
    (-33.8688, 151.2093),   # Sydney (hémisphère sud, longitude positive élevée)
    (40.7128, -74.0060),    # New York (longitude négative)
    (89.9, 179.9),          # proche pôle nord / ligne de changement de date
    (-89.9, -179.9),        # proche pôle sud / ligne de changement de date (côté opposé)
])
def test_round_trip_stays_within_half_a_subsquare(lat, lon):
    locator = to_locator(lat, lon)
    decoded_lat, decoded_lon = from_locator(locator)

    assert abs(decoded_lat - lat) <= _SUBSQUARE_LAT_TOLERANCE + 1e-9
    assert abs(decoded_lon - lon) <= _SUBSQUARE_LON_TOLERANCE + 1e-9
