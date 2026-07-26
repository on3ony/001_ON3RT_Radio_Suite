"""Smoke test : le module contest doit pouvoir se construire sans planter."""

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_contest_window_builds(qapp, tmp_path, monkeypatch):
    from apps.contest import database as database_module
    original_init = database_module.ContestDatabase.__init__
    monkeypatch.setattr(
        database_module.ContestDatabase, "__init__",
        lambda self, db_path=None: original_init(
            self, db_path=tmp_path / "contest_smoke.db"
        ),
    )

    from apps.contest.window import ContestWindow
    window = ContestWindow()
    assert window.windowTitle()
    window.close()
