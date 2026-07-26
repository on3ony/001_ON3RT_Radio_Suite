"""
apps/contest/contest_preferences.py
ON3RT Radio Suite - Contest Logbook

Mémorise les derniers choix de l'utilisateur pour le dialogue
"Propriétés du concours" dans les préférences de l'application,
indépendamment du fichier de base de données du concours actif, afin
qu'ils soient réutilisés au prochain "Nouveau concours".
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

FIELDS = ("contest_name", "callsign", "operator", "category", "power", "club")


def _default_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "data" / "config" / "contest_preferences.ini"


def _settings(path: str | Path | None = None) -> QSettings:
    ini_path = Path(path) if path else _default_path()
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    return QSettings(str(ini_path), QSettings.Format.IniFormat)


def load_last_contest_properties(path: str | Path | None = None) -> dict:
    settings = _settings(path)
    settings.beginGroup("contest_properties")
    try:
        return {key: settings.value(key, "") for key in FIELDS}
    finally:
        settings.endGroup()


def save_last_contest_properties(values: dict, path: str | Path | None = None) -> None:
    settings = _settings(path)
    settings.beginGroup("contest_properties")
    try:
        for key in FIELDS:
            if key in values:
                settings.setValue(key, values[key])
    finally:
        settings.endGroup()
    settings.sync()
