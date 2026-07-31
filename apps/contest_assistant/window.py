"""
ON3RT Radio Suite
apps/contest_assistant/window.py

Fenêtre du module Contest Assistant.

ContestMessageService et StationService sont reçus en injection
(jamais créés ici). ContestMessageService n'expose aucun signal Qt
(classe plate, un seul consommateur) : cette fenêtre appelle ses
méthodes directement puis rafraîchit l'affichage elle-même, sans
abonnement — donc aucun signal à déconnecter à la fermeture,
contrairement à Scanner/DX Cluster/BandMap qui suivent un service
partagé actif en arrière-plan.

transmission_service et voice_service (étape 4e-2 de l'architecture
Voix) sont reçus en injection exactement de la même façon, jamais
instanciés ici : règle stricte de la Suite, une seule instance
partagée de VoiceService/AudioOutputService/PTTGuard/TransmissionService
existe dans toute l'application, créée uniquement par
core/application.py (voir sa docstring) — aucune fenêtre n'a le droit
d'en créer une seconde.

"Annoncer" (étape 4e-3) : premier vrai consommateur de la chaîne Voix,
une action TOTALEMENT INDÉPENDANTE de "Envoyer" (voir sa docstring,
section Envoi, plus bas) — aucun code partagé entre les deux, aucun
effet sur le numéro progressif ni sur l'historique. "Annoncer" ne fait
que résoudre le même texte et le prononcer réellement : voice_service.
synthesize(resolved, cacheable=False, owner=...) -> sur
synthesis_finished -> transmission_service.transmit(output_path,
owner=...) -> sur transmission_finished/transmission_error, réactive
le bouton. cacheable=False délibérément : un échange de concours avec
%RST%/%SERIAL% change presque à chaque appel, un cache serait inutile
(voir la docstring de VoiceService.synthesize()). Entièrement
asynchrone (signaux Qt) à chaque étape : l'interface ne se bloque
jamais, ni pendant la synthèse ni pendant la transmission.

Actif seulement si voice_service ET transmission_service ont été
fournis (sinon désactivé en permanence — dégradation propre plutôt
qu'un clic qui ne ferait rien ou lèverait une exception), et désactivé
le temps qu'une annonce déjà lancée se termine (succès ou erreur) :
évite un second clic pendant qu'une synthèse/transmission est en cours,
en plus du rejet natif de TransmissionService.transmit() si une
transmission est déjà active (voir sa docstring).

request_id de VoiceService.synthesize() vérifié avant de réagir à
synthesis_finished/synthesis_error : VoiceService est une ressource
partagée de toute la Suite (voir core/application.py), une future
fenêtre pourrait un jour l'utiliser en parallèle — cette fenêtre ne
doit jamais réagir à la synthèse de quelqu'un d'autre. Signaux de
VoiceService/TransmissionService connectés UNE SEULE FOIS à la
construction (jamais connectés/déconnectés par clic), comme
TransmissionService le fait déjà pour les signaux d'AudioOutputService.

Aucune vérification symétrique côté transmission_finished/
transmission_error : TransmissionService ne permet qu'une transmission
à la fois (is_transmitting) et rien d'autre ne le consomme encore
aujourd'hui — si un second consommateur apparaît plus tard, ce point
devra être revisité (filtrage par owner, comme request_id ci-dessus).

Toute erreur (synthèse, transmission — TransmissionService relaie déjà
les erreurs de lecture d'AudioOutputService) est affichée dans la barre
d'état, jamais une exception qui remonterait : le clic sur "Annoncer"
est lui-même protégé par un bloc try/except large, en dernier recours,
pour ne jamais planter la fenêtre quelle que soit la cause.

Fermeture de la fenêtre pendant une annonce en cours : volontairement
non gérée ici — transmission_service est un service partagé de toute
l'application (pas la propriété de cette fenêtre), la transmission se
termine naturellement même si cette fenêtre se ferme entre-temps, avec
la minuterie de sécurité de PTTGuard comme filet de secours ultime.

%MYCALL% est résolu ici, pas dans le service : ContestMessageService
ne dépend d'aucun autre service (voir sa conception) — c'est cette
fenêtre qui assemble le texte du modèle avec station_service.callsign
au moment de l'envoi.

"Envoyer" est une action purement logique en V1 : résout les variables,
avance le numéro progressif, ajoute à l'historique — aucune
transmission réelle (pas de CAT, pas d'audio, pas de CW). Chaque envoi
passe par une seule méthode (_on_send_clicked -> _send_template), pour
qu'une future version puisse y brancher un envoi réel (CW/audio) ou un
raccourci clavier sans restructurer la fenêtre.

Le champ "Nom du concours" réutilise CONTEST_NAMES du module Contest
(apps/contest/contest_properties_dialog.py) — même liste, même
comportement de liste déroulante éditable (avec "Autre..." qui vide le
champ pour une saisie libre) — plutôt que de dupliquer cette liste ici.
C'est la seule dépendance de ce fichier vers apps/contest/ : une
simple constante de données, jamais son service ni sa fenêtre.

Messages et Historique sont affichés en QTableView (MessageTemplateTableModel
/SentMessageTableModel, apps/contest_assistant/table_model.py) — même
présentation qu'apps/dxcluster/window.py (en-têtes de colonnes, hauteur
de ligne fixe via setDefaultSectionSize, même feuille de style).

--- Historique des deux causes réelles déjà rencontrées et de la
    conception actuelle (mesuré, pas deviné) ---

1) Le tableau Messages ne doit jamais partager de conteneur avec sa
   rangée de boutons (measure initiale : les deux se disputaient le
   même espace sans qu'aucun ne soit prioritaire). Corrigé en ajoutant
   le tableau directement à content_layout, avec un facteur
   d'étirement explicite — comme DX Cluster ajoute directement le sien.

2) Une fois le vrai thème de la suite chargé (assets/themes/on3rt_dark.qss,
   chargé par launcher.py sur toute l'application, jamais par un test
   isolé sans thème), les widgets classiques (QGroupBox, QPushButton,
   QLineEdit, QComboBox) grossissent nettement. Avec 4 sections
   QGroupBox distinctes (Concours, Correspondant, Messages, Historique)
   en plus des tableaux, l'espace total requis dépassait ce qu'une
   fenêtre de taille fixe, même généreuse, pouvait fournir sur un écran
   réel : mesuré sur l'écran de développement (1536x864, mise à
   l'échelle Windows 125%, soit 816px de hauteur réellement utilisable
   après barre des tâches), une fenêtre demandant plus de hauteur que
   l'écran ne peut tout simplement pas l'obtenir — Windows la contraint
   de force, quelle que soit la valeur passée à resize()/setMinimumSize().
   Une taille de fenêtre fixe, choisie sans connaître l'écran réel de
   l'utilisateur, ne peut donc jamais être fiable.

   Conséquence sur la conception actuelle, les deux à la fois :
   - Concours et Correspondant se passent de QGroupBox (_build_contest_row/
     _build_contact_row, voir point 4) : le chrome d'une QGroupBox
     (marge de titre, bordure, padding) coûtait à lui seul plusieurs
     dizaines de pixels par section, pour un contenu qui tient
     confortablement sur une ligne.
   - La fenêtre s'ouvre agrandie (showMaximized(), positionné avant
     l'affichage via setWindowState()) plutôt qu'à une taille fixe
     devinée : elle utilise ainsi toujours l'intégralité de l'écran
     réel de l'utilisateur, quel qu'il soit, au lieu d'une valeur qui
     ne peut être vérifiée que sur l'écran du développeur.

3) Messages et Historique n'ont pas la même fréquence d'usage réelle en
   concours : Messages est consulté en continu, Historique seulement
   occasionnellement. Plutôt que de les faire cohabiter verticalement
   (ce qui limite toujours la hauteur du tableau le plus utilisé au
   profit de l'autre, quel que soit le partage choisi), ils sont
   répartis dans un QTabWidget à deux onglets — même pattern que
   apps/settings/window.py (seul autre précédent d'onglets dans la
   Suite ; aucune section repliable ni fenêtre secondaire de
   consultation n'existe ailleurs). L'onglet "Messages" est ouvert par
   défaut et son tableau reçoit alors toute la hauteur du contenu, sans
   la partager avec Historique. Concours + Correspondant restent hors
   des onglets, visibles en permanence : ces champs servent à résoudre
   les variables des messages quel que soit l'onglet actif.

4) La zone hors-onglets (Concours + Correspondant) tenait sur une seule
   rangée très chargée (7 widgets), avec Dernier n°/Prochain n° rejetés
   loin à droite par les deux QLineEdit à politique Expanding qui
   consommaient tout l'espace restant. Corrigée en deux rangées plus
   courtes : _build_contest_row() (nom du concours, langue,
   réinitialisation) puis _build_contact_row() (indicatif, RST, puis
   immédiatement les deux numéros — regroupés dans le même bloc plutôt
   que poussés en bout de ligne). Les champs texte de la seconde rangée
   ont une largeur maximale fixe plutôt qu'un facteur d'étirement, et un
   addStretch() ferme la rangée : le regroupement Correspondant+numéros
   reste compact à gauche au lieu de s'écarteler sur toute la largeur
   de la fenêtre. Les boutons de cette fenêtre (rangées du haut et
   rangée d'actions de l'onglet Messages) reçoivent aussi
   _COMPACT_BUTTON_STYLESHEET : le thème de la suite fixe min-height:
   42px sur QPushButton pour un usage général, ce qui laissait moins de
   hauteur au tableau qu'un bouton plus compact ne l'exige réellement.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from libraries.text.variable_resolver import resolve_variables
from libraries.ui import colors
from libraries.ui.base_window import BaseWindow

from apps.contest.contest_properties_dialog import CONTEST_NAMES
from apps.contest_assistant.message_service import ContestMessageService
from apps.contest_assistant.table_model import MessageTemplateTableModel, SentMessageTableModel

# Même présentation que DX Cluster (apps/dxcluster/window.py) : hauteur
# de ligne fixe et feuille de style identique, pour une cohérence
# visuelle immédiate entre les deux modules.
_ROW_HEIGHT = 34

# Mesuré (voir docstring du module) pour que les 9 modèles par défaut
# restent visibles sans défilement : 9 lignes x 34px + en-tête + bordures.
_MESSAGES_TABLE_MIN_HEIGHT = 345

# Simple plancher de confort : Historique est seul dans son propre
# onglet (voir docstring, point 3), il ne se dispute donc plus l'espace
# avec Messages et reçoit toute la hauteur de son onglet.
_HISTORY_TABLE_MIN_HEIGHT = 140

# Le thème de la suite (assets/themes/on3rt_dark.qss) fixe min-height:
# 42px sur QPushButton pour un usage général — confortable, mais
# coûteux en hauteur pour une fenêtre à onglets où le tableau Messages
# doit rester la priorité. Une feuille de style appliquée directement à
# chaque bouton de cette fenêtre ne redéfinit que min-height/padding ;
# couleurs, bordure et rayon restent hérités du thème (une feuille de
# style posée sur un widget précis ne remplace, propriété par
# propriété, que ce qu'elle définit elle-même).
_COMPACT_BUTTON_STYLESHEET = "QPushButton { min-height: 28px; padding: 4px 12px; }"

_TABLE_STYLESHEET = f"""
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


