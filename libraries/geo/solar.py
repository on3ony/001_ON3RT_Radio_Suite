"""
ON3RT Radio Suite
libraries/geo/solar.py

Position du Soleil (déclinaison, équation du temps, point subsolaire,
angle horaire, lever/coucher, terminateur jour/nuit) -- brique de
libraries/geo/, indépendante de tout autre module de la Suite (aucune
connaissance de StationService, du panneau Carte, ni d'aucun autre
composant). Destinée à alimenter une future couche Grayline de la Carte
(apps/dashboard/map_layers/), mais ne connaît rien de Qt ni du système
de projection -- terminator_points() retourne des (latitude, longitude),
jamais des coordonnées écran (voir libraries/geo/projection.py pour la
conversion).

Algorithme : formules de basse précision du NOAA Solar Calculator
(gml.noaa.gov/grad/solcalc/solareqns.PDF), elles-mêmes issues de Jean
Meeus, "Astronomical Algorithms" (2e édition, Willmann-Bell, 1998),
chapitres 25 (position du Soleil) et 28 (équation du temps). Précision
annoncée par la NOAA : de l'ordre de ±0.01° sur la déclinaison et
±1 seconde sur l'équation du temps entre 1800 et 2100 -- très largement
suffisant pour une carte de propagation HF (l'incertitude de position
d'une station DX ou la largeur visuelle du terminateur à l'écran
dominent très largement cette erreur résiduelle).

Toutes les fonctions prennent un datetime.datetime "conscient" du fuseau
horaire (tzinfo non None, converti en UTC en interne) -- jamais un
datetime naïf, pour éviter toute ambiguïté de fuseau silencieuse.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

__all__ = [
    "solar_declination_deg",
    "equation_of_time_minutes",
    "subsolar_point",
    "hour_angle_deg",
    "sunrise_sunset_utc",
    "terminator_points",
]

_JULIAN_DAY_AT_UNIX_EPOCH = 2440587.5  # JD du 1970-01-01T00:00:00 UTC
_SECONDS_PER_DAY = 86400.0
_JULIAN_DAY_J2000 = 2451545.0  # JD du 2000-01-01T12:00:00 UTC
_JULIAN_CENTURY_DAYS = 36525.0

# Dépression standard du centre du disque solaire sous l'horizon
# géométrique au lever/coucher (réfraction atmosphérique moyenne 34' +
# rayon apparent du Soleil 16' = 50' = 0.8333°) -- même valeur que celle
# utilisée par le NOAA Solar Calculator et la quasi-totalité des
# éphémérides grand public.
_SUNRISE_SUNSET_ELEVATION_DEG = -0.8333

# En deçà de cette distance au pôle exact, l'angle horaire de lever/
# coucher n'est mathématiquement pas défini (division par cos(latitude)
# qui tend vers zéro) -- cas dégénéré réel (jour/nuit polaire permanent
# à quelques mètres du pôle) mais rarissime en usage radioamateur.
_POLE_EPSILON_DEG = 1e-9


def _require_utc(moment: datetime) -> datetime:
    """Convertit moment en UTC. Lève ValueError si moment est naïf (pas de tzinfo)."""

    if moment.tzinfo is None:
        raise ValueError("moment doit être un datetime conscient du fuseau horaire (tzinfo requis)")

    return moment.astimezone(timezone.utc)


def _julian_day(moment: datetime) -> float:
    """Jour julien (JD) de moment (converti en UTC)."""

    moment = _require_utc(moment)

    return _JULIAN_DAY_AT_UNIX_EPOCH + moment.timestamp() / _SECONDS_PER_DAY


def _sun_position(moment: datetime) -> tuple[float, float]:
    """
    Déclinaison du Soleil (degrés) et équation du temps (minutes) à
    l'instant moment -- calculées ensemble car elles partagent les mêmes
    termes intermédiaires (longitude moyenne, anomalie moyenne,
    excentricité, obliquité corrigée...), voir docstring du module pour
    la référence NOAA/Meeus. Retourne (declination_deg, eot_minutes).
    """

    t = (_julian_day(moment) - _JULIAN_DAY_J2000) / _JULIAN_CENTURY_DAYS

    geom_mean_long = math.radians((280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0)
    geom_mean_anom = math.radians(357.52911 + t * (35999.05029 - 0.0001537 * t))
    eccentricity = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)

    sun_eq_of_center = math.radians(
        math.sin(geom_mean_anom) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + math.sin(2.0 * geom_mean_anom) * (0.019993 - 0.000101 * t)
        + math.sin(3.0 * geom_mean_anom) * 0.000289
    )

    sun_true_long = geom_mean_long + sun_eq_of_center
    sun_app_long = (
        sun_true_long
        - math.radians(0.00569)
        - math.radians(0.00478) * math.sin(math.radians(125.04 - 1934.136 * t))
    )

    mean_obliquity = math.radians(
        23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60.0) / 60.0
    )
    obliquity_correction = mean_obliquity + math.radians(0.00256) * math.cos(math.radians(125.04 - 1934.136 * t))

    declination = math.asin(math.sin(obliquity_correction) * math.sin(sun_app_long))

    y = math.tan(obliquity_correction / 2.0) ** 2
    equation_of_time = 4.0 * math.degrees(
        y * math.sin(2.0 * geom_mean_long)
        - 2.0 * eccentricity * math.sin(geom_mean_anom)
        + 4.0 * eccentricity * y * math.sin(geom_mean_anom) * math.cos(2.0 * geom_mean_long)
        - 0.5 * y * y * math.sin(4.0 * geom_mean_long)
        - 1.25 * eccentricity * eccentricity * math.sin(2.0 * geom_mean_anom)
    )

    return math.degrees(declination), equation_of_time


def solar_declination_deg(moment: datetime) -> float:
    """
    Déclinaison du Soleil (degrés) à l'instant moment -- la latitude à
    laquelle le Soleil est au zénith. Varie entre environ -23.44° (solstice
    de décembre) et +23.44° (solstice de juin).
    """

    declination_deg, _ = _sun_position(moment)

    return declination_deg


def equation_of_time_minutes(moment: datetime) -> float:
    """
    Équation du temps (minutes) à l'instant moment : écart entre le
    temps solaire apparent (celui d'un cadran solaire) et le temps
    solaire moyen (celui d'une horloge), dû à l'excentricité de l'orbite
    terrestre et à l'obliquité de l'écliptique. Varie entre environ -14
    et +16 minutes au cours de l'année.
    """

    _, eot_minutes = _sun_position(moment)

    return eot_minutes


def subsolar_point(moment: datetime) -> tuple[float, float]:
    """
    Point subsolaire (latitude, longitude en degrés) à l'instant moment :
    le point du globe où le Soleil est exactement au zénith. La latitude
    vaut la déclinaison du Soleil ; la longitude se déduit de l'heure UTC
    et de l'équation du temps (l'endroit où il est actuellement midi
    solaire vrai).
    """

    moment = _require_utc(moment)
    declination_deg, eot_minutes = _sun_position(moment)

    utc_hours = (
        moment.hour
        + moment.minute / 60.0
        + moment.second / 3600.0
        + moment.microsecond / 3_600_000_000.0
    )
    longitude = -15.0 * (utc_hours - 12.0 + eot_minutes / 60.0)
    longitude = ((longitude + 180.0) % 360.0) - 180.0

    return declination_deg, longitude


def hour_angle_deg(moment: datetime, longitude: float) -> float:
    """
    Angle horaire du Soleil (degrés) à la longitude donnée, à l'instant
    moment : 0° à midi solaire vrai en ce lieu, négatif le matin, positif
    l'après-midi, croît de 15°/heure. Vaut simplement l'écart de
    longitude au point subsolaire courant (voir subsolar_point()) --
    normalisé dans [-180, 180]. Lève ValueError si longitude est hors
    plage [-180, 180].
    """

    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"longitude hors plage ({longitude}, plage valide -180..180)")

    _, subsolar_longitude = subsolar_point(moment)
    hour_angle = longitude - subsolar_longitude

    return ((hour_angle + 180.0) % 360.0) - 180.0


def sunrise_sunset_utc(
    moment: datetime, latitude: float, longitude: float
) -> tuple[datetime | None, datetime | None]:
    """
    Heures de lever et de coucher du Soleil (datetime conscients du
    fuseau, en UTC) pour la date calendaire de moment (UTC), au point
    (latitude, longitude). La déclinaison et l'équation du temps sont
    évaluées à midi UTC de cette même date -- ces deux grandeurs varient
    trop lentement sur 24h pour justifier un calcul itératif (même
    approximation que le NOAA Solar Calculator).

    Retourne (None, None) si le Soleil ne se lève pas ou ne se couche
    pas ce jour-là à cette latitude (nuit polaire, soleil de minuit, ou
    latitude à ±90° exact où l'angle horaire n'est pas défini) -- aucune
    heure n'est inventée dans ces cas.

    Lève ValueError si latitude est hors plage [-90, 90] ou longitude
    hors plage [-180, 180].
    """

    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"latitude hors plage ({latitude}, plage valide -90..90)")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"longitude hors plage ({longitude}, plage valide -180..180)")

    if abs(latitude) >= 90.0 - _POLE_EPSILON_DEG:
        return None, None

    moment = _require_utc(moment)
    reference_noon = moment.replace(hour=12, minute=0, second=0, microsecond=0)
    declination_deg, eot_minutes = _sun_position(reference_noon)

    phi = math.radians(latitude)
    delta = math.radians(declination_deg)

    cos_hour_angle = (
        math.sin(math.radians(_SUNRISE_SUNSET_ELEVATION_DEG)) - math.sin(phi) * math.sin(delta)
    ) / (math.cos(phi) * math.cos(delta))

    if cos_hour_angle > 1.0 or cos_hour_angle < -1.0:
        # Nuit polaire (jamais de lever) ou soleil de minuit (jamais de
        # coucher) -- indiscernables l'un de l'autre par cette seule
        # valeur, d'où (None, None) dans les deux cas.
        return None, None

    cos_hour_angle = max(-1.0, min(1.0, cos_hour_angle))  # protège des dépassements d'arrondi flottant
    sunrise_hour_angle_deg = math.degrees(math.acos(cos_hour_angle))

    solar_noon_utc_hours = 12.0 - longitude / 15.0 - eot_minutes / 60.0
    midnight = reference_noon.replace(hour=0, minute=0, second=0, microsecond=0)

    sunrise = midnight + timedelta(hours=solar_noon_utc_hours - sunrise_hour_angle_deg / 15.0)
    sunset = midnight + timedelta(hours=solar_noon_utc_hours + sunrise_hour_angle_deg / 15.0)

    return sunrise, sunset


def terminator_points(moment: datetime, num_points: int = 180) -> list[tuple[float, float]]:
    """
    Terminateur jour/nuit à l'instant moment : num_points points
    (latitude, longitude en degrés) échantillonnant le grand cercle situé
    à exactement 90° du point subsolaire -- la frontière géométrique
    entre l'hémisphère éclairé et l'hémisphère nocturne (réfraction
    atmosphérique ignorée, comme pour toute carte grayline usuelle --
    WSJT-X, DX Atlas...). Formule du point de destination à distance et
    relèvement donnés, même famille que libraries/geo/great_circle.py
    (Aviation Formulary / www.movable-type.co.uk/scripts/latlong.html),
    avec une distance angulaire fixe de 90°.

    Les points sont ordonnés par relèvement croissant (0° à 360°) depuis
    le point subsolaire : un consommateur (future GraylineLayer) les
    relie dans cet ordre pour tracer une ligne continue.
    """

    if num_points < 3:
        raise ValueError(f"num_points doit être >= 3 pour former un tracé fermé ({num_points})")

    subsolar_lat, subsolar_lon = subsolar_point(moment)

    phi1 = math.radians(subsolar_lat)
    lambda0 = math.radians(subsolar_lon)

    points: list[tuple[float, float]] = []
    for i in range(num_points):
        bearing = math.radians(360.0 * i / num_points)

        phi2 = math.asin(max(-1.0, min(1.0, math.cos(phi1) * math.cos(bearing))))
        lambda2 = lambda0 + math.atan2(
            math.sin(bearing) * math.cos(phi1),
            -math.sin(phi1) * math.sin(phi2),
        )

        latitude = math.degrees(phi2)
        longitude = ((math.degrees(lambda2) + 180.0) % 360.0) - 180.0

        points.append((latitude, longitude))

    return points
