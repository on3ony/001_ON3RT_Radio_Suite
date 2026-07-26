"""Tests des métadonnées de concours et des actions Nouveau/Ouvrir/Enregistrer."""

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
            self, db_path=tmp_path / "contest_mgmt.db"
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


def test_contest_info_defaults_are_empty(window):
    info = window.db.get_contest_info()
    assert info["contest_name"] == ""
    assert info["callsign"] == ""


def test_edit_contest_properties_updates_title(window, monkeypatch):
    from apps.contest.contest_properties_dialog import ContestPropertiesDialog
    monkeypatch.setattr(
        ContestPropertiesDialog, "exec",
        lambda self: ContestPropertiesDialog.DialogCode.Accepted,
    )
    monkeypatch.setattr(
        ContestPropertiesDialog, "values",
        lambda self: {"contest_name": "CQ WW SSB", "callsign": "ON3RT"},
    )

    window.edit_contest_properties()

    assert window.db.get_contest_info()["contest_name"] == "CQ WW SSB"
    assert "CQ WW SSB" in window.windowTitle()


def test_new_contest_archives_and_resets(window, monkeypatch):
    window.db.add_qso(callsign="ON4XYZ", serial_sent=1)
    assert len(window.db.get_all_qsos()) == 1

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    from apps.contest.contest_properties_dialog import ContestPropertiesDialog
    monkeypatch.setattr(
        ContestPropertiesDialog, "exec",
        lambda self: ContestPropertiesDialog.DialogCode.Rejected,
    )

    db_path = window.db.db_path
    window.new_contest()

    assert window.db.get_all_qsos() == []
    archive_dir = db_path.parent / "archives"
    assert archive_dir.exists()
    assert any(archive_dir.iterdir())


def test_new_contest_declined_keeps_data(window, monkeypatch):
    window.db.add_qso(callsign="ON4XYZ", serial_sent=1)

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))

    window.new_contest()

    assert len(window.db.get_all_qsos()) == 1


def test_edit_contest_properties_saves_preferences(window, monkeypatch, tmp_path):
    from apps.contest.contest_properties_dialog import ContestPropertiesDialog
    monkeypatch.setattr(
        ContestPropertiesDialog, "exec",
        lambda self: ContestPropertiesDialog.DialogCode.Accepted,
    )
    monkeypatch.setattr(
        ContestPropertiesDialog, "values",
        lambda self: {
            "contest_name": "ARRL DX", "callsign": "ON6DEF",
            "operator": "Multi Operator", "category": "Multi",
            "power": "1000 W (HIGH)", "club": "ON3RT Radio Club",
        },
    )

    window.edit_contest_properties()

    from apps.contest.contest_preferences import load_last_contest_properties
    saved = load_last_contest_properties(tmp_path / "contest_preferences.ini")
    assert saved["contest_name"] == "ARRL DX"
    assert saved["callsign"] == "ON6DEF"
    assert saved["club"] == "ON3RT Radio Club"


def test_new_contest_prefills_dialog_from_saved_preferences(window, monkeypatch, tmp_path):
    from apps.contest.contest_preferences import save_last_contest_properties
    save_last_contest_properties({
        "contest_name": "REF HF", "callsign": "ON4XYZ",
        "operator": "Multi Operator", "category": "Multi",
        "power": "500 W", "club": "ON3RT Radio Club",
    }, tmp_path / "contest_preferences.ini")

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    from apps.contest.contest_properties_dialog import ContestPropertiesDialog
    captured = {}
    original_init = ContestPropertiesDialog.__init__

    def spy_init(self, info, parent=None):
        captured.update(info)
        original_init(self, info, parent)

    monkeypatch.setattr(ContestPropertiesDialog, "__init__", spy_init)
    monkeypatch.setattr(
        ContestPropertiesDialog, "exec",
        lambda self: ContestPropertiesDialog.DialogCode.Rejected,
    )

    window.new_contest()

    assert captured["contest_name"] == "REF HF"
    assert captured["callsign"] == "ON4XYZ"
    assert captured["operator"] == "Multi Operator"
    assert captured["power"] == "500 W"


