"""
Tests de apps/contest_assistant/models.py.

Vérifie que MessageTemplate et SentMessage sont des structures de
données pures : champs, valeurs par défaut, égalité, et aucune
dépendance Qt ni à un autre service.
"""

import apps.contest_assistant.models as models_module
from apps.contest_assistant.models import MessageTemplate, SentMessage


def test_module_has_no_qt_or_service_dependency():
    forbidden_names = (
        "QObject",
        "Signal",
        "QWidget",
        "StationService",
        "SettingsService",
        "RadioService",
    )
    for name in forbidden_names:
        assert not hasattr(models_module, name), f"{name} ne doit pas être importé dans ce module"


def test_message_template_defaults():
    template = MessageTemplate()

    assert template.id is None
    assert template.label == ""
    assert template.text_fr == ""
    assert template.text_en == ""


def test_message_template_stores_fields():
    template = MessageTemplate(
        id=1,
        label="CQ",
        text_fr="CQ Concours de %MYCALL%",
        text_en="CQ Contest %MYCALL%",
    )

    assert template.id == 1
    assert template.label == "CQ"
    assert template.text_fr == "CQ Concours de %MYCALL%"
    assert template.text_en == "CQ Contest %MYCALL%"


def test_message_template_equality():
    a = MessageTemplate(id=1, label="CQ", text_fr="x", text_en="y")
    b = MessageTemplate(id=1, label="CQ", text_fr="x", text_en="y")

    assert a == b


def test_sent_message_defaults():
    entry = SentMessage()

    assert entry.timestamp == ""
    assert entry.serial == 0
    assert entry.resolved_text == ""


def test_sent_message_stores_fields():
    entry = SentMessage(timestamp="2026-07-30T12:00:00Z", serial=1, resolved_text="59 001")

    assert entry.timestamp == "2026-07-30T12:00:00Z"
    assert entry.serial == 1
    assert entry.resolved_text == "59 001"


def test_dataclasses_use_slots_and_reject_arbitrary_attributes():
    template = MessageTemplate()

    try:
        template.unexpected = "x"
    except AttributeError:
        pass
    else:
        raise AssertionError("MessageTemplate ne doit pas accepter d'attribut arbitraire (slots=True attendu)")

    entry = SentMessage()

    try:
        entry.unexpected = "x"
    except AttributeError:
        pass
    else:
        raise AssertionError("SentMessage ne doit pas accepter d'attribut arbitraire (slots=True attendu)")
