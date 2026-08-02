"""
ON3RT Radio Suite
apps/settings/panels/cw_panel.py

Panneau "CW" de l'écran Settings — vitesse (WPM), Farnsworth, et
information sur le backend de keying actif. Utilise exclusivement
SettingsService.cw (config/settings.json) : ce panneau ne crée,
n'importe ni ne modifie CWService/PTTKeyerBackend — même raisonnement
que ServicesPanel pour Weather/Propagation/DXCluster.

CWService n'est pas encore instancié par core/application.py à cette
étape du chantier (viendra avec l'intégration dans Contest Assistant/
apps/cw — étapes ultérieures) : ces réglages sont déjà persistés, mais
n'ont d'effet réel qu'une fois CWService câblé dans l'application —
affiché honnêtement à l'écran plutôt que de laisser croire à un effet
immédiat, même convention que ServicesPanel.

Backend de keying : information seule pour l'instant, pas un
sélecteur fonctionnel — PTTKeyerBackend est le seul backend réel
aujourd'hui (voir libraries/cw/keyer_backend.py). Un vrai sélecteur
n'apparaîtra qu'une fois Winkeyer réellement implémenté : présenter un
choix qui ne ferait rien serait trompeur.

Farnsworth jamais supérieur à la vitesse caractère (WPM) : même
contrainte que TimingEngine (libraries/cw/timing.py), appliquée ici en
amont pour ne jamais permettre de sauvegarder une combinaison
incohérente — le plafond du réglage Farnsworth suit dynamiquement la
valeur WPM courante.

Tonalité (sidetone_hz) : réglage préparatoire à l'étape 10 (sidetone
via AudioOutputService, pas encore implémentée) — persisté dès
maintenant pour ne jamais casser la compatibilité de
config/settings.json quand cette fonctionnalité arrivera, mais sans
effet sonore réel aujourd'hui, comme WPM/Farnsworth/Backend.

Contrainte ergonomique (validée avec l'utilisateur) : au chargement,
chaque réglage affiché doit toujours montrer une valeur déterminée --
celle de Settings si présente, sinon la valeur par défaut de
l'application -- jamais un champ vide ni un état indéterminé.
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

_MIN_WPM = 5
_MAX_WPM = 60

_MIN_SIDETONE_HZ = 300
_MAX_SIDETONE_HZ = 1200


class CWPanel(QWidget):

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
            "Ces réglages seront utilisés une fois CWService intégré à "
            "l'application (étape ultérieure du chantier CW) — aucun "
            "effet immédiat aujourd'hui."
        )
        notice.setWordWrap(True)
        outer.addWidget(notice)

        outer.addWidget(self._build_speed_group())
        outer.addWidget(self._build_sidetone_group())
        outer.addWidget(self._build_backend_group())

        self.btn_save = QPushButton("Enregistrer")
        outer.addWidget(self.btn_save)

        outer.addStretch(1)

    def _build_speed_group(self) -> QGroupBox:
        group = QGroupBox("Vitesse")
        form = QFormLayout(group)

        self.spin_wpm = QSpinBox()
        self.spin_wpm.setRange(_MIN_WPM, _MAX_WPM)
        self.spin_wpm.setSuffix(" WPM")

        self.check_farnsworth = QCheckBox("Activer le Farnsworth")

        self.spin_farnsworth_wpm = QSpinBox()
        self.spin_farnsworth_wpm.setRange(_MIN_WPM, _MAX_WPM)
        self.spin_farnsworth_wpm.setSuffix(" WPM")

        form.addRow("Vitesse des caractères", self.spin_wpm)
        form.addRow(self.check_farnsworth)
        form.addRow("Vitesse Farnsworth (globale)", self.spin_farnsworth_wpm)

        return group

    def _build_sidetone_group(self) -> QGroupBox:
        group = QGroupBox("Sidetone")
        form = QFormLayout(group)

        self.spin_sidetone_hz = QSpinBox()
        self.spin_sidetone_hz.setRange(_MIN_SIDETONE_HZ, _MAX_SIDETONE_HZ)
        self.spin_sidetone_hz.setSuffix(" Hz")

        form.addRow("Tonalité", self.spin_sidetone_hz)

        return group

    def _build_backend_group(self) -> QGroupBox:
        group = QGroupBox("Backend de keying")
        layout = QVBoxLayout(group)

        info = QLabel(
            "Backend actif : PTT (PTTKeyerBackend) — seul backend "
            "disponible actuellement. Un backend Winkeyer sera ajouté "
            "ultérieurement, sans qu'aucun réglage CWService n'ait à changer."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        return group

    def _connect_signals(self):
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.check_farnsworth.toggled.connect(self.spin_farnsworth_wpm.setEnabled)
        self.spin_wpm.valueChanged.connect(self._on_wpm_changed)

    # ------------------------------------------------------------------
    # Farnsworth jamais superieur au WPM courant (voir docstring du module)
    # ------------------------------------------------------------------

    def _on_wpm_changed(self, wpm: int) -> None:
        self.spin_farnsworth_wpm.setMaximum(wpm)
        if self.spin_farnsworth_wpm.value() > wpm:
            self.spin_farnsworth_wpm.setValue(wpm)

    # ------------------------------------------------------------------
    # SettingsService -> champs
    # ------------------------------------------------------------------

    def _load_from_service(self):
        cw = self.settings_service.cw

        self.spin_wpm.setValue(cw["wpm"])
        self.spin_farnsworth_wpm.setMaximum(cw["wpm"])

        farnsworth_wpm = cw["farnsworth_wpm"]
        has_farnsworth = farnsworth_wpm is not None

        self.check_farnsworth.setChecked(has_farnsworth)
        self.spin_farnsworth_wpm.setValue(farnsworth_wpm if has_farnsworth else cw["wpm"])
        self.spin_farnsworth_wpm.setEnabled(has_farnsworth)

        self.spin_sidetone_hz.setValue(cw["sidetone_hz"])

    # ------------------------------------------------------------------
    # Champs -> SettingsService
    # ------------------------------------------------------------------

    def _on_save_clicked(self):
        cw = self.settings_service.cw

        cw["wpm"] = self.spin_wpm.value()
        cw["farnsworth_wpm"] = self.spin_farnsworth_wpm.value() if self.check_farnsworth.isChecked() else None
        cw["sidetone_hz"] = self.spin_sidetone_hz.value()

        self.settings_service.save()
