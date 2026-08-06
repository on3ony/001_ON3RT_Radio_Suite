"""
Tests de apps/dashboard/widgets/smeter_bar.py (SMeterBar).

Ne vérifie jamais le rendu pixel par pixel (non pertinent, fragile) --
uniquement le contrat public : set_target_level() anime TOUJOURS
depuis la valeur actuellement affichée (jamais depuis 0), clampe au
niveau documenté 0-255, et traite None comme "aucune lecture" (anime
vers 0, jamais une valeur inventée).
"""

import pytest
from PySide6.QtCore import QPropertyAnimation

from apps.dashboard.widgets.smeter_bar import SMeterBar


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def bar(qapp):
    return SMeterBar()


def test_initial_level_is_zero(bar):
    assert bar.level == 0.0


def test_set_target_level_animates_to_the_requested_level(bar):
    bar.set_target_level(120)

    assert bar._animation.endValue() == 120.0
    assert bar._animation.state() == QPropertyAnimation.State.Running


def test_set_target_level_starts_from_the_currently_displayed_value(bar):
    bar._set_level(60.0)  # simule une animation déjà en cours, arrêtée à mi-chemin

    bar.set_target_level(200)

    assert bar._animation.startValue() == 60.0
    assert bar._animation.endValue() == 200.0


def test_set_target_level_clamps_above_documented_maximum(bar):
    bar.set_target_level(999)

    assert bar._animation.endValue() == 255.0


def test_set_target_level_clamps_below_zero(bar):
    bar.set_target_level(-42)

    assert bar._animation.endValue() == 0.0


def test_set_target_level_none_animates_towards_zero(bar):
    bar._set_level(120.0)

    bar.set_target_level(None)

    assert bar._animation.endValue() == 0.0


def test_set_target_level_replaces_a_running_animation(bar):
    """Un nouvel appel pendant une animation en cours doit repartir de la valeur affichée à cet instant, pas de l'ancienne cible."""

    bar.set_target_level(255)
    bar._set_level(30.0)  # simule une valeur intermédiaire au moment du second appel

    bar.set_target_level(0)

    assert bar._animation.startValue() == 30.0
    assert bar._animation.endValue() == 0.0


def test_level_property_update_triggers_repaint_without_raising(bar):
    """_set_level() ne doit jamais lever, même appelé directement (utilisé en interne par QPropertyAnimation)."""

    bar._set_level(150.0)

    assert bar.level == 150.0
