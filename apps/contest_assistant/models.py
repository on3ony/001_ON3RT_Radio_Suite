"""
ON3RT Radio Suite
Module Contest Assistant
Modèles de données.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class MessageTemplate:

    id: Optional[int] = None
    label: str = ""
    text_fr: str = ""
    text_en: str = ""


@dataclass(slots=True)
class SentMessage:

    timestamp: str = ""
    serial: int = 0
    resolved_text: str = ""
