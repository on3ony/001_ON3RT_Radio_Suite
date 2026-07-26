"""Tests des actions d'édition/suppression de QSO dans ContestWindow."""

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
            self, db_path=tmp_path / "contest_actions.db"
        ),
    )

    from apps.contest.window import ContestWindow
    win = ContestWindow()
    yield win
    win.close()


def test_add_qso_stores_received_exchange_separately_from_sent(window):
    window.add_qso({
        "callsign": "ON4XYZ",
        "band": "20m",
        "mode": "SSB",
        "rst_sent": "59",
        "rst_recv": "59",
        "exchange_recv": "014",
        "qso_date": "20260723",
        "time_on": "0815",
    })

    qso = window.db.get_all_qsos()[0]
    assert qso["exchange_recv"] == "014"
    assert qso["serial_recv"] == 14
    assert qso["serial_sent"] == 1
    assert qso["exchange_sent"] == "001"


def test_edit_qso_updates_database(window, monkeypatch):
    qso_id = window.db.add_qso(callsign="ON3RT", serial_sent=1)
    window.refresh()

    from apps.contest.qso_edit_dialog import QSOEditDialog
    monkeypatch.setattr(QSOEditDialog, "exec", lambda self: QSOEditDialog.DialogCode.Accepted)
    monkeypatch.setattr(QSOEditDialog, "values", lambda self: {"callsign": "ON4XYZ"})

    window.edit_qso(qso_id)

    assert window.db.get_qso(qso_id)["callsign"] == "ON4XYZ"


def test_edit_qso_cancelled_leaves_database_untouched(window, monkeypatch):
    qso_id = window.db.add_qso(callsign="ON3RT", serial_sent=1)

    from apps.contest.qso_edit_dialog import QSOEditDialog
    monkeypatch.setattr(QSOEditDialog, "exec", lambda self: QSOEditDialog.DialogCode.Rejected)

    window.edit_qso(qso_id)

    assert window.db.get_qso(qso_id)["callsign"] == "ON3RT"


def test_delete_qso_confirmed_removes_row(window, monkeypatch):
    qso_id = window.db.add_qso(callsign="ON3RT", serial_sent=1)

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    window.delete_qso(qso_id)

    assert window.db.get_qso(qso_id) is None


def test_delete_qso_declined_keeps_row(window, monkeypatch):
    qso_id = window.db.add_qso(callsign="ON3RT", serial_sent=1)

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))

    window.delete_qso(qso_id)

    assert window.db.get_qso(qso_id) is not None
