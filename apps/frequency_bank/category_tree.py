"""
ON3RT Radio Suite
Module Banque de fréquences
Construction et gestion de l'arbre de catégories (QTreeWidget).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from libraries.ui import colors

from apps.frequency_bank.category_node import CategoryNode
from apps.frequency_bank.frequency_service import FrequencyService
from apps.frequency_bank.models import Frequency


def build_category_tree(nodes: list[CategoryNode], selected_id: str | None = None) -> QTreeWidget:
    """
    Construit un QTreeWidget à partir d'une liste de CategoryNode,
    restaure l'état développé/réduit et la sélection de chaque nœud.
    Ne connaît rien du contenu réel des catégories.
    """

    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    tree.setStyleSheet(
        f"""
        QTreeWidget {{
            background-color: {colors.BG_PANEL};
            border: 1px solid {colors.BORDER};
            selection-background-color: {colors.ACCENT};
            selection-color: #ffffff;
        }}
        QTreeWidget::item {{
            padding: 4px;
        }}
        """
    )

    selected_item = None

    def add_item(parent, node: CategoryNode) -> None:
        nonlocal selected_item
        item = QTreeWidgetItem(parent, [node.label])
        item.setData(0, Qt.ItemDataRole.UserRole, node.id)
        item.setExpanded(node.expanded)

        if node.id == selected_id:
            selected_item = item

        for child in node.children:
            add_item(item, child)

    for node in nodes:
        add_item(tree, node)

    if selected_item is not None:
        tree.setCurrentItem(selected_item)
    elif tree.topLevelItemCount() > 0:
        tree.setCurrentItem(tree.topLevelItem(0))

    return tree


def frequencies_for_category(service: FrequencyService, node: CategoryNode | None) -> list[Frequency]:
    """
    Retourne les fréquences correspondant à un CategoryNode, en
    s'appuyant uniquement sur les méthodes déjà exposées par
    FrequencyService (aucune modification du service). Ne connaît rien
    du contenu réel des catégories : le champ à filtrer et la valeur
    recherchée viennent entièrement du nœud (filter_field/filter_value).
    """

    if node is None or node.filter_field is None:
        return service.get_all()

    if node.filter_field == "group":
        # Regroupement de sous-catégories : l'agrégation réelle (union
        # des filtres des enfants) n'est pas encore implémentée. En
        # attendant, afficher toutes les fréquences plutôt que de
        # laisser penser qu'aucune donnée n'existe.
        return service.get_all()

    if node.filter_field == "mode":
        return service.by_mode(node.filter_value)

    if node.filter_field == "favorite":
        return service.favorites()

    return service.get_all()