def test_new_contest_saves_preferences_on_accept(window, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    from apps.contest.contest_properties_dialog import ContestPropertiesDialog
    monkeypatch.setattr(
        ContestPropertiesDialog, "exec",
        lambda self: ContestPropertiesDialog.DialogCode.Accepted,
    )
    monkeypatch.setattr(
        ContestPropertiesDialog, "values",
        lambda self: {
            "contest_name": "CQ WPX CW", "callsign": "ON5ABC",
            "operator": "Single Operator", "category": "SOAB",
            "power": "100 W (LOW)", "club": "",
        },
    )

    window.new_contest()

    assert window.db.get_contest_info()["contest_name"] == "CQ WPX CW"
    assert "CQ WPX CW" in window.windowTitle()

    from apps.contest.contest_preferences import load_last_contest_properties
    saved = load_last_contest_properties(tmp_path / "contest_preferences.ini")
    assert saved["contest_name"] == "CQ WPX CW"
    assert saved["callsign"] == "ON5ABC"


def test_open_contest_switches_database(window, monkeypatch, tmp_path):
    from apps.contest.database import ContestDatabase
    other_path = tmp_path / "other_contest.db"
    other_db = ContestDatabase(other_path)
    other_db.add_qso(callsign="OTHER", serial_sent=1)
    other_db.close()

    from PySide6.QtWidgets import QFileDialog
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName",
        staticmethod(lambda *a, **k: (str(other_path), "")),
    )

    window.open_contest()

    qsos = window.db.get_all_qsos()
    assert len(qsos) == 1
    assert qsos[0]["callsign"] == "OTHER"


def test_import_adif_adds_qsos(window, monkeypatch, tmp_path):
    adif_path = tmp_path / "import.adi"
    adif_path.write_text(
        "<CALL:6>ON4XYZ<QSO_DATE:8>20260723<TIME_ON:4>0815<EOR>\n",
        encoding="utf-8",
    )

    from PySide6.QtWidgets import QFileDialog, QMessageBox
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName",
        staticmethod(lambda *a, **k: (str(adif_path), "")),
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

    window.import_adif()

    qsos = window.db.get_all_qsos()
    assert len(qsos) == 1
    assert qsos[0]["callsign"] == "ON4XYZ"


def test_export_adif_writes_file(window, monkeypatch, tmp_path):
    window.db.add_qso(callsign="ON3RT", serial_sent=1)
    dest = tmp_path / "out.adi"

    from PySide6.QtWidgets import QFileDialog, QMessageBox
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **k: (str(dest), "")),
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

    window.export_adif()

    assert dest.exists()
    assert "ON3RT" in dest.read_text(encoding="utf-8")


def test_export_cabrillo_writes_file(window, monkeypatch, tmp_path):
    window.db.set_contest_info(contest_name="CQ-WW-SSB", callsign="ON3RT")
    window.db.add_qso(callsign="ON4XYZ", serial_sent=1, mode="SSB", band="20m")
    dest = tmp_path / "contest.log"

    from apps.contest.cabrillo_export_dialog import CabrilloExportDialog
    monkeypatch.setattr(
        CabrilloExportDialog, "exec",
        lambda self: CabrilloExportDialog.DialogCode.Accepted,
    )

    from PySide6.QtWidgets import QFileDialog, QMessageBox
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **k: (str(dest), "")),
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

    window.export_cabrillo()

    assert dest.exists()
    content = dest.read_text(encoding="utf-8")
    assert "CONTEST: CQ-WW-SSB" in content
    assert "ON4XYZ" in content


def test_export_cabrillo_cancelled_does_not_write_file(window, monkeypatch, tmp_path):
    from apps.contest.cabrillo_export_dialog import CabrilloExportDialog
    monkeypatch.setattr(
        CabrilloExportDialog, "exec",
        lambda self: CabrilloExportDialog.DialogCode.Rejected,
    )
    dest = tmp_path / "should_not_exist.log"

    window.export_cabrillo()

    assert not dest.exists()


def test_save_contest_as_copies_file(window, monkeypatch, tmp_path):
    window.db.add_qso(callsign="ON4XYZ", serial_sent=1)
    dest = tmp_path / "backup.db"

    from PySide6.QtWidgets import QFileDialog, QMessageBox
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **k: (str(dest), "")),
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

    window.save_contest_as()

    assert dest.exists()
