"""Tests pour la base commune apps/contest/simple_form_dialog.py"""

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_fields_prefilled_from_values(qapp):
    from apps.contest.simple_form_dialog import SimpleFormDialog

    class Dummy(SimpleFormDialog):
        FIELDS = [("name", "Nom"), ("club", "Club")]

    dialog = Dummy({"name": "ON3RT", "club": ""}, "Titre")
    assert dialog.windowTitle() == "Titre"
    assert dialog.text("name") == "ON3RT"
    assert dialog.text("club") == ""
    assert dialog.values() == {"name": "ON3RT", "club": ""}


def test_int_value_falls_back_on_invalid_input(qapp):
    from apps.contest.simple_form_dialog import SimpleFormDialog

    class Dummy(SimpleFormDialog):
        FIELDS = [("count", "Count")]

    dialog = Dummy({"count": "abc"}, "Titre")
    assert dialog.int_value("count", default=7) == 7

    dialog2 = Dummy({"count": "42"}, "Titre")
    assert dialog2.int_value("count") == 42


def test_qso_edit_dialog_uppercases_callsign_and_mode(qapp):
    from apps.contest.qso_edit_dialog import QSOEditDialog

    dialog = QSOEditDialog({
        "id": 1, "callsign": "on3rt", "mode": "ssb",
        "serial_sent": "3", "points": "not-a-number",
    })
    values = dialog.values()
    assert values["callsign"] == "ON3RT"
    assert values["mode"] == "SSB"
    assert values["serial_sent"] == 3
    assert values["points"] == 0


def test_cabrillo_export_dialog_uses_simple_form_dialog_behavior(qapp):
    from apps.contest.cabrillo_export_dialog import CabrilloExportDialog

    cab = CabrilloExportDialog({"callsign": "ON3RT"})
    assert cab.values()["callsign"] == "ON3RT"
