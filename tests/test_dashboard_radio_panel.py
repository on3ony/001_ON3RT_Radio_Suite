"""
Tests de apps/dashboard/panels/radio_panel.py (RadioPanel).

Aucun test dédié n'existait avant le rafraîchissement visuel du
2026-08-02 -- se concentre ici sur ce qui a réellement changé/est
nouveau : le badge RX/TX qui bascule vert/rouge, et surtout le widget
S-mètre qui doit consommer deux clés DISTINCTES de l'état partagé --
smeter_level (référence, pilote la barre animée) et smeter (texte
affiché à côté) -- sans jamais les confondre.
"""

import pytest

from apps.dashboard.panels.radio_panel import RadioPanel


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def panel(qapp):
    return RadioPanel(live_service=None)


def test_frequency_formats_with_dot_separators(panel):
    panel.update_from_state({"frequency": 14020000})

    assert panel.frequency.text() == "14.020.000 Hz"


def test_frequency_falls_back_to_dash_when_absent(panel):
    panel.update_from_state({})

    assert panel.frequency.text() == "--"


def test_ptt_badge_shows_rx_in_green_by_default(panel):
    panel.update_from_state({"ptt": False})

    assert panel.ptt.text() == "RX"
    assert "#00ff88" in panel.ptt.styleSheet()


def test_ptt_badge_shows_tx_in_red_when_transmitting(panel):
    panel.update_from_state({"ptt": True})

    assert panel.ptt.text() == "TX"
    assert "#ff6666" in panel.ptt.styleSheet()


# ------------------------------------------------------------------
# S-mètre : smeter_level (référence, barre) vs smeter (texte) --
# jamais l'un à la place de l'autre.
# ------------------------------------------------------------------

def test_smeter_text_comes_from_the_smeter_key(panel):
    panel.update_from_state({"smeter": "S9+20dB", "smeter_level": 150})

    assert panel.smeter.text() == "S9+20dB"


def test_smeter_bar_target_comes_from_the_smeter_level_key_not_the_text(panel):
    panel.update_from_state({"smeter": "S9+20dB", "smeter_level": 150})

    assert panel.smeter_bar._animation.endValue() == 150.0


def test_smeter_bar_ignores_smeter_text_entirely(panel):
    """Un texte "S9" avec un smeter_level absent ne doit jamais faire deviner une valeur numérique à la barre."""

    panel.update_from_state({"smeter": "S9", "smeter_level": None})

    assert panel.smeter_bar._animation.endValue() == 0.0


def test_smeter_falls_back_to_dash_and_bar_to_zero_when_state_is_empty(panel):
    panel.update_from_state({})

    assert panel.smeter.text() == "--"
    assert panel.smeter_bar._animation.endValue() == 0.0


def test_footer_combines_model_port_and_baudrate(panel):
    panel.update_from_state({"model": "IC-7300", "port": "COM3", "baudrate": 19200})

    assert panel.footer.text() == "IC-7300  ·  COM3  ·  19200 bauds"


def test_update_from_state_ignores_non_dict_state(panel):
    before = panel.frequency.text()

    panel.update_from_state("not a dict")
    panel.update_from_state(None)

    assert panel.frequency.text() == before
