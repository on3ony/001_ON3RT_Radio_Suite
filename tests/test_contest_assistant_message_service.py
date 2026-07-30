"""
Tests de apps/contest_assistant/message_service.py.

Vérifie : chargement des modèles depuis le fichier seed au premier
lancement (et seulement là), persistance atomique, langue, CRUD des
modèles, numéro progressif, historique, reset_contest() (règles
validées : nom/numéro/historique remis à zéro, modèles et langue
jamais touchés), et resolve_variables().
"""

import json

import pytest

from apps.contest_assistant.message_service import ContestMessageService, resolve_variables
from apps.contest_assistant.models import MessageTemplate, SentMessage

_SEED = [
    {"label": "CQ", "text_fr": "CQ Concours de %MYCALL%", "text_en": "CQ Contest %MYCALL%"},
    {"label": "Échange", "text_fr": "%RST% %SERIAL%", "text_en": "%RST% %SERIAL%"},
]


@pytest.fixture
def seed_path(tmp_path):
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(_SEED), encoding="utf-8")
    return path


@pytest.fixture
def config_path(tmp_path):
    return tmp_path / "contest_assistant.json"


# ------------------------------------------------------------------
# Aucune dépendance GUI / autre service
# ------------------------------------------------------------------

def test_module_has_no_qt_or_other_service_dependency():
    import apps.contest_assistant.message_service as module

    forbidden_names = ("QObject", "Signal", "QWidget", "StationService", "SettingsService", "RadioService")
    for name in forbidden_names:
        assert not hasattr(module, name), f"{name} ne doit pas être importé dans ce service"


# ------------------------------------------------------------------
# Chargement initial depuis le fichier seed
# ------------------------------------------------------------------

def test_first_launch_loads_templates_from_seed_and_persists_immediately(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)

    assert [t.label for t in service.templates] == ["CQ", "Échange"]
    assert [t.id for t in service.templates] == [1, 2]
    assert config_path.exists()  # sauvegardé immédiatement, pas seulement en mémoire


def test_first_launch_without_a_seed_file_starts_with_no_templates(config_path, tmp_path):
    service = ContestMessageService(config_path=config_path, seed_path=tmp_path / "missing_seed.json")

    assert service.templates == []


def test_reloading_an_existing_file_does_not_reseed_even_if_all_templates_were_deleted(config_path, seed_path):
    first = ContestMessageService(config_path=config_path, seed_path=seed_path)
    for template in list(first.templates):
        first.delete_template(template.id)
    assert first.templates == []

    second = ContestMessageService(config_path=config_path, seed_path=seed_path)

    assert second.templates == []  # pas reseedé malgré la présence du fichier seed


# ------------------------------------------------------------------
# Persistance : aller-retour complet
# ------------------------------------------------------------------

