"""
Tests de libraries/radio/license_privileges.py.

Registre pur (aucun matériel, aucune I/O) des classes de licence et
des bandes autorisées par classe -- premier étage du chantier "Tuile
Activité par bande" : filtre les bandes de BandManager selon la
classe de licence active de l'opérateur, de façon évolutive (ajouter
une classe = ajouter une entrée, jamais toucher un module consommateur).
"""

from libraries.radio.band_manager import BandManager
from libraries.radio.license_privileges import (
    DEFAULT_LICENSE_CLASS,
    LICENSE_CLASSES,
    allowed_bands,
    available_license_classes,
)

_ALL_BAND_NAMES = frozenset(band.name for band in BandManager.BANDS)


# ------------------------------------------------------------------
# Classe ON3 (Belgique, novice) -- valeurs explicitement demandées
# ------------------------------------------------------------------

def test_on3_allows_exactly_the_five_specified_bands():
    assert allowed_bands("ON3") == frozenset({"80m", "40m", "20m", "15m", "10m"})


def test_on3_excludes_the_five_bands_explicitly_named_as_forbidden():
    """160m, 30m, 17m, 12m, 6m -- explicitement exclues par l'utilisateur pour ON3."""

    forbidden = {"160m", "30m", "17m", "12m", "6m"}

    assert forbidden.isdisjoint(allowed_bands("ON3"))


# ------------------------------------------------------------------
# Classe HAREC / sans restriction -- toutes les bandes de BandManager
# ------------------------------------------------------------------

def test_harec_allows_every_band_manager_band():
    assert allowed_bands("HAREC") == _ALL_BAND_NAMES


# ------------------------------------------------------------------
# Discipline "jamais planter, jamais inventer" sur une classe absente
# ------------------------------------------------------------------

def test_unknown_license_class_falls_back_to_default_instead_of_raising():
    assert allowed_bands("CLASSE_INEXISTANTE") == allowed_bands(DEFAULT_LICENSE_CLASS)


def test_empty_string_license_class_falls_back_to_default():
    assert allowed_bands("") == allowed_bands(DEFAULT_LICENSE_CLASS)


def test_none_license_class_falls_back_to_default():
    assert allowed_bands(None) == allowed_bands(DEFAULT_LICENSE_CLASS)


def test_default_license_class_is_unrestricted():
    """Le fallback par défaut ne doit jamais masquer silencieusement des bandes non demandées."""

    assert allowed_bands(DEFAULT_LICENSE_CLASS) == _ALL_BAND_NAMES


# ------------------------------------------------------------------
# available_license_classes() -- pour peupler un sélecteur Settings
# ------------------------------------------------------------------

def test_available_license_classes_includes_harec_and_on3():
    ids = [class_id for class_id, _label in available_license_classes()]

    assert "HAREC" in ids
    assert "ON3" in ids


def test_available_license_classes_labels_are_non_empty_strings():
    for _class_id, label in available_license_classes():
        assert isinstance(label, str)
        assert label != ""


def test_available_license_classes_matches_registry_size():
    assert len(available_license_classes()) == len(LICENSE_CLASSES)


# ------------------------------------------------------------------
# Vocabulaire des bandes -- jamais un nom hors BandManager.BANDS
# ------------------------------------------------------------------

def test_every_allowed_band_in_every_class_is_a_real_band_manager_band():
    """Non-régression architecturale : ce registre ne doit jamais inventer un nom de bande."""

    for class_id, _label in available_license_classes():
        assert allowed_bands(class_id).issubset(_ALL_BAND_NAMES)
