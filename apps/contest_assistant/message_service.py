"""
ON3RT Radio Suite
apps/contest_assistant/message_service.py

Service du module Contest Assistant : modèles de message, langue
active, nom du concours, numéro progressif et historique des messages
envoyés. Persistance atomique dans data/contest_assistant.json, même
mécanisme que StationService/SettingsService.

Aucune dépendance à l'interface graphique ni à un autre service de la
suite. StationService en particulier n'est pas consommé ici : la
résolution de %MYCALL% combine le texte brut de ce service avec
station_service.callsign au niveau de la fenêtre, qui reste seule
responsable d'assembler les deux. Classe plate, sans signal Qt : un
seul consommateur (ContestAssistantWindow), aucune activité en
arrière-plan — même raisonnement que StationService/SettingsService.

Premier lancement (aucun data/contest_assistant.json existant) : les
modèles de message sont initialisés depuis
data/contest_assistant_seed.json, puis sauvegardés immédiatement.
Cette initialisation ne se reproduit plus jamais une fois le fichier
présent, même s'il ne contient plus aucun modèle (l'utilisateur a pu
tous les supprimer volontairement) — mêmes règles que FrequencyService
avec data/frequency_bank_seed.json.

restore_default_templates() permet de recréer, à la demande, les
modèles standards manquants (ex. supprimés par erreur) sans jamais
dupliquer ceux déjà présents ni écraser leur contenu, et sans jamais
toucher aux modèles personnels de l'utilisateur ni au reste de l'état
(numéro progressif, historique, langue, nom du concours).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from apps.contest_assistant.models import MessageTemplate, SentMessage

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "contest_assistant.json"
DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "contest_assistant_seed.json"

DEFAULT_LANGUAGE = "FR"

_VARIABLE_RE = re.compile(r"%([A-Z]+)%")


def resolve_variables(text: str, values: dict) -> str:
    """
    Remplace chaque marqueur %CLE% présent dans `text` par
    values["CLE"], si connu. Un marqueur sans valeur correspondante
    est laissé tel quel dans le texte — jamais de donnée inventée pour
    le combler.
    """

    def _replace(match: "re.Match[str]") -> str:
        key = match.group(1)
        return str(values[key]) if key in values else match.group(0)

    return _VARIABLE_RE.sub(_replace, text)


class ContestMessageService:
    """
    Expose les modèles de message, la langue, le nom du concours, le
    numéro progressif et l'historique en attributs, et via info() pour
    un instantané complet. Aucune classe métier intermédiaire.
    """

    def __init__(self, config_path=None, seed_path=None):

        self._path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._seed_path = Path(seed_path) if seed_path else DEFAULT_SEED_PATH

        self.contest_name: str = ""
        self.language: str = DEFAULT_LANGUAGE
        self.templates: list[MessageTemplate] = []
        self.serial: int = 0
        self.history: list[SentMessage] = []

        if self._path.exists():
            self.load()
        else:
            self._load_seed_templates()
            self.save()

    # ------------------------------------------------------------------
    # Persistance
    # ------------------------------------------------------------------

    def load(self) -> None:
        """
        Charge data/contest_assistant.json. Si le fichier est absent,
        vide, illisible ou mal formé, l'état par défaut est conservé :
        aucune donnée n'est inventée. Une entrée individuellement mal
        formée dans "templates"/"history" est ignorée plutôt que de
        faire échouer tout le chargement.
        """

        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return

        if not isinstance(data, dict):
            return

        self.contest_name = data.get("contest_name", self.contest_name)
        self.language = data.get("language", self.language)
        self.serial = data.get("serial", self.serial)

        raw_templates = data.get("templates")
        if isinstance(raw_templates, list):
            self.templates = _parse_entries(raw_templates, MessageTemplate)

        raw_history = data.get("history")
        if isinstance(raw_history, list):
            self.history = _parse_entries(raw_history, SentMessage)

    def save(self) -> None:
        """Écrit l'état courant, en écriture atomique (fichier temporaire puis remplacement)."""

        self._path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self._path.with_suffix(".tmp")

        tmp_path.write_text(
            json.dumps(self.info(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        tmp_path.replace(self._path)

    def info(self) -> dict:
        """Retourne un instantané complet de l'état du service."""

        return {
            "contest_name": self.contest_name,
            "language": self.language,
            "templates": [_asdict_ordered(t, ("id", "label", "text_fr", "text_en")) for t in self.templates],
            "serial": self.serial,
            "history": [_asdict_ordered(h, ("timestamp", "serial", "resolved_text")) for h in self.history],
        }

    # ------------------------------------------------------------------
    # Fichier seed (data/contest_assistant_seed.json)
    # ------------------------------------------------------------------

    def _read_seed_entries(self) -> list[dict]:
        """
        Lit le fichier seed et retourne sa liste d'entrées brutes
        (dicts avec label/text_fr/text_en). Liste vide si le fichier
        est absent, illisible ou mal formé — jamais de donnée inventée.
        Les entrées individuellement mal formées (pas un dict) sont
        ignorées.
        """

        if not self._seed_path.exists():
            return []

        try:
            raw = self._seed_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return []

        if not isinstance(data, list):
            return []

        return [item for item in data if isinstance(item, dict)]

    def _load_seed_templates(self) -> None:
        """Premier lancement seulement : initialise les modèles depuis le fichier seed."""

        templates = []
        next_id = 1

        for item in self._read_seed_entries():
            try:
                templates.append(MessageTemplate(id=next_id, **item))
            except TypeError:
                continue
            next_id += 1

        self.templates = templates

    def restore_default_templates(self) -> list[MessageTemplate]:
        """
        Recrée les modèles standards manquants (identifiés par leur
        libellé) depuis le fichier seed. Ne duplique jamais un modèle
        déjà présent, ne modifie jamais son contenu même s'il a été
        édité par l'utilisateur, et ne touche jamais aux modèles
        personnels, au numéro progressif, à l'historique, à la langue
        ni au nom du concours. Retourne la liste des modèles
        effectivement recréés (vide si tous les modèles standards
        étaient déjà présents).
        """

        existing_labels = {t.label for t in self.templates}
        next_id = max((t.id for t in self.templates if t.id is not None), default=0) + 1

        restored = []

        for item in self._read_seed_entries():
            label = item.get("label")

            if label in existing_labels:
                continue

            try:
                template = MessageTemplate(id=next_id, **item)
            except TypeError:
                continue

            self.templates.append(template)
            existing_labels.add(label)
            restored.append(template)
            next_id += 1

        if restored:
            self.save()

        return restored

    # ------------------------------------------------------------------
    # Langue
    # ------------------------------------------------------------------

    def toggle_language(self) -> None:
        self.language = "EN" if self.language == "FR" else "FR"
        self.save()

    def active_text(self, template: MessageTemplate) -> str:
        return template.text_en if self.language == "EN" else template.text_fr

    # ------------------------------------------------------------------
    # Modèles de message (CRUD)
    # ------------------------------------------------------------------

    def add_template(self, label: str, text_fr: str, text_en: str) -> MessageTemplate:
        next_id = max((t.id for t in self.templates if t.id is not None), default=0) + 1
        template = MessageTemplate(id=next_id, label=label, text_fr=text_fr, text_en=text_en)
        self.templates.append(template)
        self.save()
        return template

    def update_template(self, template_id: int, label: str, text_fr: str, text_en: str) -> None:
        for index, existing in enumerate(self.templates):
            if existing.id == template_id:
                self.templates[index] = MessageTemplate(
                    id=template_id, label=label, text_fr=text_fr, text_en=text_en
                )
                self.save()
                return

    def delete_template(self, template_id: int) -> None:
        self.templates = [t for t in self.templates if t.id != template_id]
        self.save()

    # ------------------------------------------------------------------
    # Numéro progressif et historique
    # ------------------------------------------------------------------

    @property
    def next_serial(self) -> int:
        return self.serial + 1

    def record_sent(self, resolved_text: str) -> SentMessage:
        """Incrémente le numéro progressif, ajoute à l'historique, sauvegarde."""

        self.serial = self.next_serial

        entry = SentMessage(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            serial=self.serial,
            resolved_text=resolved_text,
        )
        self.history.append(entry)
        self.save()

        return entry

    # ------------------------------------------------------------------
    # Réinitialisation du concours
    # ------------------------------------------------------------------

    def reset_contest(self) -> None:
        """
        Réinitialise uniquement l'état du concours en cours : nom,
        numéro progressif, historique. Ne touche jamais aux modèles de
        message, à la langue, ni à aucune autre préférence.
        """

        self.contest_name = ""
        self.serial = 0
        self.history = []
        self.save()


def _parse_entries(raw_entries: list, cls) -> list:
    """Construit une liste d'instances de `cls` depuis des dicts, en ignorant les entrées mal formées."""

    parsed = []

    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        try:
            parsed.append(cls(**item))
        except TypeError:
            continue

    return parsed


def _asdict_ordered(instance, fields: tuple) -> dict:
    return {field: getattr(instance, field) for field in fields}
