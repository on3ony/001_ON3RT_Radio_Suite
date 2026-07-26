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


def test_show_about_does_not_crash(window, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    calls = []
    monkeypatch.setattr(
        QMessageBox, "about",
        staticmethod(lambda *a, **k: calls.append(a)),
    )

    window.show_about()

    assert len(calls) == 1


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


def test_delete_last_qso_resets_entry_to_001_when_journal_empty(window, monkeypatch):
    qso_id = window.db.add_qso(callsign="ON3RT", serial_sent=1)
    window.refresh()
    assert window.qso_entry.number.text() == "002"

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    window.delete_qso(qso_id)

    assert window.db.get_next_serial() == 1
    assert window.qso_entry.number.text() == "001"
    assert window.qso_entry.exchange.text() == "001"


def test_delete_qso_recalculates_entry_from_remaining_qsos(window, monkeypatch):
    window.db.add_qso(callsign="ON3RT", serial_sent=1)
    window.db.add_qso(callsign="ON4XYZ", serial_sent=2)
    third_id = window.db.add_qso(callsign="ON5ABC", serial_sent=3)
    window.refresh()
    assert window.qso_entry.number.text() == "004"

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    window.delete_qso(third_id)

    assert window.db.get_next_serial() == 3
    assert window.qso_entry.number.text() == "003"
    assert window.qso_entry.exchange.text() == "003"


def test_entry_seeded_from_existing_database_on_startup(qapp, tmp_path, monkeypatch):
    from apps.contest.database import ContestDatabase
    from apps.contest.window import ContestWindow

    seed_path = tmp_path / "contest_preexisting.db"
    seed_db = ContestDatabase(seed_path)
    seed_db.add_qso(callsign="ON3RT", serial_sent=1)
    seed_db.add_qso(callsign="ON4XYZ", serial_sent=2)
    seed_db.close()

    import apps.contest.database as database_module
    original_init = database_module.ContestDatabase.__init__
    monkeypatch.setattr(
        database_module.ContestDatabase, "__init__",
        lambda self, db_path=None: original_init(self, db_path=seed_path),
    )

    win = ContestWindow()
    try:
        assert win.qso_entry.number.text() == "003"
    finally:
        win.close()
