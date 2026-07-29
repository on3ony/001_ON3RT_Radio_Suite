"""
ON3RT Radio Suite
Module Banque de fréquences
Donnée d'un profil de fréquences.

Un profil représente, à terme, une banque de fréquences indépendante
(HF, Portable, Contest, DX, Expériences...), avec ses propres
catégories et fréquences. Cette étape ne définit que la donnée pure —
aucune connexion à FrequencyService, CategoryStore ou à l'interface :
le comportement actuel de la Banque de fréquences n'est pas modifié.
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class FrequencyProfile:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    is_default: bool = False

    # Distinct de is_default : is_system protège un profil contre la
    # suppression (mirroir de CategoryNode.is_system). "Par défaut"
    # sera le seul profil système tant qu'aucune gestion multi-profils
    # réelle n'est branchée ; les profils créés par l'utilisateur
    # restent entièrement personnalisables (is_system=False).
    is_system: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_default": self.is_default,
            "is_system": self.is_system,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FrequencyProfile":
        return cls(
            id=data.get("id") or uuid.uuid4().hex[:8],
            name=data.get("name", ""),
            description=data.get("description", ""),
            is_default=data.get("is_default", False),
            is_system=data.get("is_system", False),
        )
