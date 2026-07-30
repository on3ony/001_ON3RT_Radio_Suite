"""
ON3RT Radio Suite
libraries/text/variable_resolver.py

Substitution de marqueurs %CLE% dans un texte — extrait de
apps/contest_assistant/message_service.py (comportement inchangé) pour
devenir un utilitaire partagé, indépendant de tout module applicatif.
Contest Assistant reste un consommateur comme un autre ; le futur
VoiceService (étape 4) en aura besoin lui aussi, pour résoudre le
texte d'un message avant synthèse — sans jamais dépendre de
apps/contest_assistant/, ce qui aurait été une dépendance à l'envers
pour un utilitaire censé servir des consommateurs sans rapport avec le
concours (alertes DX Cluster, annonces système, etc.).
"""

from __future__ import annotations

import re

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
