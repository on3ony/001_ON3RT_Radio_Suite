"""
ON3RT Radio Suite
Module Scanner
Fenêtre du module.
"""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from libraries.ui import colors
from libraries.ui.base_window import BaseWindow

from apps.scanner.scanner_engine import ScannerEngine
from apps.scanner.scanner_model import ScannerModel


class ScannerWindow(BaseWindow):

    def __init__(self, radio_service=None, frequency_service=None):
        super().__init__(
            title="Scanner",
            subtitle="Balayage de fréquences — pilotage radio réel",
        )

        # RadioService / FrequencyService partagés, comme dans les
        # autres modules — jamais créés ici, jamais d'accès direct à
        # CATController ni à FrequencyRepository.
        self.radio_service = radio_service
        self.frequency_service = frequency_service

        self.model = ScannerModel()

        self._settings = QSettings("ON3RT", "Scanner")
        self._load_settings()

        # Si la radio est déjà connectée, on part de sa fréquence
        # réelle plutôt que d'une valeur arbitraire — l'affichage doit
        # refléter l'état réel dès l'ouverture.
        if self.radio_service is not None and self.radio_service.connected:
            try:
                self.model.set_frequency(self.radio_service.frequency)
            except ValueError:
                pass

        self.engine = ScannerEngine(self.model, radio_service=self.radio_service)

        self._build_content()
        self._connect_signals()

        self._update_frequency_display(self.model.current_freq_hz)
        self._reload_memories()

    # ------------------------------------------------------------------
    # Paramètres persistants (QSettings — aucune persistance propre au
    # Scanner, conformément à l'architecture validée)
    # ------------------------------------------------------------------

    def _load_settings(self):
        start_hz = self._settings.value("start_freq_hz", self.model.start_freq_hz, type=int)
        stop_hz = self._settings.value("stop_freq_hz", self.model.stop_freq_hz, type=int)
        step_hz = self._settings.value("step_hz", self.model.step_hz, type=int)
        speed_ms = self._settings.value("speed_ms", self.model.speed_ms, type=int)

        try:
            self.model.set_limits(start_hz, stop_hz)
        except ValueError:
            pass  # bornes sauvegardées incohérentes : conserve les valeurs par défaut du modèle

        self.model.step_hz = step_hz
        self.model.speed_ms = speed_ms

    def _save_settings(self):
        self._settings.setValue("start_freq_hz", self.model.start_freq_hz)
        self._settings.setValue("stop_freq_hz", self.model.stop_freq_hz)
        self._settings.setValue("step_hz", self.model.step_hz)
        self._settings.setValue("speed_ms", self.model.speed_ms)

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_content(self):
        display_row = QHBoxLayout()

        self.frequency_label = QLabel("--")
        self.frequency_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frequency_label.setStyleSheet(
            f"font-size:22px; font-weight:bold; color:{colors.ACCENT_CYAN};"
        )

        self.band_label = QLabel("Bande : --")
        self.band_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.band_label.setStyleSheet(f"font-size:11pt; color:{colors.TEXT_SECONDARY};")

        display_col = QVBoxLayout()
        display_col.addWidget(self.frequency_label)
        display_col.addWidget(self.band_label)

        display_row.addStretch()
        display_row.addLayout(display_col)
        display_row.addStretch()

        control_row = QHBoxLayout()

        self.btn_start = QPushButton("▶ Start")
        self.btn_stop = QPushButton("■ Stop")
        self.btn_step_down = QPushButton("▼ Pas -")
        self.btn_step_up = QPushButton("▲ Pas +")

        self.btn_stop.setEnabled(False)

        for button in (self.btn_start, self.btn_stop, self.btn_step_down, self.btn_step_up):
            control_row.addWidget(button)

        self.status_label = QLabel("Scanner arrêté")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"font-size:10pt; color:{colors.TEXT_SECONDARY};")

        params_group = QGroupBox("Paramètres de balayage")
        params_form = QFormLayout(params_group)

        self.spin_start = QDoubleSpinBox()
        self.spin_start.setDecimals(6)
        self.spin_start.setRange(0.000001, 999.999999)
        self.spin_start.setSuffix(" MHz")
        self.spin_start.setValue(self.model.start_freq_hz / 1_000_000)

        self.spin_stop = QDoubleSpinBox()
        self.spin_stop.setDecimals(6)
        self.spin_stop.setRange(0.000001, 999.999999)
        self.spin_stop.setSuffix(" MHz")
        self.spin_stop.setValue(self.model.stop_freq_hz / 1_000_000)

        self.spin_step = QSpinBox()
        self.spin_step.setRange(1, 1_000_000)
        self.spin_step.setSuffix(" Hz")
        self.spin_step.setValue(self.model.step_hz)

        self.spin_speed = QSpinBox()
        self.spin_speed.setRange(20, 10_000)
        self.spin_speed.setSuffix(" ms")
        self.spin_speed.setValue(self.model.speed_ms)

        self.btn_apply = QPushButton("Appliquer")

        params_form.addRow("Début", self.spin_start)
        params_form.addRow("Fin", self.spin_stop)
        params_form.addRow("Pas", self.spin_step)
        params_form.addRow("Vitesse", self.spin_speed)
        params_form.addRow(self.btn_apply)

        memories_group = QGroupBox("Mémoires (favoris de la Banque de fréquences)")
        memories_layout = QVBoxLayout(memories_group)

        self.memory_list = QListWidget()
        self.memory_list.setStyleSheet(
            f"""
            QListWidget {{
                background-color: {colors.BG_PANEL};
                border: 1px solid {colors.BORDER};
                color: {colors.TEXT_PRIMARY};
            }}
            QListWidget::item:selected {{
                background-color: {colors.ACCENT};
                color: #ffffff;
            }}
            """
        )
        memories_layout.addWidget(self.memory_list)

        self.content_layout.addLayout(display_row)
        self.content_layout.addLayout(control_row)
        self.content_layout.addWidget(self.status_label)
        self.content_layout.addWidget(params_group)
        self.content_layout.addWidget(memories_group)

    def _connect_signals(self):
        self.btn_start.clicked.connect(self._on_start_clicked)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        self.btn_step_up.clicked.connect(lambda: self._manual_step("UP"))
        self.btn_step_down.clicked.connect(lambda: self._manual_step("DOWN"))
        self.btn_apply.clicked.connect(self._apply_settings)
        self.memory_list.itemDoubleClicked.connect(self._on_memory_double_clicked)

        self.engine.frequency_changed.connect(self._update_frequency_display)
        self.engine.started.connect(self._on_scan_started)
        self.engine.stopped.connect(self._on_scan_stopped)

        if self.frequency_service is not None:
            self.frequency_service.frequency_added.connect(self._on_frequency_bank_changed)
            self.frequency_service.frequency_updated.connect(self._on_frequency_bank_changed)
            self.frequency_service.frequency_deleted.connect(self._on_frequency_bank_changed)
            self.frequency_service.bank_reloaded.connect(self._reload_memories)

    # ------------------------------------------------------------------
    # Balayage
    # ------------------------------------------------------------------

    def _on_start_clicked(self) -> None:
        if not self.engine.start():
            QMessageBox.information(
                self,
                "Radio non disponible",
                "Impossible de démarrer le balayage : aucune radio connectée.",
            )

    def _on_stop_clicked(self) -> None:
        self.engine.stop()

    def _on_scan_started(self) -> None:
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_step_up.setEnabled(False)
        self.btn_step_down.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.memory_list.setEnabled(False)

        self.status_label.setText("Scanner en fonctionnement")
        self.status_label.setStyleSheet(
            f"font-size:10pt; font-weight:bold; color:{colors.STATE_GREEN};"
        )

    def _on_scan_stopped(self) -> None:
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_step_up.setEnabled(True)
        self.btn_step_down.setEnabled(True)
        self.btn_apply.setEnabled(True)
        self.memory_list.setEnabled(True)

        self.status_label.setText("Scanner arrêté")
        self.status_label.setStyleSheet(f"font-size:10pt; color:{colors.TEXT_SECONDARY};")

    def _manual_step(self, direction: str) -> None:
        if self.radio_service is None or not self.radio_service.connected:
            QMessageBox.information(
                self,
                "Radio non disponible",
                "Impossible de déplacer la fréquence : aucune radio connectée.",
            )
            return

        freq = self.model.step_up() if direction == "UP" else self.model.step_down()
        self.radio_service.set_frequency(freq)
        self._update_frequency_display(freq)

    # ------------------------------------------------------------------
    # Paramètres
    # ------------------------------------------------------------------

    def _apply_settings(self) -> None:
        start_hz = int(round(self.spin_start.value() * 1_000_000))
        stop_hz = int(round(self.spin_stop.value() * 1_000_000))

        try:
            self.model.set_limits(start_hz, stop_hz)
        except ValueError as exc:
            QMessageBox.information(self, "Limites invalides", str(exc))
            return

        self.model.step_hz = self.spin_step.value()
        self.engine.set_speed(self.spin_speed.value())

        self._save_settings()

        if not (start_hz <= self.model.current_freq_hz <= stop_hz):
            self.model.set_frequency(start_hz)  # toujours valide : start_hz appartient à ses propres bornes

            if self.radio_service is not None and self.radio_service.connected:
                self.radio_service.set_frequency(self.model.current_freq_hz)

            self._update_frequency_display(self.model.current_freq_hz)

        self.statusBar().showMessage("Paramètres appliqués", 3000)

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------

    def _update_frequency_display(self, freq_hz: int) -> None:
        self.frequency_label.setText(f"{freq_hz / 1_000_000:.6f} MHz")

        band_text = "--"

        if self.frequency_service is not None:
            info = self.frequency_service.detect_band(freq_hz / 1_000_000)
            band_text = info.get("band") or "--"

        self.band_label.setText(f"Bande : {band_text}")

    # ------------------------------------------------------------------
    # Mémoires (FrequencyService — aucune persistance propre au Scanner)
    # ------------------------------------------------------------------

    def _on_frequency_bank_changed(self, _payload) -> None:
        self._reload_memories()

    def _reload_memories(self) -> None:
        self.memory_list.clear()

        if self.frequency_service is None:
            item = QListWidgetItem("Service de fréquences indisponible")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.memory_list.addItem(item)
            return

        favorites = self.frequency_service.favorites()

        if not favorites:
            item = QListWidgetItem("Aucun favori dans la Banque de fréquences")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.memory_list.addItem(item)
            return

        for frequency in favorites:
            label = f"{frequency.frequency:.6f} MHz — {frequency.name or frequency.band or '--'}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, frequency)
            self.memory_list.addItem(item)

    def _on_memory_double_clicked(self, item: QListWidgetItem) -> None:
        frequency = item.data(Qt.ItemDataRole.UserRole)

        if frequency is None:
            return

        freq_hz = int(round(frequency.frequency * 1_000_000))

        if not (self.model.start_freq_hz <= freq_hz <= self.model.stop_freq_hz):
            QMessageBox.information(
                self,
                "Hors limites",
                "Cette mémoire est en dehors des limites actuelles du balayage.",
            )
            return

        self.model.set_frequency(freq_hz)

        if self.radio_service is not None and self.radio_service.connected:
            self.radio_service.set_frequency(freq_hz)
        else:
            QMessageBox.information(
                self,
                "Radio non disponible",
                "Fréquence positionnée localement : aucune radio connectée pour l'envoyer réellement.",
            )

        self._update_frequency_display(freq_hz)

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        # Le balayage pilote réellement la radio : il ne doit jamais
        # continuer en arrière-plan une fois la fenêtre fermée.
        self.engine.stop()

        if self.frequency_service is not None:
            self.frequency_service.frequency_added.disconnect(self._on_frequency_bank_changed)
            self.frequency_service.frequency_updated.disconnect(self._on_frequency_bank_changed)
            self.frequency_service.frequency_deleted.disconnect(self._on_frequency_bank_changed)
            self.frequency_service.bank_reloaded.disconnect(self._reload_memories)

        super().closeEvent(event)