def test_save_then_reload_round_trips_full_state(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    service.contest_name = "CQ WW DX SSB"
    service.toggle_language()
    service.record_sent("59 001")
    service.save()

    reloaded = ContestMessageService(config_path=config_path, seed_path=seed_path)

    assert reloaded.contest_name == "CQ WW DX SSB"
    assert reloaded.language == "EN"
    assert reloaded.serial == 1
    assert len(reloaded.history) == 1
    assert reloaded.history[0].resolved_text == "59 001"
    assert len(reloaded.templates) == 2


def test_corrupt_file_falls_back_to_defaults_without_crashing(config_path, seed_path):
    config_path.write_text("{ceci n'est pas du JSON", encoding="utf-8")

    service = ContestMessageService(config_path=config_path, seed_path=seed_path)

    assert service.contest_name == ""
    assert service.language == "FR"
    assert service.serial == 0
    assert service.history == []


def test_malformed_template_entry_is_skipped_without_crashing(config_path, seed_path):
    config_path.write_text(
        json.dumps(
            {
                "contest_name": "",
                "language": "FR",
                "serial": 0,
                "templates": [
                    {"id": 1, "label": "OK", "text_fr": "x", "text_en": "y"},
                    {"unexpected_field": "bad"},
                ],
                "history": [],
            }
        ),
        encoding="utf-8",
    )

    service = ContestMessageService(config_path=config_path, seed_path=seed_path)

    assert [t.label for t in service.templates] == ["OK"]


# ------------------------------------------------------------------
# Langue
# ------------------------------------------------------------------

def test_toggle_language_flips_between_fr_and_en(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    assert service.language == "FR"

    service.toggle_language()
    assert service.language == "EN"

    service.toggle_language()
    assert service.language == "FR"


def test_active_text_follows_current_language(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    template = service.templates[0]

    assert service.active_text(template) == template.text_fr

    service.toggle_language()
    assert service.active_text(template) == template.text_en


# ------------------------------------------------------------------
# CRUD des modèles
# ------------------------------------------------------------------

def test_add_template_assigns_a_sequential_id_and_persists(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)

    new_template = service.add_template("Merci", "Merci %CALL%", "Thank you %CALL%")

    assert new_template.id == 3  # après les 2 modèles du seed (id 1 et 2)
    assert [t.label for t in service.templates] == ["CQ", "Échange", "Merci"]

    reloaded = ContestMessageService(config_path=config_path, seed_path=seed_path)
    assert [t.label for t in reloaded.templates] == ["CQ", "Échange", "Merci"]


def test_add_template_id_accounts_for_gaps_left_by_deletion(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    service.delete_template(2)  # ne laisse que l'id 1

    new_template = service.add_template("Nouveau", "x", "y")

    assert new_template.id == 2  # max(id existants)=1 + 1, jamais de collision


def test_update_template_replaces_only_the_matching_entry(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)

    service.update_template(1, "CQ modifié", "Nouveau texte FR", "New EN text")

    updated = next(t for t in service.templates if t.id == 1)
    untouched = next(t for t in service.templates if t.id == 2)

    assert updated.label == "CQ modifié"
    assert updated.text_fr == "Nouveau texte FR"
    assert untouched.label == "Échange"  # non modifié


def test_delete_template_removes_only_the_matching_entry(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)

    service.delete_template(1)

    assert [t.id for t in service.templates] == [2]


# ------------------------------------------------------------------
# Numéro progressif et historique
# ------------------------------------------------------------------

def test_next_serial_previews_without_mutating_state(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)

    assert service.next_serial == 1
    assert service.serial == 0  # aperçu seul, aucune mutation

    assert service.next_serial == 1  # stable tant que rien n'a été envoyé


def test_record_sent_increments_serial_and_appends_history(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)

    entry = service.record_sent("59 001")

    assert isinstance(entry, SentMessage)
    assert entry.serial == 1
    assert entry.resolved_text == "59 001"
    assert entry.timestamp != ""
    assert service.serial == 1
    assert service.next_serial == 2
    assert len(service.history) == 1

    service.record_sent("59 002")
    assert service.serial == 2
    assert len(service.history) == 2


# ------------------------------------------------------------------
# reset_contest() — règles validées explicitement par l'utilisateur
# ------------------------------------------------------------------

def test_reset_contest_clears_name_serial_and_history_only(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    service.contest_name = "CQ WW DX SSB"
    service.toggle_language()  # EN
    service.record_sent("59 001")
    original_templates = list(service.templates)

    service.reset_contest()

    assert service.contest_name == ""
    assert service.serial == 0
    assert service.history == []
    assert service.language == "EN"  # jamais touché
    assert service.templates == original_templates  # jamais touchés


def test_reset_contest_persists_immediately(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    service.contest_name = "CQ WW DX SSB"
    service.record_sent("59 001")

    service.reset_contest()

    reloaded = ContestMessageService(config_path=config_path, seed_path=seed_path)
    assert reloaded.contest_name == ""
    assert reloaded.serial == 0
    assert reloaded.history == []


# ------------------------------------------------------------------
# resolve_variables()
# ------------------------------------------------------------------

def test_resolve_variables_substitutes_known_markers():
    result = resolve_variables(
        "%RST% %SERIAL% de %MYCALL% pour %CALL%",
        {"RST": "599", "SERIAL": "001", "MYCALL": "ON3RT", "CALL": "F4XYZ"},
    )
    assert result == "599 001 de ON3RT pour F4XYZ"


def test_resolve_variables_leaves_unknown_markers_untouched():
    result = resolve_variables("%RST% %UNKNOWN%", {"RST": "599"})
    assert result == "599 %UNKNOWN%"


def test_resolve_variables_handles_repeated_markers():
    result = resolve_variables("%SERIAL%-%SERIAL%", {"SERIAL": "007"})
    assert result == "007-007"


def test_resolve_variables_with_no_markers_returns_text_unchanged():
    assert resolve_variables("Merci, bonne continuation", {}) == "Merci, bonne continuation"


# ------------------------------------------------------------------
# restore_default_templates()
# ------------------------------------------------------------------

def test_restore_default_templates_recreates_a_missing_standard_template(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    service.delete_template(1)  # supprime "CQ" par erreur
    assert [t.label for t in service.templates] == ["Échange"]

    restored = service.restore_default_templates()

    assert [t.label for t in restored] == ["CQ"]
    labels = [t.label for t in service.templates]
    assert "CQ" in labels
    assert "Échange" in labels
    assert len(labels) == 2  # pas de doublon


def test_restore_default_templates_does_not_duplicate_existing_standard_templates(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)

    restored = service.restore_default_templates()

    assert restored == []
    assert [t.label for t in service.templates] == ["CQ", "Échange"]


def test_restore_default_templates_never_overwrites_a_modified_standard_template(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    service.update_template(1, "CQ", "Texte personnalisé FR", "Custom EN text")

    service.restore_default_templates()

    cq = next(t for t in service.templates if t.label == "CQ")
    assert cq.text_fr == "Texte personnalisé FR"  # jamais écrasé
    assert cq.text_en == "Custom EN text"


def test_restore_default_templates_never_deletes_personal_templates(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    service.add_template("Mon modèle perso", "Texte perso", "Personal text")
    service.delete_template(1)  # supprime "CQ"

    service.restore_default_templates()

    labels = [t.label for t in service.templates]
    assert "Mon modèle perso" in labels
    assert "CQ" in labels  # recréé
    assert "Échange" in labels  # jamais touché


def test_restore_default_templates_assigns_a_fresh_id_without_collision(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    service.delete_template(1)  # id 1 ("CQ") libéré

    restored = service.restore_default_templates()

    assert restored[0].id == 3  # jamais de collision avec l'id 2 ("Échange") toujours présent
    assert len({t.id for t in service.templates}) == len(service.templates)  # tous les ids uniques


def test_restore_default_templates_leaves_serial_history_language_and_contest_name_untouched(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    service.contest_name = "CQ WW DX SSB"
    service.toggle_language()  # EN
    service.record_sent("599 001")
    service.delete_template(1)

    service.restore_default_templates()

    assert service.contest_name == "CQ WW DX SSB"
    assert service.language == "EN"
    assert service.serial == 1
    assert len(service.history) == 1


def test_restore_default_templates_when_nothing_is_missing_does_not_call_save(config_path, seed_path, monkeypatch):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)

    save_calls = []
    monkeypatch.setattr(service, "save", lambda: save_calls.append(True))

    service.restore_default_templates()

    assert save_calls == []  # rien de manquant -> aucune écriture inutile


def test_restore_default_templates_persists_the_recreated_template(config_path, seed_path):
    service = ContestMessageService(config_path=config_path, seed_path=seed_path)
    service.delete_template(1)

    service.restore_default_templates()

    reloaded = ContestMessageService(config_path=config_path, seed_path=seed_path)
    assert "CQ" in [t.label for t in reloaded.templates]
