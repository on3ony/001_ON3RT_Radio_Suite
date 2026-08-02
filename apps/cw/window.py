"""
ON3RT Radio Suite
apps/cw/window.py

Fenêtre CW — saisie libre, macros F1-F12 et envoi de messages Morse en
direct via CWService (libraries/cw/cw_service.py), déjà construit et
injecté depuis core/application.py (étape 2a du chantier). Premier vrai
consommateur de CWService (étape 2b), complété par les macros F1-F12 à
l'étape 2d -- même discipline que le reste de la Suite, une étape à la
fois.

CWService est reçu en injection, jamais créé ici (même convention que
RadioService/DXClusterService dans tous les autres modules) : cette
fenêtre n'importe et ne connaît ni PTTKeyerBackend, ni ElementDriver,
ni aucun détail du matériel/backend/driver -- uniquement l'API publique
de CWService (send()/stop()/state/signaux), exactement l'ignorance
prescrite par libraries/cw/ARCHITECTURE.md pour tout consommateur.

Point d'entrée unique _send_cw_text(text) : tout texte à émettre
(saisie libre aujourd'hui, macros résolues plus tard) passe par cette
seule méthode, qui appelle cw_service.send(text, owner="cw_window").

Affichage d'état : toujours dérivé de cw_service.state au moment de
chaque signal reçu, jamais une valeur supposée à partir du signal
lui-même -- même exigence que pour le champ "État" du panneau Settings
CW (apps/settings/panels/cw_panel.py) : ne jamais afficher un état
inventé.

Boutons Envoyer/Stop : activés/désactivés strictement selon
cw_service.state (SENDING = seul état qui désactive Envoyer et active
Stop), jamais un état local dupliqué -- CWService reste l'unique source
de vérité.

Macros F1-F12 (étape 2d) : 12 boutons qui appellent tous
_send_cw_text() -- même point d'entrée unique que la saisie libre,
aucun chemin d'envoi parallèle. Édition déportée dans une boîte de
dialogue séparée (apps/cw/macro_dialog.py, choix validé avec
l'utilisateur) : cette fenêtre reste orientée utilisation, jamais un
écran de configuration. Les 12 textes sont stockés dans
settings_service.cw["macros"] (texte fixe, aucune résolution de
variable -- ExchangeService reste différé) ; settings_service est reçu
en injection, comme cw_service, jamais créé ici.
"""

from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
)

from libraries.cw.cw_service import CWState
from libraries.ui.base_window import BaseWindow

from apps.cw.macro_dialog import MacroEditDialog

_STATE_LABELS = {
    CWState.IDLE: "inactif",
    CWState.SENDING: "émission en cours",
    CWState.STOPPED: "arrêté",
    CWState.ERROR: "erreur",
}

_MACRO_COUNT = 12


