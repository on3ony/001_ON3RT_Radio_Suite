"""
Tests de apps/cw/macro_dialog.py.

Vérifie : pré-remplissage des 12 champs F1-F12 à partir des valeurs
reçues, retour des valeurs éditées via edited_macros(), et robustesse
si moins de 12 valeurs sont fournies en entrée -- ne doit jamais
planter ni perdre les emplacements restants (complétés à vide).
"""

import pytest

from apps.cw.macro_dialog import MACRO_COUNT, MacroEditDialog


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_dialog_prefills_all_twelve_fields(qapp):
    macros = [f"macro {i}" for i in range(MACRO_COUNT)]
    dialog = MacroEditDialog(macros)

    assert [field.text() for field in dialog._fields] == macros
    assert len(dialog._fields) == MACRO_COUNT

    dialog.close()


def test_dialog_pads_missing_values_with_empty_strings(qapp):
    dialog = MacroEditDialog(["CQ CQ DE ON3RT"])

    assert dialog._fields[0].text() == "CQ CQ DE ON3RT"
    assert all(field.text() == "" for field in dialog._fields[1:])
    assert len(dialog._fields) == MACRO_COUNT

    dialog.close()


def test_edited_macros_reflects_field_edits(qapp):
    dialog = MacroEditDialog([""] * MACRO_COUNT)

    dialog._fields[0].setText("CQ CQ DE ON3RT")
    dialog._fields[11].setText("73")

    result = dialog.edited_macros()

    assert result[0] == "CQ CQ DE ON3RT"
    assert result[11] == "73"
    assert result[1:11] == [""] * 10
    assert len(result) == MACRO_COUNT

    dialog.close()
