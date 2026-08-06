"""
ON3RT Radio Suite
libraries/geo/maidenhead.py

Conversion entre coordonnées géographiques (latitude/longitude) et
locator Maidenhead ("JO20EU") -- première brique de libraries/geo/,
indépendante de tout autre module de la Suite (aucune connaissance de
StationService, du panneau Carte, ni d'aucun autre composant).

Précision standard (3 paires de caractères, 6 caractères, ex. "JO20EU") :
    - Champ (2 lettres, A-R) : cellules de 20° de longitude x 10° de
      latitude.
    - Carré (2 chiffres, 0-9) : cellules de 2° de longitude x 1° de
      latitude à l'intérieur du champ.
    - Sous-carré (2 lettres, A-X) : cellules de 5' de longitude x 2.5'
      de latitude à l'intérieur du carré (2°/24 = 5', 1°/24 = 2.5').

to_locator() encode le point vers la cellule qui le contient (troncature,
comme n'importe quel repère de grille). from_locator() fait l'inverse
et retourne le CENTRE de la cellule désignée (jamais son coin), car un
locator ne désigne qu'une zone, jamais un point exact -- c'est la
convention universellement utilisée par les convertisseurs Maidenhead.
Un aller-retour to_locator()->from_locator() ne retombe donc PAS
exactement sur les coordonnées d'origine : l'écart maximal possible est
la moitié d'un sous-carré (~2.5' de longitude, ~1.25' de latitude),
c'est un comportement attendu, pas une imprécision du calcul.
"""

from __future__ import annotations

_FIELD_LETTERS = "ABCDEFGHIJKLMNOPQR"
_SUBSQUARE_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWX"

_FIELD_SPAN_LON = 20.0
_FIELD_SPAN_LAT = 10.0
_SQUARE_SPAN_LON = 2.0
_SQUARE_SPAN_LAT = 1.0
_SUBSQUARE_SPAN_LON = _SQUARE_SPAN_LON / 24.0
_SUBSQUARE_SPAN_LAT = _SQUARE_SPAN_LAT / 24.0


def to_locator(latitude: float, longitude: float) -> str:
    """
    Encode (latitude, longitude) vers un locator Maidenhead à 6
    caractères (précision standard, ex. "JO20EU"). Lève ValueError si
    les coordonnées sont hors plage (latitude hors [-90, 90], longitude
    hors [-180, 180]).
    """

    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"latitude hors plage ({latitude}, plage valide -90..90)")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"longitude hors plage ({longitude}, plage valide -180..180)")

    lon_adjusted = longitude + 180.0
    lat_adjusted = latitude + 90.0

    field_lon = min(17, int(lon_adjusted // _FIELD_SPAN_LON))
    field_lat = min(17, int(lat_adjusted // _FIELD_SPAN_LAT))

    remainder_lon = lon_adjusted - field_lon * _FIELD_SPAN_LON
    remainder_lat = lat_adjusted - field_lat * _FIELD_SPAN_LAT

    square_lon = min(9, int(remainder_lon // _SQUARE_SPAN_LON))
    square_lat = min(9, int(remainder_lat // _SQUARE_SPAN_LAT))

    remainder_lon -= square_lon * _SQUARE_SPAN_LON
    remainder_lat -= square_lat * _SQUARE_SPAN_LAT

    subsquare_lon = min(23, int(remainder_lon // _SUBSQUARE_SPAN_LON))
    subsquare_lat = min(23, int(remainder_lat // _SUBSQUARE_SPAN_LAT))

    return (
        _FIELD_LETTERS[field_lon] + _FIELD_LETTERS[field_lat]
        + str(square_lon) + str(square_lat)
        + _SUBSQUARE_LETTERS[subsquare_lon] + _SUBSQUARE_LETTERS[subsquare_lat]
    )


def from_locator(locator: str) -> tuple[float, float]:
    """
    Décode un locator Maidenhead à 6 caractères vers (latitude,
    longitude) -- le CENTRE du sous-carré désigné, voir docstring du
    module. Insensible à la casse. Lève ValueError si le format est
    invalide (longueur, caractères hors plage documentée pour leur
    position).
    """

    if len(locator) != 6:
        raise ValueError(f"locator invalide ({locator!r}, 6 caractères attendus)")

    locator = locator.upper()
    field_lon_c, field_lat_c, square_lon_c, square_lat_c, subsquare_lon_c, subsquare_lat_c = locator

    if field_lon_c not in _FIELD_LETTERS or field_lat_c not in _FIELD_LETTERS:
        raise ValueError(f"locator invalide ({locator!r}) : champ hors plage A-R")
    if not square_lon_c.isdigit() or not square_lat_c.isdigit():
        raise ValueError(f"locator invalide ({locator!r}) : carré hors plage 0-9")
    if subsquare_lon_c not in _SUBSQUARE_LETTERS or subsquare_lat_c not in _SUBSQUARE_LETTERS:
        raise ValueError(f"locator invalide ({locator!r}) : sous-carré hors plage A-X")

    field_lon = _FIELD_LETTERS.index(field_lon_c)
    field_lat = _FIELD_LETTERS.index(field_lat_c)
    square_lon = int(square_lon_c)
    square_lat = int(square_lat_c)
    subsquare_lon = _SUBSQUARE_LETTERS.index(subsquare_lon_c)
    subsquare_lat = _SUBSQUARE_LETTERS.index(subsquare_lat_c)

    longitude = (
        field_lon * _FIELD_SPAN_LON
        + square_lon * _SQUARE_SPAN_LON
        + (subsquare_lon + 0.5) * _SUBSQUARE_SPAN_LON
        - 180.0
    )
    latitude = (
        field_lat * _FIELD_SPAN_LAT
        + square_lat * _SQUARE_SPAN_LAT
        + (subsquare_lat + 0.5) * _SUBSQUARE_SPAN_LAT
        - 90.0
    )

    return latitude, longitude
