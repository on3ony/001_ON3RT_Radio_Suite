"""
ON3RT Radio Suite
apps/settings/panels/services_panel.py

Panneau "Services" de l'écran Settings — intervalles de sondage
Open-Meteo/HamQSL et hôte/port DX Cluster.

Utilise exclusivement SettingsService.services (config/settings.json) :
ce panneau ne crée, n'importe ni ne modifie WeatherService,
PropagationService ou DXClusterService — aucune logique réseau ici.

Ces trois services sont construits une seule fois, au lancement de la
suite (core/application.py), avec les valeurs de SettingsService lues
à cet instant : une modification depuis ce panneau ne prend donc effet
qu'au prochain lancement de la Radio Suite, jamais en direct. C'est un
choix assumé (pas de méthode reconfigure() ajoutée à ces services pour
cette première version) — affiché honnêtement à l'écran plutôt que de
laisser croire à un effet immédiat.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

_MIN_INTERVAL_MINUTES = 1
_MAX_INTERVAL_MINUTES = 1440  # 24 h


class ServicesPanel(QWidget):

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
            "Les modifications de cet onglet prennent effet au prochain "
            "lancement de la Radio Suite."
        )
        notice.setWordWrap(True)
        outer.addWidget(notice)

        outer.addWidget(self._build_open_meteo_group())
        outer.addWidget(self._build_hamqsl_group())
        outer.addWidget(self._build_dxcluster_group())

        self.btn_save = QPushButton("Enregistrer")
        outer.addWidget(self.btn_save)

        outer.addStretch(1)

    def _build_open_meteo_group(self) -> QGroupBox:
        group = QGroupBox("Open-Meteo")
        form = QFormLayout(group)

        self.spin_open_meteo_interval = QSpinBox()
        self.spin_open_meteo_interval.setRange(_MIN_INTERVAL_MINUTES, _MAX_INTERVAL_MINUTES)
        self.spin_open_meteo_interval.setSuffix(" min")

        form.addRow("Intervalle de sondage", self.spin_open_meteo_interval)

        return group

    def _build_hamqsl_group(self) -> QGroupBox:
        group = QGroupBox("HamQSL")
        form = QFormLayout(group)

        self.spin_hamqsl_interval = QSpinBox()
        self.spin_hamqsl_interval.setRange(_MIN_INTERVAL_MINUTES, _MAX_INTERVAL_MINUTES)
        self.spin_hamqsl_interval.setSuffix(" min")

        form.addRow("Intervalle de sondage", self.spin_hamqsl_interval)

        return group

    def _build_dxcluster_group(self) -> QGroupBox:
        group = QGroupBox("DX Cluster")
        form = QFormLayout(group)

        self.edit_dxcluster_host = QLineEdit()

        self.spin_dxcluster_port = QSpinBox()
        self.spin_dxcluster_port.setRange(1, 65535)

        form.addRow("Hôte", self.edit_dxcluster_host)
        form.addRow("Port", self.spin_dxcluster_port)

        return group

    def _connect_signals(self):
        self.btn_save.clicked.connect(self._on_save_clicked)

    # ------------------------------------------------------------------
    # SettingsService -> champs
    # ------------------------------------------------------------------

    def _load_from_service(self):
        services = self.settings_service.services

        self.spin_open_meteo_interval.setValue(
            self._ms_to_minutes(services["open_meteo_poll_interval_ms"])
        )
        self.spin_hamqsl_interval.setValue(
            self._ms_to_minutes(services["hamqsl_poll_interval_ms"])
        )
        self.edit_dxcluster_host.setText(services["dxcluster_host"])
        self.spin_dxcluster_port.setValue(services["dxcluster_port"])

    # ------------------------------------------------------------------
    # Champs -> SettingsService
    # ------------------------------------------------------------------

    def _on_save_clicked(self):
        services = self.settings_service.services

        services["open_meteo_poll_interval_ms"] = self._minutes_to_ms(
            self.spin_open_meteo_interval.value()
        )
        services["hamqsl_poll_interval_ms"] = self._minutes_to_ms(
            self.spin_hamqsl_interval.value()
        )
        services["dxcluster_host"] = self.edit_dxcluster_host.text().strip()
        services["dxcluster_port"] = self.spin_dxcluster_port.value()

        self.settings_service.save()

    # ------------------------------------------------------------------
    # Conversion d'affichage (minutes <-> millisecondes)
    # ------------------------------------------------------------------

    @staticmethod
    def _ms_to_minutes(value_ms: int) -> int:
        return max(_MIN_INTERVAL_MINUTES, round(value_ms / 60_000))

    @staticmethod
    def _minutes_to_ms(minutes: int) -> int:
        return minutes * 60_000
