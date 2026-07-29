"""
ON3RT Radio Suite
Module Banque de fréquences
Fenêtre du module.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
)

from libraries.ui import colors
from libraries.ui.base_window import BaseWindow

from apps.frequency_bank.category_node import CategoryNode
from apps.frequency_bank.category_provider import DefaultCategoryProvider
from apps.frequency_bank.category_store import CategoryStore
from apps.frequency_bank.category_tree import build_category_tree, frequencies_for_category
from apps.frequency_bank.frequency_dialog import FrequencyDialog
from apps.frequency_bank.frequency_service import FrequencyService
from apps.frequency_bank.models import Frequency
from apps.frequency_bank.table_model import FrequencyTableModel


# ==========================================================================
# Panneau de catégories — architecture pérenne, préparée par avance
#
# Réparties en plusieurs fichiers selon leur responsabilité :
#
#   - category_node.py       : CategoryNode, la donnée pure (un nœud
#                               catégorie ou sous-catégorie, profondeur
#                               illimitée), indépendante de Qt.
#                               Sérialisable (to_dict/from_dict), prête
#                               pour un futur import/export.
#   - category_provider.py   : CategoryProvider / DefaultCategoryProvider
#                               — la source des données. Aujourd'hui une
#                               liste en mémoire ; demain un chargement
#                               JSON, base de données, ou gestion
#                               utilisateur. C'est le seul point qu'une
#                               nouvelle source aura à remplacer — ni
#                               CategoryStore, ni l'interface, n'auront
#                               besoin d'être modifiés.
#   - category_store.py      : CategoryStore, la logique de gestion —
#                               ajout, renommage, déplacement, suppression
#                               (avec protection des catégories système),
#                               sélection courante.
#   - category_tree.py       : build_category_tree()/
#                               frequencies_for_category(), l'interface —
#                               transforme une liste de CategoryNode en
#                               QTreeWidget et calcule le filtrage des
#                               fréquences, sans aucune connaissance du
#                               contenu des catégories elles-mêmes.
# ==========================================================================


class FrequencyBankWindow(BaseWindow):

    def __init__(self, frequency_service: FrequencyService = None):
        super().__init__(
            title="Banque de fréquences",
            subtitle="Fréquences de référence, plan de bandes, favoris",
        )

        # FrequencyService est un service partagé de la Suite (injecté
        # depuis core/application.py). Si aucun n'est fourni (lancement
        # autonome), la fenêtre crée le sien et en reste responsable —
        # elle seule le fermera alors à la fermeture (voir closeEvent).
        self._owns_service = frequency_service is None
        self.service = frequency_service or FrequencyService()

        self.model = FrequencyTableModel()

        # Gestion des catégories : purement en mémoire pour l'instant
        # (DefaultCategoryProvider), sans effet sur le tableau. Voir le
        # bloc CategoryNode/CategoryProvider/CategoryStore en tête de
        # fichier.
        self.category_store = CategoryStore(DefaultCategoryProvider())

        self._build_content()

        self.add_button.clicked.connect(self.new_frequency)
        self.edit_button.clicked.connect(self.edit_frequency)
        self.delete_button.clicked.connect(self.delete_frequency)
        self.search_button.clicked.connect(self.search_frequency)
        self.search_edit.returnPressed.connect(self.search_frequency)
        self.refresh_button.clicked.connect(self.load_frequencies)
        self.table.doubleClicked.connect(self.edit_frequency)
        self._wire_category_tree(self.category_tree)

        self.load_frequencies()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_content(self):
        # ----- Recherche : ligne dédiée, volontairement plus visible -----
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Rechercher une fréquence (nom, description, bande, mode...)")
        self.search_edit.setStyleSheet(
            "QLineEdit { min-height: 38px; padding: 8px 12px; font-size: 11pt; }"
        )

        self.search_button = QPushButton("Rechercher")

        search_row.addWidget(self.search_edit, 1)
        search_row.addWidget(self.search_button)

        # ----- Actions : ligne séparée, prête à accueillir de futurs
        # boutons (catégories, etc.) sans réorganisation -----
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.add_button = QPushButton("Ajouter")
        self.edit_button = QPushButton("Modifier")
        self.delete_button = QPushButton("Supprimer")
        self.refresh_button = QPushButton("Actualiser")

        actions_row.addWidget(self.add_button)
        actions_row.addWidget(self.edit_button)
        actions_row.addWidget(self.delete_button)
        actions_row.addWidget(self.refresh_button)
        actions_row.addStretch()

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)

        self.table.setStyleSheet(
            f"""
            QTableView {{
                background-color: {colors.BG_PANEL};
                alternate-background-color: {colors.BG_PANEL_2};
                gridline-color: {colors.BORDER};
                border: 1px solid {colors.BORDER};
                selection-background-color: {colors.ACCENT};
                selection-color: #ffffff;
            }}
            QHeaderView::section {{
                background-color: {colors.BG_PANEL_2};
                color: {colors.TEXT_SECONDARY};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {colors.BORDER};
                font-weight: 600;
            }}
            """
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Description absorbe l'espace restant

        self.category_tree = build_category_tree(self.category_store.roots, self.category_store.selected_id)

        # Le panneau de catégories occupe l'emplacement réservé à gauche du
        # tableau depuis l'étape précédente. La sélection y est
        # fonctionnelle (voir _on_category_selected) mais ne filtre pas
        # encore les données du tableau — le contenu affiché ici est un
        # exemple provisoire, sans lien avec les champs category/mode
        # réels du modèle Frequency. La vraie taxonomie, sa persistance et
        # son caractère personnalisable font l'objet d'une étape dédiée.
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.category_tree)
        self.splitter.addWidget(self.table)
        self.splitter.setSizes([220, 900])

        self.content_layout.addLayout(search_row)
        self.content_layout.addLayout(actions_row)
        self.content_layout.addWidget(self.splitter)

    def _on_category_selected(self, item: QTreeWidgetItem, column: int) -> None:
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.category_store.select(node_id)
        self.load_frequencies()

    def _on_category_expanded(self, item: QTreeWidgetItem) -> None:
        node = self.category_store.find(item.data(0, Qt.ItemDataRole.UserRole))
        if node is not None:
            node.expanded = True

    def _on_category_collapsed(self, item: QTreeWidgetItem) -> None:
        node = self.category_store.find(item.data(0, Qt.ItemDataRole.UserRole))
        if node is not None:
            node.expanded = False

    # ------------------------------------------------------------------
    # Gestion des catégories (menu contextuel)
    # ------------------------------------------------------------------

    def _wire_category_tree(self, tree: QTreeWidget) -> None:
        tree.itemClicked.connect(self._on_category_selected)
        tree.itemExpanded.connect(self._on_category_expanded)
        tree.itemCollapsed.connect(self._on_category_collapsed)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._show_category_menu)

    def _refresh_category_tree(self) -> None:
        old_tree = self.category_tree
        self.category_tree = build_category_tree(self.category_store.roots, self.category_store.selected_id)
        self._wire_category_tree(self.category_tree)

        index = self.splitter.indexOf(old_tree)
        self.splitter.replaceWidget(index, self.category_tree)
        old_tree.deleteLater()

    def _show_category_menu(self, pos) -> None:
        item = self.category_tree.itemAt(pos)
        node = self.category_store.find(item.data(0, Qt.ItemDataRole.UserRole)) if item is not None else None

        menu = QMenu(self)
        add_root_action = menu.addAction("Ajouter une catégorie")

        add_child_action = rename_action = delete_action = move_action = None

        if node is not None:
            add_child_action = menu.addAction("Ajouter une sous-catégorie")
            menu.addSeparator()
            rename_action = menu.addAction("Renommer")
            delete_action = menu.addAction("Supprimer")
            move_action = menu.addAction("Déplacer vers...")

            if node.is_system:
                rename_action.setEnabled(False)
                delete_action.setEnabled(False)
                move_action.setEnabled(False)

        chosen = menu.exec(self.category_tree.viewport().mapToGlobal(pos))

        if chosen is None:
            return
        if chosen is add_root_action:
            self._add_category(parent_id=None)
        elif chosen is add_child_action:
            self._add_category(parent_id=node.id)
        elif chosen is rename_action:
            self._rename_category(node)
        elif chosen is delete_action:
            self._delete_category(node)
        elif chosen is move_action:
            self._move_category(node)

    def _add_category(self, parent_id: str | None) -> None:
        label, ok = QInputDialog.getText(self, "Nouvelle catégorie", "Nom de la catégorie :")
        label = label.strip()

        if not ok or not label:
            return

        new_node = self.category_store.add(label, parent_id=parent_id)
        self.category_store.select(new_node.id)
        self._refresh_category_tree()

    def _rename_category(self, node: CategoryNode) -> None:
        label, ok = QInputDialog.getText(self, "Renommer la catégorie", "Nouveau nom :", text=node.label)
        label = label.strip()

        if not ok or not label:
            return

        try:
            self.category_store.rename(node.id, label)
        except ValueError as exc:
            QMessageBox.warning(self, "Renommage impossible", str(exc))
            return

        self._refresh_category_tree()

    def _delete_category(self, node: CategoryNode) -> None:
        answer = QMessageBox.question(
            self,
            "Supprimer la catégorie",
            f"Supprimer la catégorie « {node.label} » et ses éventuelles sous-catégories ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.category_store.delete(node.id)
        except ValueError as exc:
            QMessageBox.warning(self, "Suppression impossible", str(exc))
            return

        self._refresh_category_tree()
        self.load_frequencies()

    def _category_path(self, node_id: str) -> str:
        def find_path(nodes, target_id, trail):
            for n in nodes:
                new_trail = trail + [n.label]
                if n.id == target_id:
                    return new_trail
                found = find_path(n.children, target_id, new_trail)
                if found is not None:
                    return found
            return None

        path = find_path(self.category_store.roots, node_id, [])
        return " > ".join(path) if path else "?"

    def _move_category(self, node: CategoryNode) -> None:
        # Le chemin complet (pas le seul libellé) évite toute ambiguïté
        # entre deux catégories de même nom situées à des endroits
        # différents de l'arbre (ex. « FM » sous VHF et sous UHF).
        candidates = [("(Racine)", None)] + [
            (self._category_path(n.id), n.id)
            for n in self.category_store.all_nodes()
            if self.category_store.can_move(node.id, n.id)
        ]
        labels = [label for label, _ in candidates]

        choice, ok = QInputDialog.getItem(
            self, "Déplacer la catégorie", "Nouvelle catégorie parente :", labels, editable=False,
        )

        if not ok:
            return

        new_parent_id = dict(candidates)[choice]

        try:
            self.category_store.move(node.id, new_parent_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Déplacement impossible", str(exc))
            return

        self._refresh_category_tree()

    # ------------------------------------------------------------------
    # Chargement / recherche
    # ------------------------------------------------------------------

    def load_frequencies(self):
        # Ré-applique la catégorie actuellement sélectionnée (le cas
        # échéant) : utilisée au démarrage, par "Actualiser", et après
        # chaque ajout/modification/suppression, afin que le filtre
        # actif reste appliqué plutôt que d'être silencieusement
        # réinitialisé à "toutes les fréquences".
        node = (
            self.category_store.find(self.category_store.selected_id)
            if self.category_store.selected_id
            else None
        )
        frequencies = frequencies_for_category(self.service, node)
        self.model.set_frequencies(frequencies)

        if node is not None and node.filter_field == "group":
            self.statusBar().showMessage(
                f"{node.label} : regroupement de sous-catégories (affichage complet, filtrage à venir)", 3000
            )
        elif node is not None:
            self.statusBar().showMessage(f"{node.label} : {len(frequencies)} fréquence(s)", 3000)
        else:
            self.statusBar().showMessage(f"{len(frequencies)} fréquence(s)")

    def search_frequency(self):
        text = self.search_edit.text().strip()

        if not text:
            self.load_frequencies()
            return

        results = self.service.search(text)
        self.model.set_frequencies(results)
        self.statusBar().showMessage(f"{len(results)} résultat(s)")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def new_frequency(self):
        dialog = FrequencyDialog(parent=self)

        if dialog.exec():
            frequency = self._build_frequency(dialog.get_data())
            self.service.add(frequency)
            self.load_frequencies()

    def edit_frequency(self):
        frequency = self._selected_frequency()

        if frequency is None:
            return

        dialog = FrequencyDialog(frequency=frequency, parent=self)

        if dialog.exec():
            updated = self._build_frequency(dialog.get_data(), existing=frequency)
            self.service.update(updated)
            self.load_frequencies()

    def delete_frequency(self):
        frequency = self._selected_frequency()

        if frequency is None:
            return

        answer = QMessageBox.question(
            self,
            "Supprimer",
            f"Supprimer la fréquence {frequency.name or frequency.frequency} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.service.delete(frequency.id)
        self.load_frequencies()

    def _selected_frequency(self):
        index = self.table.currentIndex()

        if not index.isValid():
            return None

        return self.model.frequency(index.row())

    def _build_frequency(self, data: dict, existing: Frequency = None) -> Frequency:
        frequency = Frequency()

        if existing is not None:
            frequency.id = existing.id
            frequency.start_frequency = existing.start_frequency
            frequency.end_frequency = existing.end_frequency
        else:
            frequency.start_frequency = data["frequency"]
            frequency.end_frequency = data["frequency"]

        frequency.frequency = data["frequency"]
        frequency.band = data["band"]
        frequency.mode = data["mode"]
        frequency.category = data["category"]
        frequency.step = data["step"]
        frequency.modulation = data["modulation"]
        frequency.service = data["service"]
        frequency.name = data["name"]
        frequency.description = data["description"]
        frequency.country = data["country"]
        frequency.region = data["region"]
        frequency.source = data["source"]
        frequency.favorite = data["favorite"]
        frequency.priority = data["priority"]
        frequency.active = data["active"]
        frequency.color = data["color"]

        return frequency

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self._owns_service:
            self.service.close()
        super().closeEvent(event)
