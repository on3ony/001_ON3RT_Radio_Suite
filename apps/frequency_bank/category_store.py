"""
ON3RT Radio Suite
Module Banque de fréquences
Gestion en mémoire de l'arbre de catégories.
"""

from apps.frequency_bank.category_node import CategoryNode
from apps.frequency_bank.category_provider import CategoryProvider


class CategoryStore:
    """
    Gestion en mémoire de l'arbre de catégories. Reçoit sa source de
    données par injection (CategoryProvider) : la provenance réelle des
    données n'a aucun impact sur cette classe.
    """

    def __init__(self, provider: CategoryProvider):
        self._provider = provider
        self.roots: list[CategoryNode] = provider.load()
        self.selected_id: str | None = None

    def save(self) -> None:
        self._provider.save(self.roots)

    # ---- Parcours ----

    def all_nodes(self):
        def walk(nodes):
            for node in nodes:
                yield node
                yield from walk(node.children)

        yield from walk(self.roots)

    def find(self, node_id: str) -> CategoryNode | None:
        return next((n for n in self.all_nodes() if n.id == node_id), None)

    # ---- Gestion ----

    def add(self, label: str, parent_id: str | None = None) -> CategoryNode:
        node = CategoryNode(label, is_system=False)

        if parent_id is None:
            self.roots.append(node)
        else:
            parent = self.find(parent_id)
            if parent is None:
                raise ValueError(f"Catégorie parente introuvable : {parent_id}")
            parent.children.append(node)

        return node

    def rename(self, node_id: str, new_label: str) -> None:
        node = self.find(node_id)
        if node is None:
            raise ValueError(f"Catégorie introuvable : {node_id}")
        if node.is_system:
            raise ValueError("Une catégorie système ne peut pas être renommée")

        node.label = new_label

    def delete(self, node_id: str) -> None:
        node = self.find(node_id)
        if node is None:
            return
        if node.is_system:
            raise ValueError("Une catégorie système ne peut pas être supprimée")

        # La sélection courante peut pointer sur une sous-catégorie du
        # nœud supprimé (suppression en cascade) : il faut réinitialiser
        # selected_id dans ce cas aussi, pas seulement s'il pointe
        # exactement sur le nœud supprimé lui-même.
        if self.selected_id is not None and (
            self.selected_id == node_id or self._is_descendant(node, self.selected_id)
        ):
            self.selected_id = None

        self._remove_from_parent(self.roots, node_id)

    def move(self, node_id: str, new_parent_id: str | None) -> None:
        node = self.find(node_id)
        if node is None:
            raise ValueError(f"Catégorie introuvable : {node_id}")

        if new_parent_id is not None:
            if new_parent_id == node_id:
                raise ValueError("Une catégorie ne peut pas devenir sa propre catégorie parente")
            if self._is_descendant(node, new_parent_id):
                raise ValueError("Impossible de déplacer une catégorie dans l'une de ses propres sous-catégories")

        self._remove_from_parent(self.roots, node_id)

        if new_parent_id is None:
            self.roots.append(node)
        else:
            parent = self.find(new_parent_id)
            if parent is None:
                raise ValueError(f"Catégorie parente introuvable : {new_parent_id}")
            parent.children.append(node)

    def _remove_from_parent(self, siblings: list[CategoryNode], node_id: str) -> bool:
        for index, candidate in enumerate(siblings):
            if candidate.id == node_id:
                del siblings[index]
                return True
            if self._remove_from_parent(candidate.children, node_id):
                return True
        return False

    def _is_descendant(self, node: CategoryNode, candidate_id: str) -> bool:
        for child in node.children:
            if child.id == candidate_id or self._is_descendant(child, candidate_id):
                return True
        return False

    def can_move(self, node_id: str, new_parent_id: str | None) -> bool:
        """Indique si move(node_id, new_parent_id) réussirait, sans l'exécuter."""

        if new_parent_id is None:
            return True
        if new_parent_id == node_id:
            return False

        node = self.find(node_id)
        if node is None:
            return False

        return not self._is_descendant(node, new_parent_id)

    # ---- Sélection ----

    def select(self, node_id: str | None) -> None:
        self.selected_id = node_id

    # ---- Import / export ----

    def to_dict(self) -> dict:
        return {
            "roots": [node.to_dict() for node in self.roots],
            "selected_id": self.selected_id,
        }

    def load_dict(self, data: dict) -> None:
        self.roots = [CategoryNode.from_dict(d) for d in data.get("roots", [])]
        self.selected_id = data.get("selected_id")
