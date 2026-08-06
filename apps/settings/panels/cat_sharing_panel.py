"""
ON3RT Radio Suite
apps/settings/panels/cat_sharing_panel.py

Panneau "CAT Sharing" de l'écran Settings — activation et port du
serveur rigctld (RigctldAdapter, protocole "Hamlib NET rigctl" pour
WSJT-X et logiciels compatibles). Les réglages "enabled"/"port" restent
exclusivement gérés via SettingsService.cat_sharing
(config/settings.json) : ce panneau ne crée, n'importe ni ne modifie
CatSharingService ni RigctldAdapter — même raisonnement que
LivePanel/ServicesPanel/CWPanel pour leurs services respectifs.

Volontairement réduit à ces deux réglages (activer/port), sans bouton
de diagnostic ni lien à partager, contrairement à LivePanel : décision
explicite, pas un oubli.

Activer/modifier "enabled"/"port" ici ne démarre/n'arrête pas un
serveur déjà actif : RigctldAdapter est construit une seule fois au
lancement de la Radio Suite (core/application.py), à partir des
réglages lus à cet instant précis — un changement ici ne prend donc
effet qu'au prochain lancement, affiché honnêtement à l'écran plutôt
que de laisser croire à un effet immédiat, même convention que
LivePanel.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class CatSharingPanel(QWidget):

    def __init__(self, settings_service, parent=None):
        super().__init__(parent)

        self.settings_service = settings_service

        self._build_ui()
        self._load_from_service()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)

        notice = QLabel(
            "Ce réglage prend effet au prochain lancement de la Radio Suite — "
            "le modifier ici ne démarre ni n'arrête un serveur déjà actif."
        )
        notice.setWordWrap(True)
        outer.addWidget(notice)

        outer.addWidget(self._build_sharing_group())

        self.btn_save = QPushButton("Enregistrer")
        outer.addWidget(self.btn_save)

        outer.addStretch(1)

    def _build_sharing_group(self) -> QGroupBox:
        group = QGroupBox("Partage CAT (rigctld)")
        form = QFormLayout(group)

        self.check_enabled = QCheckBox("Activer le serveur rigctld (WSJT-X et compatibles)")

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)

        form.addRow(self.check_enabled)
        form.addRow("Port", self.spin_port)

        return group

    def _connect_signals(self):
        self.btn_save.clicked.connect(self._on_save_clicked)

    # ------------------------------------------------------------------
    # SettingsService -> champs
    # ------------------------------------------------------------------

    def _load_from_service(self):
        cat_sharing = self.settings_service.cat_sharing

        self.check_enabled.setChecked(cat_sharing["enabled"])
        self.spin_port.setValue(cat_sharing["port"])

    # ------------------------------------------------------------------
    # Champs -> SettingsService
    # ------------------------------------------------------------------

    def _on_save_clicked(self):
        cat_sharing = self.settings_service.cat_sharing

        cat_sharing["enabled"] = self.check_enabled.isChecked()
        cat_sharing["port"] = self.spin_port.value()

        self.settings_service.save()