class CWWindow(BaseWindow):

    def __init__(self, cw_service=None, settings_service=None, parent=None):
        super().__init__(title="CW", subtitle="Envoi de Morse en direct")

        # Services partagés, injectés -- jamais créés ici (voir docstring du module).
        self.cw_service = cw_service
        self.settings_service = settings_service

        self._macros = self._load_macros()

        self._build_content()
        self._connect_signals()
        self._build_macro_shortcuts()

        self._refresh_macro_buttons()
        self._sync_state_label()
        self._refresh_buttons()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_content(self) -> None:
        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Texte à envoyer en CW...")
        self.input_text.returnPressed.connect(self._on_send_clicked)

        self.btn_send = QPushButton("Envoyer")
        self.btn_stop = QPushButton("Stop")

        input_row = QHBoxLayout()
        input_row.addWidget(self.input_text, 1)
        input_row.addWidget(self.btn_send)
        input_row.addWidget(self.btn_stop)

        self.lbl_state = QLabel()

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)

        self.macro_buttons: list[QPushButton] = []
        macros_grid = QGridLayout()
        for index in range(_MACRO_COUNT):
            button = QPushButton(f"F{index + 1}")
            button.clicked.connect(lambda _checked=False, i=index: self._on_macro_button_clicked(i))
            self.macro_buttons.append(button)
            macros_grid.addWidget(button, index // 6, index % 6)

        self.btn_edit_macros = QPushButton("Éditer les macros…")
        self.btn_edit_macros.clicked.connect(self._on_edit_macros_clicked)

        self.content_layout.addLayout(input_row)
        self.content_layout.addWidget(self.lbl_state)
        self.content_layout.addWidget(self.progress)
        self.content_layout.addLayout(macros_grid)
        self.content_layout.addWidget(self.btn_edit_macros)
        self.content_layout.addStretch(1)

    def _connect_signals(self) -> None:
        self.btn_send.clicked.connect(self._on_send_clicked)
        self.btn_stop.clicked.connect(self._on_stop_clicked)

        if self.cw_service is not None:
            self.cw_service.cw_started.connect(self._on_cw_started)
            self.cw_service.cw_progress.connect(self._on_cw_progress)
            self.cw_service.cw_finished.connect(self._on_cw_finished)
            self.cw_service.cw_stopped.connect(self._on_cw_stopped)
            self.cw_service.cw_error.connect(self._on_cw_error)

    def _build_macro_shortcuts(self) -> None:
        """Touches F1-F12, actives seulement quand cette fenêtre a le focus (contexte par défaut de QShortcut)."""

        self._macro_shortcuts = []
        for index in range(_MACRO_COUNT):
            shortcut = QShortcut(QKeySequence(f"F{index + 1}"), self)
            shortcut.activated.connect(lambda i=index: self._on_macro_button_clicked(i))
            self._macro_shortcuts.append(shortcut)

    # ------------------------------------------------------------------
    # Point d'entrée unique d'envoi (voir docstring du module)
    # ------------------------------------------------------------------

    def _send_cw_text(self, text: str) -> None:
        if self.cw_service is None:
            self.statusBar().showMessage("CWService indisponible", 3000)
            return

        text = text.strip()
        if not text:
            return

        request_id = self.cw_service.send(text, owner="cw_window")

        if request_id is None:
            self.statusBar().showMessage("Émission déjà en cours", 3000)

    # ------------------------------------------------------------------
    # Actions utilisateur
    # ------------------------------------------------------------------

    def _on_send_clicked(self) -> None:
        self._send_cw_text(self.input_text.text())

    def _on_stop_clicked(self) -> None:
        if self.cw_service is not None:
            self.cw_service.stop()

    # ------------------------------------------------------------------
    # Macros F1-F12 (voir docstring du module)
    # ------------------------------------------------------------------

    def _on_macro_button_clicked(self, index: int) -> None:
        text = self._macros[index]

        if not text.strip():
            self.statusBar().showMessage(f"Macro F{index + 1} vide", 3000)
            return

        self._send_cw_text(text)

    def _on_edit_macros_clicked(self) -> None:
        dialog = MacroEditDialog(self._macros, parent=self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._macros = dialog.edited_macros()
        self._save_macros()
        self._refresh_macro_buttons()

    def _load_macros(self) -> list[str]:
        raw = []
        if self.settings_service is not None:
            raw = list(self.settings_service.cw.get("macros", []))

        return raw[:_MACRO_COUNT] + [""] * max(0, _MACRO_COUNT - len(raw))

    def _save_macros(self) -> None:
        if self.settings_service is None:
            self.statusBar().showMessage("Macros non sauvegardées -- SettingsService indisponible", 3000)
            return

        self.settings_service.cw["macros"] = list(self._macros)
        self.settings_service.save()

    def _refresh_macro_buttons(self) -> None:
        for index, button in enumerate(self.macro_buttons):
            text = self._macros[index].strip()
            button.setToolTip(text if text else "(vide)")

    # ------------------------------------------------------------------
    # Signaux CWService -> affichage (état réel, voir docstring du module)
    # ------------------------------------------------------------------

    def _on_cw_started(self, request_id: str) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self._sync_state_label()
        self._refresh_buttons()

    def _on_cw_progress(self, request_id: str, char_index: int, total_chars: int) -> None:
        self.progress.setRange(0, max(total_chars, 1))
        self.progress.setValue(char_index)

    def _on_cw_finished(self, request_id: str) -> None:
        self._sync_state_label()
        self._refresh_buttons()

    def _on_cw_stopped(self, request_id: str) -> None:
        self._sync_state_label()
        self._refresh_buttons()

    def _on_cw_error(self, request_id: str, message: str) -> None:
        self._sync_state_label(detail=message)
        self._refresh_buttons()

    # ------------------------------------------------------------------
    # État / boutons -- toujours dérivés de cw_service.state
    # ------------------------------------------------------------------

    def _sync_state_label(self, detail: str | None = None) -> None:
        state = self.cw_service.state if self.cw_service is not None else CWState.IDLE
        text = _STATE_LABELS.get(state, state.value)

        if detail:
            text = f"{text} — {detail}"

        self.lbl_state.setText(f"État : {text}")

    def _refresh_buttons(self) -> None:
        sending = self.cw_service is not None and self.cw_service.state is CWState.SENDING
        self.btn_send.setEnabled(not sending)
        self.btn_stop.setEnabled(sending)

        for button in self.macro_buttons:
            button.setEnabled(not sending)

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self.cw_service is not None:
            self.cw_service.cw_started.disconnect(self._on_cw_started)
            self.cw_service.cw_progress.disconnect(self._on_cw_progress)
            self.cw_service.cw_finished.disconnect(self._on_cw_finished)
            self.cw_service.cw_stopped.disconnect(self._on_cw_stopped)
            self.cw_service.cw_error.disconnect(self._on_cw_error)

        super().closeEvent(event)