class ContestAssistantWindow(BaseWindow):

    def __init__(
        self,
        message_service: ContestMessageService,
        station_service=None,
        transmission_service=None,
        voice_service=None,
        parent=None,
    ):
        super().__init__(
            title="Contest Assistant",
            subtitle="Messages de concours bilingues, numérotation automatique",
        )

        self.message_service = message_service
        self.station_service = station_service
        self.transmission_service = transmission_service
        self.voice_service = voice_service

        # État de l'annonce en cours (étape 4e-3) — voir docstring du
        # module, section "Annoncer". _announce_request_id filtre les
        # signaux de voice_service (ressource partagée) pour ne réagir
        # qu'à notre propre demande.
        self._announcing = False
        self._announce_request_id: str | None = None

        self._build_content()
        self._connect_signals()
        self._refresh_all()
        self._update_announce_button_enabled()

        # Ouvre agrandie plutôt qu'à une taille fixe devinée : voir
        # docstring du module. setWindowState() avant l'affichage
        # (plutôt que showMaximized() ici) pour rester compatible avec
        # le patron d'appel existant, où c'est l'appelant
        # (core/main_window.py) qui décide quand appeler .show().
        self.setWindowState(Qt.WindowState.WindowMaximized)

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_content(self) -> None:
        self.content_layout.setSpacing(8)

        self.content_layout.addLayout(self._build_contest_row())
        self.content_layout.addLayout(self._build_contact_row())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_messages_tab(), "Messages")
        self.tabs.addTab(self._build_history_tab(), "Historique")

        self.content_layout.addWidget(self.tabs, 1)

    def _build_messages_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        layout.addLayout(self._build_message_buttons_row())

        self.template_model = MessageTemplateTableModel()
        self.template_table = self._build_table(self.template_model)
        self.template_table.setMinimumHeight(_MESSAGES_TABLE_MIN_HEIGHT)

        header = self.template_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.template_table)

        return tab

    def _build_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 0)

        self.history_model = SentMessageTableModel()
        self.history_table = self._build_table(self.history_model)
        self.history_table.setMinimumHeight(_HISTORY_TABLE_MIN_HEIGHT)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.history_table)

        return tab

    def _build_contest_row(self) -> QHBoxLayout:
        """Nom du concours, langue, réinitialisation — voir docstring du module, point 4."""

        layout = QHBoxLayout()
        layout.setSpacing(8)

        layout.addWidget(QLabel("Concours"))

        self.edit_contest_name = QComboBox()
        self.edit_contest_name.setEditable(True)
        self.edit_contest_name.addItems(CONTEST_NAMES)
        layout.addWidget(self.edit_contest_name, 1)

        self.btn_language = QPushButton()
        self.btn_language.setStyleSheet(_COMPACT_BUTTON_STYLESHEET)
        layout.addWidget(self.btn_language)

        self.btn_reset = QPushButton("Réinitialiser le concours")
        self.btn_reset.setStyleSheet(_COMPACT_BUTTON_STYLESHEET)
        layout.addWidget(self.btn_reset)

        return layout

    def _build_contact_row(self) -> QHBoxLayout:
        """
        Indicatif, RST puis numéros immédiatement à leur suite — voir
        docstring du module, point 4. Largeur maximale fixe (pas de
        facteur d'étirement) sur les champs texte, addStretch() en fin
        de rangée : le bloc reste groupé à gauche au lieu de s'étaler
        sur toute la largeur de la fenêtre.
        """

        layout = QHBoxLayout()
        layout.setSpacing(8)

        layout.addWidget(QLabel("Indicatif (%CALL%)"))
        self.edit_call = QLineEdit()
        self.edit_call.setMaximumWidth(160)
        layout.addWidget(self.edit_call)

        layout.addWidget(QLabel("RST (%RST%)"))
        self.edit_rst = QLineEdit()
        self.edit_rst.setMaximumWidth(100)
        layout.addWidget(self.edit_rst)

        layout.addSpacing(16)

        layout.addWidget(QLabel("N° envoyé"))
        self.lbl_last_serial = QLabel()
        layout.addWidget(self.lbl_last_serial)

        layout.addWidget(QLabel("→ Prochain"))
        self.lbl_next_serial = QLabel()
        layout.addWidget(self.lbl_next_serial)

        layout.addStretch(1)

        return layout

    def _build_message_buttons_row(self) -> QHBoxLayout:
        # Simple rangée au-dessus du tableau, comme la status_row de
        # DXClusterWindow au-dessus du sien — pas de conteneur partagé
        # avec le tableau, donc rien avec quoi il doive se disputer
        # l'espace disponible.
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.btn_send = QPushButton("Envoyer le message sélectionné")
        self.btn_announce = QPushButton("Annoncer")
        self.btn_add_template = QPushButton("Ajouter")
        self.btn_edit_template = QPushButton("Modifier")
        self.btn_delete_template = QPushButton("Supprimer")
        self.btn_restore_defaults = QPushButton("Restaurer les modèles par défaut")

        for button in (
            self.btn_send,
            self.btn_announce,
            self.btn_add_template,
            self.btn_edit_template,
            self.btn_delete_template,
            self.btn_restore_defaults,
        ):
            button.setStyleSheet(_COMPACT_BUTTON_STYLESHEET)
            layout.addWidget(button)

        return layout

    @staticmethod
    def _build_table(model) -> QTableView:
        """
        Même construction que apps/dxcluster/window.py : aucun
        setMinimumHeight ici (DX Cluster n'en a pas non plus) — la
        hauteur réelle vient uniquement de la politique de taille
        Expanding par défaut d'un QTableView, combinée au facteur
        d'étirement donné par l'appelant au moment de l'ajouter à son
        layout. Le minimum éventuel (Messages/Historique) est ajouté
        séparément par l'appelant, pas ici.
        """

        table = QTableView()
        table.setModel(model)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setStyleSheet(_TABLE_STYLESHEET)

        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(_ROW_HEIGHT)

        return table

    def _connect_signals(self) -> None:
        self.edit_contest_name.activated.connect(self._on_contest_name_activated)
        self.edit_contest_name.lineEdit().editingFinished.connect(self._on_contest_name_edited)

        self.btn_language.clicked.connect(self._on_toggle_language_clicked)
        self.btn_reset.clicked.connect(self._on_reset_contest_clicked)

        self.btn_send.clicked.connect(self._on_send_clicked)
        self.btn_announce.clicked.connect(self._on_announce_clicked)
        self.btn_add_template.clicked.connect(self._on_add_template_clicked)
        self.btn_edit_template.clicked.connect(self._on_edit_template_clicked)
        self.btn_delete_template.clicked.connect(self._on_delete_template_clicked)
        self.btn_restore_defaults.clicked.connect(self._on_restore_defaults_clicked)

        # Connectés une seule fois ici, jamais par clic (ressources
        # partagées) — voir docstring du module. Absents si les
        # services n'ont pas été fournis (bouton alors désactivé en
        # permanence, voir _update_announce_button_enabled()).
        if self.voice_service is not None:
            self.voice_service.synthesis_finished.connect(self._on_voice_synthesis_finished)
            self.voice_service.synthesis_error.connect(self._on_voice_synthesis_error)

        if self.transmission_service is not None:
            self.transmission_service.transmission_finished.connect(self._on_transmission_finished)
            self.transmission_service.transmission_error.connect(self._on_transmission_error)

    # ------------------------------------------------------------------
    # Rafraîchissement de l'affichage
    # ------------------------------------------------------------------

    def _refresh_all(self) -> None:
        self._refresh_contest_name()
        self._refresh_language_button()
        self._refresh_serial_labels()
        self._refresh_template_list()
        self._refresh_history_list()

    def _refresh_contest_name(self) -> None:
        value = self.message_service.contest_name
        index = self.edit_contest_name.findText(value) if value else -1

        if index >= 0:
            self.edit_contest_name.setCurrentIndex(index)
        else:
            self.edit_contest_name.setEditText(value)

    def _refresh_language_button(self) -> None:
        label = "Langue : Français" if self.message_service.language == "FR" else "Langue : English"
        self.btn_language.setText(label)

    def _refresh_serial_labels(self) -> None:
        self.lbl_last_serial.setText(f"{self.message_service.serial:03d}")
        self.lbl_next_serial.setText(f"{self.message_service.next_serial:03d}")

    def _refresh_template_list(self) -> None:
        self.template_model.set_language(self.message_service.language)
        self.template_model.set_templates(self.message_service.templates)

    def _refresh_history_list(self) -> None:
        self.history_model.set_entries(self.message_service.history)

    # ------------------------------------------------------------------
    # Concours
    # ------------------------------------------------------------------

    def _on_contest_name_activated(self, index: int) -> None:
        if self.edit_contest_name.itemText(index) == "Autre...":
            self.edit_contest_name.setEditText("")
            return

        self._on_contest_name_edited()

    def _on_contest_name_edited(self) -> None:
        self.message_service.contest_name = self.edit_contest_name.currentText().strip()
        self.message_service.save()

    def _on_toggle_language_clicked(self) -> None:
        self.message_service.toggle_language()
        self._refresh_language_button()
        self._refresh_template_list()

    def _on_reset_contest_clicked(self) -> None:
        answer = QMessageBox.question(
            self,
            "Réinitialiser le concours",
            "Confirmer la réinitialisation complète du concours ?\n\n"
            "Le nom du concours, le numéro progressif et l'historique seront remis à zéro.\n"
            "Les modèles de message et la langue ne seront pas modifiés.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.message_service.reset_contest()
        self._refresh_contest_name()
        self._refresh_serial_labels()
        self._refresh_history_list()

    # ------------------------------------------------------------------
    # Modèles de message
    # ------------------------------------------------------------------

    def _selected_template(self):
        index = self.template_table.currentIndex()
        if not index.isValid():
            return None
        return self.template_model.template_at(index.row())

    def _on_add_template_clicked(self) -> None:
        dialog = _MessageTemplateDialog(self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        label, text_fr, text_en = dialog.values()

        if not label:
            QMessageBox.information(self, "Libellé requis", "Le modèle doit avoir un libellé.")
            return

        self.message_service.add_template(label, text_fr, text_en)
        self._refresh_template_list()

    def _on_edit_template_clicked(self) -> None:
        template = self._selected_template()

        if template is None:
            QMessageBox.information(self, "Aucune sélection", "Sélectionnez un modèle à modifier.")
            return

        dialog = _MessageTemplateDialog(self, template.label, template.text_fr, template.text_en)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        label, text_fr, text_en = dialog.values()

        if not label:
            QMessageBox.information(self, "Libellé requis", "Le modèle doit avoir un libellé.")
            return

        self.message_service.update_template(template.id, label, text_fr, text_en)
        self._refresh_template_list()

    def _on_delete_template_clicked(self) -> None:
        template = self._selected_template()

        if template is None:
            QMessageBox.information(self, "Aucune sélection", "Sélectionnez un modèle à supprimer.")
            return

        answer = QMessageBox.question(
            self,
            "Supprimer le modèle",
            f"Supprimer le modèle « {template.label} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.message_service.delete_template(template.id)
        self._refresh_template_list()

    def _on_restore_defaults_clicked(self) -> None:
        """
        Recrée les modèles standards manquants (ex. supprimés par
        erreur) sans jamais dupliquer ni modifier ceux déjà présents,
        et sans jamais toucher aux modèles personnels — voir
        ContestMessageService.restore_default_templates().
        """

        restored = self.message_service.restore_default_templates()

        if not restored:
            self.statusBar().showMessage("Tous les modèles standards sont déjà présents.", 3000)
            return

        self._refresh_template_list()

        labels = ", ".join(t.label for t in restored)
        self.statusBar().showMessage(f"Modèle(s) restauré(s) : {labels}", 3000)

    # ------------------------------------------------------------------
    # Envoi (logique uniquement en V1 — voir docstring du module)
    # ------------------------------------------------------------------

    def _on_send_clicked(self) -> None:
        template = self._selected_template()

        if template is None:
            QMessageBox.information(self, "Aucune sélection", "Sélectionnez un message à envoyer.")
            return

        self._send_template(template)

    def _send_template(self, template) -> None:
        values = {
            "CALL": self.edit_call.text().strip(),
            "RST": self.edit_rst.text().strip(),
            "SERIAL": f"{self.message_service.next_serial:03d}",
            "MYCALL": self.station_service.callsign if self.station_service is not None else "",
        }

        text = self.message_service.active_text(template)
        resolved = resolve_variables(text, values)

        self.message_service.record_sent(resolved)

        self._refresh_serial_labels()
        self._refresh_history_list()

        self.statusBar().showMessage(f"Message envoyé : {resolved}", 3000)

    # ------------------------------------------------------------------
    # Annoncer (étape 4e-3 — action indépendante de "Envoyer", voir
    # docstring du module)
    # ------------------------------------------------------------------

    def _services_available_for_announce(self) -> bool:
        return self.voice_service is not None and self.transmission_service is not None

    def _update_announce_button_enabled(self) -> None:
        self.btn_announce.setEnabled(self._services_available_for_announce() and not self._announcing)

    def _on_announce_clicked(self) -> None:
        try:
            self._start_announce()
        except Exception as exc:
            # Dernier recours : "Annoncer" ne doit jamais faire planter
            # la fenêtre, quelle que soit la cause — voir docstring du
            # module.
            self._announcing = False
            self._announce_request_id = None
            self._update_announce_button_enabled()
            self.statusBar().showMessage(f"Erreur inattendue lors de l'annonce : {exc}", 5000)

    def _start_announce(self) -> None:
        if not self._services_available_for_announce():
            return

        template = self._selected_template()

        if template is None:
            QMessageBox.information(self, "Aucune sélection", "Sélectionnez un message à annoncer.")
            return

        values = {
            "CALL": self.edit_call.text().strip(),
            "RST": self.edit_rst.text().strip(),
            "SERIAL": f"{self.message_service.next_serial:03d}",
            "MYCALL": self.station_service.callsign if self.station_service is not None else "",
        }

        text = self.message_service.active_text(template)
        resolved = resolve_variables(text, values)

        self._announcing = True
        self._update_announce_button_enabled()
        self.statusBar().showMessage("Synthèse vocale en cours...", 0)

        self._announce_request_id = self.voice_service.synthesize(
            resolved, cacheable=False, owner="contest_assistant"
        )

    def _on_voice_synthesis_finished(self, request_id: str, output_path: str) -> None:
        if request_id != self._announce_request_id:
            return  # synthèse d'un autre consommateur de voice_service

        self._announce_request_id = None
        self.statusBar().showMessage("Transmission en cours...", 0)

        try:
            self.transmission_service.transmit(output_path, owner="contest_assistant")
        except Exception as exc:
            self._announcing = False
            self._update_announce_button_enabled()
            self.statusBar().showMessage(f"Erreur inattendue lors de la transmission : {exc}", 5000)

    def _on_voice_synthesis_error(self, request_id: str, message: str) -> None:
        if request_id != self._announce_request_id:
            return

        self._announce_request_id = None
        self._announcing = False
        self._update_announce_button_enabled()
        self.statusBar().showMessage(f"Erreur de synthèse vocale : {message}", 5000)

    # TODO (dette technique connue, volontaire à ce stade) :
    # _on_transmission_finished()/_on_transmission_error() ci-dessous ne
    # filtrent PAS par owner/request_id, contrairement à
    # _on_voice_synthesis_finished()/_on_voice_synthesis_error()
    # ci-dessus. Ce n'est pas un bug aujourd'hui : TransmissionService
    # ne permet qu'UNE SEULE transmission à la fois (is_transmitting,
    # voir sa docstring) et aucun autre consommateur ne l'utilise encore
    # dans la Suite. LE JOUR OÙ UN SECOND CONSOMMATEUR DE
    # transmission_service APPARAÎT (ex. Radio Control, une future file
    # d'attente), CE FILTRAGE DEVRA ÊTRE AJOUTÉ ICI (par owner, transmis
    # à transmit()) pour ne jamais réagir à la transmission de
    # quelqu'un d'autre.
    def _on_transmission_finished(self) -> None:
        if not self._announcing:
            return  # transmission d'un autre consommateur éventuel de transmission_service

        self._announcing = False
        self._update_announce_button_enabled()
        self.statusBar().showMessage("Annonce transmise.", 3000)

    def _on_transmission_error(self, message: str) -> None:
        if not self._announcing:
            return

        self._announcing = False
        self._update_announce_button_enabled()
        self.statusBar().showMessage(f"Erreur de transmission : {message}", 5000)


class _MessageTemplateDialog(QDialog):
    """Boîte de dialogue d'ajout/modification d'un modèle de message (libellé + texte FR/EN)."""

    def __init__(self, parent=None, label: str = "", text_fr: str = "", text_en: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Modèle de message")

        layout = QFormLayout(self)

        self.edit_label = QLineEdit(label)
        self.edit_text_fr = QLineEdit(text_fr)
        self.edit_text_en = QLineEdit(text_en)

        layout.addRow("Libellé", self.edit_label)
        layout.addRow("Texte (FR)", self.edit_text_fr)
        layout.addRow("Texte (EN)", self.edit_text_en)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> tuple[str, str, str]:
        return (
            self.edit_label.text().strip(),
            self.edit_text_fr.text().strip(),
            self.edit_text_en.text().strip(),
        )
