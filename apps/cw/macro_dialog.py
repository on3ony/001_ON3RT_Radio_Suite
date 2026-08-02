"""
ON3RT Radio Suite
apps/cw/macro_dialog.py

Boîte de dialogue dédiée à l'édition des 12 macros F1-F12 du module CW
(voir apps/cw/window.py, étape 2d) -- écran de configuration séparé,
pour garder la fenêtre CW elle-même orientée utilisation (choix validé
avec l'utilisateur). Texte fixe uniquement pour chaque macro -- aucune
résolution de variable (%CALL%/%RST%/...), ExchangeService reste
différé (voir libraries/cw/ARCHITECTURE.md) : ce champ ne fait que
stocker et retourner du texte brut, rien de plus.

Ne lit ni n'écrit SettingsService lui-même : reçoit les 12 valeurs
initiales en entrée, retourne les 12 valeurs éditées via
edited_macros() une fois la boîte acceptée -- c'est à l'appelant
(CWWindow) de les persister dans settings_service.cw["macros"], même
séparation des responsabilités que le reste de la Suite (une boîte de
dialogue ne connaît jamais directement le fichier de configuration).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

MACRO_COUNT = 12


class MacroEditDialog(QDialog):

    def __init__(self, macros: list[str], parent=None):
        super().__init__(parent)

        self.setWindowTitle("Éditer les macros F1-F12")
        self.resize(420, 420)

        self._fields: list[QLineEdit] = []

        layout = QVBoxLayout(self)
        form = QFormLayout()

        padded = list(macros[:MACRO_COUNT]) + [""] * max(0, MACRO_COUNT - len(macros))

        for index in range(MACRO_COUNT):
            field = QLineEdit(padded[index])
            self._fields.append(field)
            form.addRow(f"F{index + 1}", field)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def edited_macros(self) -> list[str]:
        return [field.text() for field in self._fields]
