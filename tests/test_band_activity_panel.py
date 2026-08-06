"""
Tests de apps/dashboard/panels/band_activity_panel.py (BandActivityPanel).

Chantier "Tuile Activité par bande", étapes 3 et 4 : le panneau
construit ses lignes dynamiquement à partir de la classe de licence
active (StationService.license_class -> libraries.radio.license_privileges),
sans jamais coder une bande en dur, et affiche tel quel ce que lui
fournit state["bands"] = {"<bande>": {"count": int, "color": "#RRGGBB"}}
sans effectuer lui-même le moindre calcul (fenêtre glissante, seuils
de couleur -- tout cela vit dans band_activity_source.py, testé
séparément dans tests/test_band_activity_source.py).
"""

from types import SimpleNamespace

import pytest

from apps.dashboard.panels.band_activity_panel import (
    DEMO_VALUE,
    NEUTRAL_COLOR,
    BandActivityPanel,
    resolve_displayed_bands,
)
from libraries.radio.band_manager import BandManager


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _station(license_class):
    return SimpleNamespace(license_class=license_class)


# ------------------------------------------------------------------
# resolve_displayed_bands() -- fonction pure
# ------------------------------------------------------------------

def test_on3_resolves_to_exactly_the_five_expected_bands_in_band_manager_order():
    bands = resolve_displayed_bands(_station("ON3"))

    assert bands == ["80m", "40m", "20m", "15m", "10m"]


def test_harec_resolves_to_every_band_manager_band_in_order():
    bands = resolve_displayed_bands(_station("HAREC"))

    assert bands == [b.name for b in BandManager.BANDS]


def test_none_station_service_falls_back_to_unrestricted_default():
    """Jamais de plantage ni de liste vide inventée si station_service est absent."""

    bands = resolve_displayed_bands(None)

    assert bands == [b.name for b in BandManager.BANDS]


def test_station_service_without_license_class_attribute_falls_back_gracefully():
    bands = resolve_displayed_bands(SimpleNamespace())

    assert bands == [b.name for b in BandManager.BANDS]


# ------------------------------------------------------------------
# Construction dynamique du panneau
# ------------------------------------------------------------------

def test_on3_panel_builds_exactly_five_rows(qapp):
    panel = BandActivityPanel(_station("ON3"), live_service=None)

    assert list(panel._value_labels.keys()) == ["80m", "40m", "20m", "15m", "10m"]


def test_on3_panel_never_builds_a_row_for_a_forbidden_band(qapp):
    panel = BandActivityPanel(_station("ON3"), live_service=None)

    for forbidden in ("160m", "30m", "17m", "12m", "6m"):
        assert forbidden not in panel._value_labels


def test_harec_panel_builds_a_row_for_every_band_manager_band(qapp):
    panel = BandActivityPanel(_station("HAREC"), live_service=None)

    assert len(panel._value_labels) == len(BandManager.BANDS)
    assert "160m" in panel._value_labels
    assert "6m" in panel._value_labels


def test_panel_construction_never_crashes_without_station_service(qapp):
    panel = BandActivityPanel(None, live_service=None)

    assert len(panel._value_labels) == len(BandManager.BANDS)


def test_module_defines_no_hardcoded_band_list_constant():
    """
    Non-régression architecturale explicitement demandée : contrairement
    à l'ancienne version (BANDS = ["160m", "80m", ...] codée en dur),
    ce module ne doit plus définir aucune constante de liste de bandes
    -- resolve_displayed_bands() doit être l'unique chemin.
    """

    import apps.dashboard.panels.band_activity_panel as module

    assert not hasattr(module, "BANDS")


def test_panel_module_contains_no_business_logic_constants():
    """
    Non-régression explicitement demandée à l'étape 4 : la fenêtre
    glissante et les seuils de couleur doivent vivre uniquement dans
    band_activity_source.py, jamais ici.
    """

    import apps.dashboard.panels.band_activity_panel as module

    for name in ("WINDOW_MINUTES", "THRESHOLD_LOW_MAX", "THRESHOLD_MEDIUM_MAX", "color_for_spot_count"):
        assert not hasattr(module, name)


# ------------------------------------------------------------------
# update_state() -- affichage pur, aucun calcul
# ------------------------------------------------------------------

@pytest.fixture
def on3_panel(qapp):
    return BandActivityPanel(_station("ON3"), live_service=None)


def test_update_state_with_no_bands_key_shows_demo_value_in_neutral_color(on3_panel):
    on3_panel.update_state({})

    label = on3_panel._value_labels["20m"]
    assert label.text() == DEMO_VALUE
    assert NEUTRAL_COLOR in label.styleSheet()


def test_update_state_displays_the_count_and_color_exactly_as_provided(on3_panel):
    """Le panneau n'interprète rien : il affiche count et color tels quels."""

    on3_panel.update_state({"bands": {"20m": {"count": 7, "color": "#e8a63d"}}})

    label = on3_panel._value_labels["20m"]
    assert label.text() == "7"
    assert "#e8a63d" in label.styleSheet()


