"""Tests pour apps/contest/contest_properties_dialog.py"""

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_defaults_when_info_is_empty(qapp):
    from apps.contest.contest_properties_dialog import (
        ContestPropertiesDialog, OPERATOR_CATEGORIES, CONTEST_CATEGORIES,
        DEFAULT_CALLSIGN, DEFAULT_POWER,
    )

    dialog = ContestPropertiesDialog({})
    values = dialog.values()

    assert values["contest_name"] == ""
    assert values["callsign"] == DEFAULT_CALLSIGN
    assert values["operator"] == OPERATOR_CATEGORIES[0]
    assert values["category"] == CONTEST_CATEGORIES[0]
    assert values["power"] == DEFAULT_POWER
    assert values["club"] == ""


def test_prefills_from_known_values(qapp):
    from apps.contest.contest_properties_dialog import ContestPropertiesDialog

    dialog = ContestPropertiesDialog({
        "contest_name": "CQ WW DX CW",
        "callsign": "ON4XYZ",
        "operator": "Multi Operator",
        "category": "Multi",
        "power": "1000 W (HIGH)",
        "club": "ON3RT Radio Club",
    })
    values = dialog.values()

    assert values == {
        "contest_name": "CQ WW DX CW",
        "callsign": "ON4XYZ",
        "operator": "Multi Operator",
        "category": "Multi",
        "power": "1000 W (HIGH)",
        "club": "ON3RT Radio Club",
    }


def test_contest_name_combo_is_editable_for_custom_values(qapp):
    from apps.contest.contest_properties_dialog import ContestPropertiesDialog

    dialog = ContestPropertiesDialog({"contest_name": "Field Day Belgium"})
    assert dialog.contest_name.isEditable()
    assert dialog.values()["contest_name"] == "Field Day Belgium"


def test_selecting_autre_clears_text_for_custom_entry(qapp):
    from apps.contest.contest_properties_dialog import ContestPropertiesDialog

    dialog = ContestPropertiesDialog({})
    autre_index = dialog.contest_name.findText("Autre...")
    assert autre_index >= 0

    dialog.contest_name.setCurrentIndex(autre_index)
    dialog._clear_on_autre(autre_index)
    assert dialog.contest_name.currentText() == ""

    dialog.contest_name.setEditText("Concours Maison ON")
    assert dialog.values()["contest_name"] == "Concours Maison ON"


def test_operator_and_category_are_restricted_to_known_choices(qapp):
    from apps.contest.contest_properties_dialog import (
        ContestPropertiesDialog, OPERATOR_CATEGORIES, CONTEST_CATEGORIES, POWER_LEVELS,
    )

    dialog = ContestPropertiesDialog({})
    assert not dialog.operator.isEditable()
    assert not dialog.category.isEditable()
    assert not dialog.power.isEditable()

    assert [dialog.operator.itemText(i) for i in range(dialog.operator.count())] == OPERATOR_CATEGORIES
    assert [dialog.category.itemText(i) for i in range(dialog.category.count())] == CONTEST_CATEGORIES
    assert [dialog.power.itemText(i) for i in range(dialog.power.count())] == POWER_LEVELS
