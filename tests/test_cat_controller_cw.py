"""
Tests de CATController.send_cw_message()/stop_cw_message()/set_keying_speed()
(libraries/cat/cat_controller.py) -- étape 2 du backend CI-V texte.

CATController est un pur passthrough vers CATEngine (même style que
read_frequency/set_ptt/etc.) : ces tests vérifient uniquement la
délégation, avec un double d'engine, jamais le vrai moteur CI-V.
"""

import pytest

from libraries.cat.cat_controller import CATController


class _FakeEngine:
    def __init__(self):
        self.calls = []

    def send_cw_message(self, text):
        self.calls.append(("send_cw_message", text))

    def stop_cw_message(self):
        self.calls.append(("stop_cw_message",))

    def set_keying_speed(self, wpm):
        self.calls.append(("set_keying_speed", wpm))


@pytest.fixture
def controller():
    c = CATController(port="COM_TEST")
    c.engine = _FakeEngine()
    return c


def test_send_cw_message_delegates_to_engine(controller):
    controller.send_cw_message("CQ ON3RT")

    assert controller.engine.calls == [("send_cw_message", "CQ ON3RT")]


def test_stop_cw_message_delegates_to_engine(controller):
    controller.stop_cw_message()

    assert controller.engine.calls == [("stop_cw_message",)]


def test_set_keying_speed_delegates_to_engine(controller):
    controller.set_keying_speed(25)

    assert controller.engine.calls == [("set_keying_speed", 25)]
