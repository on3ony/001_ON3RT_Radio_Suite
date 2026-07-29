"""
ON3RT Radio Suite
Module Banque de fréquences
Donnée d'un nœud de catégorie/sous-catégorie.
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class CategoryNode:
    label: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    children: list["CategoryNode"] = field(default_factory=list)
    is_system: bool = False
    icon: str | None = None
    color: str | None = None
    expanded: bool = True

    # Descripteur de filtrage, consulté uniquement par
    # frequencies_for_category() (category_tree.py) — jamais par
    # l'interface directement :
    #   None       -> aucun filtre, toutes les fréquences (racine)
    #   "group"    -> catégorie d'organisation regroupant des
    #                 sous-catégories (HF, VHF, UHF, Personnel...) :
    #                 affiche toutes les fréquences tant que
    #                 l'agrégation réelle des sous-catégories n'est pas
    #                 implémentée — jamais 0 résultat, pour ne pas
    #                 laisser penser que des données manquent.
    #   "mode"     -> filtre par Frequency.mode == filter_value
    #   "favorite" -> filtre par Frequency.favorite == True
    filter_field: str | None = None
    filter_value: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "is_system": self.is_system,
            "icon": self.icon,
            "color": self.color,
            "expanded": self.expanded,
            "filter_field": self.filter_field,
            "filter_value": self.filter_value,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CategoryNode":
        return cls(
            id=data.get("id") or uuid.uuid4().hex[:8],
            label=data.get("label", ""),
            is_system=data.get("is_system", False),
            icon=data.get("icon"),
            color=data.get("color"),
            expanded=data.get("expanded", True),
            filter_field=data.get("filter_field"),
            filter_value=data.get("filter_value"),
            children=[cls.from_dict(child) for child in data.get("children", [])],
        )
