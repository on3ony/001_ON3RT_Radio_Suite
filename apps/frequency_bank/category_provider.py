"""
ON3RT Radio Suite
Module Banque de fréquences
Source des données de catégories.
"""

from apps.frequency_bank.category_node import CategoryNode


class CategoryProvider:
    """
    Interface commune à toute source de données de catégories. Une
    future JSONCategoryProvider ou SQLiteCategoryProvider implémentera
    load()/save() sans qu'aucune ligne de CategoryStore ni de
    build_category_tree n'ait à changer.
    """

    def load(self) -> list[CategoryNode]:
        raise NotImplementedError

    def save(self, roots: list[CategoryNode]) -> None:
        raise NotImplementedError


class DefaultCategoryProvider(CategoryProvider):
    """
    Fournit le jeu de catégories illustratif tant qu'aucune source
    persistante n'est branchée. Purement en mémoire : save() ne
    persiste rien, la vraie taxonomie et sa persistance sont prévues
    pour une étape fonctionnelle ultérieure.
    """

    def load(self) -> list[CategoryNode]:
        return [
            CategoryNode("Toutes les fréquences", is_system=True),
            CategoryNode("HF", is_system=True, filter_field="group", children=[
                CategoryNode(label, is_system=True, filter_field="mode", filter_value=mode)
                for label, mode in (
                    ("SSB", "SSB"), ("FT8", "FT8"), ("FT4", "FT4"), ("CW", "CW"),
                    ("RTTY", "RTTY"), ("SSTV", "SSTV"), ("JS8Call", "JS8"),
                    ("VarAC", "VarAC"), ("Contest", "Contest"),
                )
            ]),
            CategoryNode("VHF", is_system=True, filter_field="group", children=[
                CategoryNode("FM", is_system=True, filter_field="mode", filter_value="FM"),
                CategoryNode("C4FM", is_system=True, filter_field="mode", filter_value="C4FM"),
            ]),
            CategoryNode("UHF", is_system=True, filter_field="group", children=[
                CategoryNode("FM", is_system=True, filter_field="mode", filter_value="FM"),
                CategoryNode("C4FM", is_system=True, filter_field="mode", filter_value="C4FM"),
            ]),
            CategoryNode("Personnel", is_system=True, filter_field="group"),
            CategoryNode("Favoris", is_system=True, filter_field="favorite"),
        ]

    def save(self, roots: list[CategoryNode]) -> None:
        pass
