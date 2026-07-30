"""
Tests de data/contest_assistant_seed.json.

Vérifie que la bibliothèque de messages par défaut est valide,
complète, utilise uniquement les variables définies dans la
conception, et correspond exactement à la forme de MessageTemplate.
"""

import json
import re
from pathlib import Path

import pytest

from apps.contest_assistant.models import MessageTemplate

SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "contest_assistant_seed.json"

_ALLOWED_VARIABLES = {"MYCALL", "CALL", "RST", "SERIAL"}
_VARIABLE_RE = re.compile(r"%([A-Z]+)%")

_EXPECTED_LABELS = [
    "CQ",
    "QRZ",
    "Réponse",
    "Échange",
    "Mon indicatif",
    "TU 73",
    "Merci",
    "QSL",
    "Répétition",
]


@pytest.fixture(scope="module")
def seed_data():
    with SEED_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_seed_file_exists_and_is_valid_json(seed_data):
    assert isinstance(seed_data, list)


def test_seed_contains_exactly_the_nine_expected_labels_in_order(seed_data):
    labels = [entry["label"] for entry in seed_data]
    assert labels == _EXPECTED_LABELS


def test_new_entries_have_the_expected_bilingual_text(seed_data):
    """Vérifie le contenu exact des 4 nouveaux modèles demandés."""

    by_label = {entry["label"]: entry for entry in seed_data}

    assert by_label["Mon indicatif"]["text_fr"] == "%MYCALL%"
    assert by_label["Mon indicatif"]["text_en"] == "%MYCALL%"

    assert by_label["Réponse"]["text_fr"] == "%CALL% de %MYCALL%"
    assert by_label["Réponse"]["text_en"] == "%CALL% from %MYCALL%"

    assert by_label["QRZ"]["text_fr"] == "QRZ de %MYCALL%"
    assert by_label["QRZ"]["text_en"] == "QRZ de %MYCALL%"

    assert by_label["TU 73"]["text_fr"] == "TU 73 %CALL%"
    assert by_label["TU 73"]["text_en"] == "TU 73 %CALL%"


def test_each_entry_has_exactly_the_fields_of_a_seedable_message_template(seed_data):
    for entry in seed_data:
        assert set(entry.keys()) == {"label", "text_fr", "text_en"}


def test_each_entry_has_non_empty_french_and_english_text(seed_data):
    for entry in seed_data:
        assert entry["text_fr"].strip() != ""
        assert entry["text_en"].strip() != ""


def test_each_entry_only_uses_approved_variables(seed_data):
    for entry in seed_data:
        for field in ("text_fr", "text_en"):
            used = set(_VARIABLE_RE.findall(entry[field]))
            unknown = used - _ALLOWED_VARIABLES
            assert not unknown, f"{field} de '{entry['label']}' utilise une variable inconnue : {unknown}"


def test_each_entry_can_construct_a_valid_message_template(seed_data):
    """
    Non-régression de forme : chaque entrée doit pouvoir construire un
    MessageTemplate sans erreur, en n'ajoutant que l'id (assigné par
    ContestMessageService, absent du fichier de données).
    """
    for entry in seed_data:
        template = MessageTemplate(id=None, **entry)
        assert template.label == entry["label"]
        assert template.text_fr == entry["text_fr"]
        assert template.text_en == entry["text_en"]
