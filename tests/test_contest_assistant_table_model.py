"""
Tests de apps/contest_assistant/table_model.py.

Vérifie MessageTemplateTableModel et SentMessageTableModel en pur
isolation : aucun ContestMessageService requis, uniquement les
dataclasses MessageTemplate/SentMessage.
"""

import pytest

from apps.contest_assistant.models import MessageTemplate, SentMessage
from apps.contest_assistant.table_model import MessageTemplateTableModel, SentMessageTableModel


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


# ------------------------------------------------------------------
# MessageTemplateTableModel
# ------------------------------------------------------------------

def test_message_template_model_starts_empty(qapp):
    model = MessageTemplateTableModel()

    assert model.rowCount() == 0
    assert model.columnCount() == 2
    assert model.template_at(0) is None


def test_message_template_model_exposes_label_and_active_text(qapp):
    model = MessageTemplateTableModel()
    template = MessageTemplate(id=1, label="CQ", text_fr="CQ FR", text_en="CQ EN")
    model.set_templates([template])

    assert model.rowCount() == 1
    assert model.data(model.index(0, 0)) == "CQ"
    assert model.data(model.index(0, 1)) == "CQ FR"  # langue par défaut FR


def test_message_template_model_switches_text_with_language(qapp):
    model = MessageTemplateTableModel()
    template = MessageTemplate(id=1, label="CQ", text_fr="CQ FR", text_en="CQ EN")
    model.set_templates([template])

    model.set_language("EN")

    assert model.data(model.index(0, 1)) == "CQ EN"

    model.set_language("FR")
    assert model.data(model.index(0, 1)) == "CQ FR"


def test_message_template_model_header_data(qapp):
    from PySide6.QtCore import Qt

    model = MessageTemplateTableModel()

    assert model.headerData(0, Qt.Orientation.Horizontal) == "Libellé"
    assert model.headerData(1, Qt.Orientation.Horizontal) == "Message"
    assert model.headerData(0, Qt.Orientation.Vertical) == 1


def test_message_template_model_template_at_maps_row_to_object(qapp):
    model = MessageTemplateTableModel()
    a = MessageTemplate(id=1, label="A", text_fr="a", text_en="a")
    b = MessageTemplate(id=2, label="B", text_fr="b", text_en="b")
    model.set_templates([a, b])

    assert model.template_at(0) is a
    assert model.template_at(1) is b
    assert model.template_at(2) is None  # hors limites


def test_message_template_model_set_templates_replaces_previous_rows(qapp):
    model = MessageTemplateTableModel()
    model.set_templates([MessageTemplate(id=1, label="A", text_fr="a", text_en="a")])

    model.set_templates([MessageTemplate(id=2, label="B", text_fr="b", text_en="b")])

    assert model.rowCount() == 1
    assert model.data(model.index(0, 0)) == "B"


# ------------------------------------------------------------------
# SentMessageTableModel
# ------------------------------------------------------------------

def test_sent_message_model_starts_empty(qapp):
    model = SentMessageTableModel()

    assert model.rowCount() == 0
    assert model.columnCount() == 3


def test_sent_message_model_exposes_all_columns(qapp):
    model = SentMessageTableModel()
    entry = SentMessage(timestamp="2026-07-30T12:00:00Z", serial=7, resolved_text="599 007")
    model.set_entries([entry])

    assert model.data(model.index(0, 0)) == "2026-07-30T12:00:00Z"
    assert model.data(model.index(0, 1)) == "007"
    assert model.data(model.index(0, 2)) == "599 007"


def test_sent_message_model_header_data(qapp):
    from PySide6.QtCore import Qt

    model = SentMessageTableModel()

    assert model.headerData(0, Qt.Orientation.Horizontal) == "Heure"
    assert model.headerData(1, Qt.Orientation.Horizontal) == "N°"
    assert model.headerData(2, Qt.Orientation.Horizontal) == "Message"
