"""
Tests de CATController.set_data_mode() (libraries/cat/cat_controller.py).

CATController est un pur passthrough vers CATEngine (même style que
read_frequency/set_ptt/etc.) : ces tests vérifient uniquement la
délégation, avec un double d'engine, jamais le vrai moteur CI-V --
même méthode que tests/test_cat_controller_cw.py.

Vérifie également, suite au chantier "Correction DATA Mode IC-7300"
(2026-08-05), que la valeur de retour de l'engine (True/False selon
ACK/NG) est bien propagée par le controller -- avant cette correction,
set_data_mode() ne retournait rien ici, perdant l'information au
passage.
"""

import pytest

from libraries.cat.cat_controller import CATController


class _FakeEngine:
    def __init__(self, return_value=True):
        self.calls = []
        self._return_value = return_value

    def set_data_mode(self, enabled):
        self.calls.append(("set_data_mode", enabled))
        return self._return_value


@pytest.fixture
def controller():
    c = CATController(port="COM_TEST")
    c.engine = _FakeEngine()
    return c


def test_set_data_mode_delegates_to_engine_when_enabling(controller):
    controller.set_data_mode(True)

    assert controller.engine.calls == [("set_data_mode", True)]


def test_set_data_mode_delegates_to_engine_when_disabling(controller):
    controller.set_data_mode(False)

    assert controller.engine.calls == [("set_data_mode", False)]


def test_set_data_mode_returns_engine_result_on_ack():
    c = CATController(port="COM_TEST")
    c.engine = _FakeEngine(return_value=True)

    assert c.set_data_mode(True) is True


def test_set_data_mode_returns_engine_result_on_ng():
    """Le NG remonté par CATEngine ne doit pas se perdre au passage dans CATController."""

    c = CATController(port="COM_TEST")
    c.engine = _FakeEngine(return_value=False)

    assert c.set_data_mode(True) is False
