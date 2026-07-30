"""
ON3RT Radio Suite
apps/settings/panels/network_panel.py

Panneau "Réseau" de l'écran Settings — identifiants des services
réseau utilisés par la suite.

QRZ.com passe exclusivement par les fonctions déjà existantes de
libraries/qrz/service.py : _load_config() pour préremplir le
formulaire (même fichier lu par client(), jamais dupliqué ici) et
save_credentials() (ajoutée à l'étape 4) pour l'enregistrement.
config/qrz.json reste l'unique emplacement de ces identifiants.

HamQTH, LoTW, eQSL et Club Log n'ont aujourd'hui aucun client ni
aucune logique de connexion dans la suite : leurs champs sont
uniquement stockés dans SettingsService.network (config/settings.json)
en préparation d'une intégration future, sans aucune logique
supplémentaire ici au-delà de la lecture/écriture.

Aucune connexion réseau automatique, aucun bouton "Tester" — un seul
bouton "Enregistrer", qui écrit vers les deux emplacements ci-dessus
et rien d'autre.
"""

from __future__ import annotations

import libraries.qrz.service as qrz_service
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class NetworkPanel(QWidget):

    def __init__(self, settings_service, parent=None):
        super().__init__(parent)

        self.settings_service = settings_service

        self._build_ui()
        self._load_from_services()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)

        outer.addWidget(self._build_qrz_group())

        hamqth_group, self.edit_hamqth_username, self.edit_hamqth_password = (
            self._build_credential_group("HamQTH")
        )
        outer.addWidget(hamqth_group)

        lotw_group, self.edit_lotw_username, self.edit_lotw_password = (
            self._build_credential_group("LoTW")
        )
        outer.addWidget(lotw_group)

        eqsl_group, self.edit_eqsl_username, self.edit_eqsl_password = (
            self._build_credential_group("eQSL")
        )
        outer.addWidget(eqsl_group)

        outer.addWidget(self._build_clublog_group())

        self.btn_save = QPushButton("Enregistrer")
        outer.addWidget(self.btn_save)

        outer.addStretch(1)

    def _build_qrz_group(self) -> QGroupBox:
        group = QGroupBox("QRZ.com")
        form = QFormLayout(group)

        self.edit_qrz_username = QLineEdit()
        self.edit_qrz_password = QLineEdit()
        self.edit_qrz_password.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Identifiant", self.edit_qrz_username)
        form.addRow("Mot de passe", self.edit_qrz_password)

        return group

    def _build_clublog_group(self) -> QGroupBox:
        group = QGroupBox("Club Log")
        form = QFormLayout(group)

        self.edit_clublog_email = QLineEdit()
        self.edit_clublog_password = QLineEdit()
        self.edit_clublog_password.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("E-mail", self.edit_clublog_email)
        form.addRow("Mot de passe", self.edit_clublog_password)

        return group

    @staticmethod
    def _build_credential_group(title: str):
        """Bloc identifiant/mot de passe générique, réutilisé par HamQTH/LoTW/eQSL."""

        group = QGroupBox(title)
        form = QFormLayout(group)

        username_edit = QLineEdit()
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Identifiant", username_edit)
        form.addRow("Mot de passe", password_edit)

        return group, username_edit, password_edit

    def _connect_signals(self):
        self.btn_save.clicked.connect(self._on_save_clicked)

    # ------------------------------------------------------------------
    # Services -> champs
    # ------------------------------------------------------------------

    def _load_from_services(self):
        qrz_credentials = self._load_qrz_credentials()
        self.edit_qrz_username.setText(qrz_credentials.get("username", ""))
        self.edit_qrz_password.setText(qrz_credentials.get("password", ""))

        network = self.settings_service.network
        self.edit_hamqth_username.setText(network["hamqth_username"])
        self.edit_hamqth_password.setText(network["hamqth_password"])
        self.edit_lotw_username.setText(network["lotw_username"])
        self.edit_lotw_password.setText(network["lotw_password"])
        self.edit_eqsl_username.setText(network["eqsl_username"])
        self.edit_eqsl_password.setText(network["eqsl_password"])
        self.edit_clublog_email.setText(network["clublog_email"])
        self.edit_clublog_password.setText(network["clublog_password"])

    @staticmethod
    def _load_qrz_credentials() -> dict:
        """
        Lit config/qrz.json via _load_config(), déjà existante dans
        libraries/qrz/service.py (le même fichier que client() lit) —
        jamais dupliquée ici. Aucun identifiant configuré (fichier
        absent ou illisible) -> champs vides, aucune donnée inventée.
        """

        try:
            return qrz_service._load_config()
        except (FileNotFoundError, OSError, ValueError):
            return {}

    # ------------------------------------------------------------------
    # Champs -> services
    # ------------------------------------------------------------------

    def _on_save_clicked(self):
        qrz_service.save_credentials(
            self.edit_qrz_username.text().strip(),
            self.edit_qrz_password.text(),
        )

        network = self.settings_service.network
        network["hamqth_username"] = self.edit_hamqth_username.text().strip()
        network["hamqth_password"] = self.edit_hamqth_password.text()
        network["lotw_username"] = self.edit_lotw_username.text().strip()
        network["lotw_password"] = self.edit_lotw_password.text()
        network["eqsl_username"] = self.edit_eqsl_username.text().strip()
        network["eqsl_password"] = self.edit_eqsl_password.text()
        network["clublog_email"] = self.edit_clublog_email.text().strip()
        network["clublog_password"] = self.edit_clublog_password.text()

        self.settings_service.save()