def test_update_state_displays_zero_count_with_whatever_color_was_provided(on3_panel):
    """Le panneau ne décide jamais lui-même qu'un compte à 0 doit être gris -- c'est déjà dans "color"."""

    on3_panel.update_state({"bands": {"15m": {"count": 0, "color": "#5f6e8a"}}})

    label = on3_panel._value_labels["15m"]
    assert label.text() == "0"
    assert "#5f6e8a" in label.styleSheet()


def test_update_state_ignores_a_forbidden_band_present_in_the_data_without_crashing(on3_panel):
    """Le DX Cluster peut légitimement spotter du 160m -- le panneau ON3 doit l'ignorer silencieusement, jamais planter."""

    on3_panel.update_state({"bands": {"160m": {"count": 20, "color": "#f0464f"}, "20m": {"count": 3, "color": "#2ed17e"}}})

    assert "160m" not in on3_panel._value_labels
    assert on3_panel._value_labels["20m"].text() == "3"


def test_update_state_with_malformed_bands_value_does_not_crash(on3_panel):
    on3_panel.update_state({"bands": "not a dict"})

    label = on3_panel._value_labels["20m"]
    assert label.text() == DEMO_VALUE


def test_update_state_with_malformed_entry_falls_back_to_neutral_display(on3_panel):
    """Une entrée qui n'a pas la forme attendue (pas de dict avec "count") ne doit jamais planter ni afficher n'importe quoi."""

    on3_panel.update_state({"bands": {"20m": "not a dict"}})

    label = on3_panel._value_labels["20m"]
    assert label.text() == DEMO_VALUE
    assert NEUTRAL_COLOR in label.styleSheet()


# ------------------------------------------------------------------
# Bargraph -- mise à l'échelle graphique locale (jamais un calcul métier)
# ------------------------------------------------------------------

def test_no_data_yet_bar_is_empty_and_neutral(on3_panel):
    on3_panel.update_state({})

    bar = on3_panel._bars["20m"]
    assert bar.value() == 0
    assert NEUTRAL_COLOR in bar.styleSheet()


def test_the_most_active_band_fills_its_bar_completely(on3_panel):
    """La bande la plus active, quelle que soit sa valeur absolue, doit toujours atteindre 100% -- c'est le principe de l'échelle auto-adaptative."""

    on3_panel.update_state({
        "bands": {
            "80m": {"count": 2, "color": "#2ed17e"},
            "20m": {"count": 9, "color": "#f0464f"},
        }
    })

    bar_20m = on3_panel._bars["20m"]
    assert bar_20m.value() == bar_20m.maximum()


def test_a_less_active_band_fills_proportionally_to_the_observed_maximum(on3_panel):
    on3_panel.update_state({
        "bands": {
            "80m": {"count": 2, "color": "#2ed17e"},
            "20m": {"count": 8, "color": "#e8a63d"},
        }
    })

    bar_80m = on3_panel._bars["80m"]
    assert bar_80m.maximum() == 8
    assert bar_80m.value() == 2


def test_scale_adapts_when_overall_activity_is_very_low(qapp):
    """Même avec une activité globale faible (max=1), la bande la plus active doit rester lisible (barre pleine), sans retoucher les seuils."""

    from apps.dashboard.panels.band_activity_panel import BandActivityPanel

    panel = BandActivityPanel(_station("ON3"), live_service=None)
    panel.update_state({"bands": {"20m": {"count": 1, "color": "#2ed17e"}}})

    bar = panel._bars["20m"]
    assert bar.maximum() == 1
    assert bar.value() == 1


def test_all_bands_at_zero_never_divides_by_zero_and_leaves_bars_empty(on3_panel):
    on3_panel.update_state({
        "bands": {band: {"count": 0, "color": "#5f6e8a"} for band in ("80m", "40m", "20m", "15m", "10m")}
    })

    for band in ("80m", "40m", "20m", "15m", "10m"):
        bar = on3_panel._bars[band]
        assert bar.value() == 0


def test_bar_color_matches_the_value_label_color(on3_panel):
    """La barre et le chiffre doivent toujours être dans la même couleur (demande explicite)."""

    on3_panel.update_state({"bands": {"15m": {"count": 5, "color": "#e8a63d"}}})

    assert "#e8a63d" in on3_panel._bars["15m"].styleSheet()
    assert "#e8a63d" in on3_panel._value_labels["15m"].styleSheet()


def test_forbidden_band_in_data_never_creates_a_bar(on3_panel):
    on3_panel.update_state({"bands": {"160m": {"count": 20, "color": "#f0464f"}}})

    assert "160m" not in on3_panel._bars


def test_panel_bar_height_is_thicker_than_the_original_eleven_pixels():
    """Ajustement explicitement demandé : la barre doit être bien visible ("un peu plus épaisse")."""

    from apps.dashboard.panels.band_activity_panel import BAR_HEIGHT

    assert BAR_HEIGHT > 11
