"""Vérifie que toutes les actions de menu/toolbar sont connectées,
à l'exception des boutons QRZ/CAT (intégrations hors périmètre du
module contest, non implémentées volontairement)."""

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    from apps.contest import database as database_module
    original_init = database_module.ContestDatabase.__init__
    monkeypatch.setattr(
        database_module.ContestDatabase, "__init__",
        lambda self, db_path=None: original_init(
            self, db_path=tmp_path / "contest_wiring.db"
        ),
    )

    from apps.contest import contest_preferences
    monkeypatch.setattr(
        contest_preferences, "_default_path",
        lambda: tmp_path / "contest_preferences.ini",
    )

    from apps.contest.window import ContestWindow
    win = ContestWindow()
    yield win
    win.close()


def _leaf_menu_actions(menu):
    actions = []
    for action in menu.actions():
        if action.menu() is not None:
            actions.extend(_leaf_menu_actions(action.menu()))
        elif not action.isSeparator():
            actions.append(action)
    return actions


def test_all_menu_actions_are_connected(window):
    actions = _leaf_menu_actions(window.menuBar())
    assert len(actions) >= 9

    unconnected = [a.text() for a in actions if a.receivers("2triggered(bool)") == 0]
    assert unconnected == []


def test_toolbar_actions_connected_except_documented_gaps(window):
    from PySide6.QtWidgets import QToolBar

    toolbars = window.findChildren(QToolBar)
    assert len(toolbars) == 1

    known_unconnected = {"QRZ", "CAT"}
    for action in toolbars[0].actions():
        if action.isSeparator() or action.text() in known_unconnected:
            continue
        assert action.receivers("2triggered(bool)") > 0, action.text()
