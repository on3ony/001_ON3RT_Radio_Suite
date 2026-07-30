"""
ON3RT Radio Suite
apps/bandmap/window.py

Fenêtre du module BandMap — suit automatiquement la bande de la radio
et affiche les spots DX Cluster de cette bande sur BandMapWidget,
l'unique composant graphique de ce module.

RadioService et DXClusterService sont reçus en injection (jamais créés
ici), comme dans tous les autres modules de la suite — aucun nouveau
service n'est introduit par ce fichier. La détection de bande utilise
BandManager (libraries/radio/band_manager.py), en lecture seule via
son attribut public BANDS, exactement comme apps/frequency_bank/
frequency_dialog.py lit déjà BANDS directement : aucune modification
de BandManager.

Le double-clic sur un spot réutilise exactement le mécanisme déjà en
production dans apps/dxcluster/window.py (send_to_radio) : conversion
kHz -> Hz, RadioService.set_frequency(), jamais de mode envoyé (le
contrat de spot de DXClusterService ne le fournit pas).

La connexion DX Cluster reste du ressort exclusif du module DX
Cluster : cette fenêtre n'affiche qu'un indicateur d'état, sans bouton
connecter/déconnecter.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox

from libraries.radio.band_manager import BandManager
from libraries.ui.base_window import BaseWindow

from apps.bandmap.band_map_widget import BandMapWidget


class BandMapWindow(BaseWindow):

    def __init__(self, radio_service=None, dxcluster_service=None, parent=None):
        super().__init__(
            title="BandMap",
            subtitle="Bande active, fréquence radio et spots DX en direct",
        )

        # Services partagés, injectés — jamais créés ici.
        self.radio_service = radio_service
        self.dxcluster_service = dxcluster_service

        # Lecture seule de BandManager, comme RadioService/RadioStatus/
        # DXClusterService le font déjà chacun de leur côté.
        self._band_manager = BandManager()
        self._current_band_name: str | None = None

        self._build_content()
        self._connect_signals()

        self._refresh_band_and_frequency()
        self._update_dxcluster_label(
            self.dxcluster_service.connected if self.dxcluster_service is not None else False
        )

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_content(self) -> None:
        status_row = QHBoxLayout()

        self.dxcluster_status_label = QLabel("DX Cluster : --")
        status_row.addWidget(self.dxcluster_status_label)
        status_row.addStretch()

        self.band_map_widget = BandMapWidget()

        self.content_layout.addLayout(status_row)
        self.content_layout.addWidget(self.band_map_widget)

    def _connect_signals(self) -> None:
        self.band_map_widget.spot_double_clicked.connect(self._on_spot_double_clicked)

        if self.radio_service is not None:
            self.radio_service.updated.connect(self._refresh_band_and_frequency)
            self.radio_service.connectionChanged.connect(self._on_radio_connection_changed)

        if self.dxcluster_service is not None:
            self.dxcluster_service.spot_received.connect(self._on_spot_received)
            self.dxcluster_service.connectionChanged.connect(self._on_dxcluster_connection_changed)

    # ------------------------------------------------------------------
    # Bande active (suit RadioService)
    # ------------------------------------------------------------------

    def _find_band(self, frequency_hz: int):
        """Retourne le Band (name, lower, upper) contenant frequency_hz, ou None."""

        for band in self._band_manager.BANDS:
            if band.lower <= frequency_hz <= band.upper:
                return band

        return None

    def _refresh_band_and_frequency(self) -> None:
        if self.radio_service is None or not self.radio_service.connected:
            self._set_no_active_band()
            return

        frequency_hz = self.radio_service.frequency
        band = self._find_band(frequency_hz)

        if band is None:
            self._set_no_active_band()
            return

        if band.name != self._current_band_name:
            self._current_band_name = band.name
            self.band_map_widget.set_band(band.name, band.lower, band.upper)
            self._reload_spots_for_current_band()

        self.band_map_widget.set_frequency(frequency_hz)

    def _set_no_active_band(self) -> None:
        if self._current_band_name is None:
            return

        self._current_band_name = None
        self.band_map_widget.clear_band()

    def _on_radio_connection_changed(self, _connected: bool) -> None:
        self._refresh_band_and_frequency()

    # ------------------------------------------------------------------
    # Spots DX Cluster (filtrés à la bande active)
    # ------------------------------------------------------------------

    def _reload_spots_for_current_band(self) -> None:
        if self.dxcluster_service is None or self._current_band_name is None:
            self.band_map_widget.set_spots([])
            return

        spots = [
            spot
            for spot in self.dxcluster_service.recent_spots()
            if spot.get("band") == self._current_band_name
        ]
        self.band_map_widget.set_spots(spots)

    def _on_spot_received(self, spot: dict) -> None:
        if self._current_band_name is not None and spot.get("band") == self._current_band_name:
            self.band_map_widget.add_spot(spot)

    def _on_dxcluster_connection_changed(self, connected: bool) -> None:
        self._update_dxcluster_label(connected)

    def _update_dxcluster_label(self, connected: bool) -> None:
        self.dxcluster_status_label.setText(
            "DX Cluster : connecté" if connected else "DX Cluster : déconnecté"
        )

    # ------------------------------------------------------------------
    # Accord par double-clic (même mécanisme que DXClusterWindow.send_to_radio)
    # ------------------------------------------------------------------

    def _on_spot_double_clicked(self, spot: dict) -> None:
        frequency_khz = spot.get("frequency_khz")

        if not isinstance(frequency_khz, (int, float)):
            return

        if self.radio_service is None:
            QMessageBox.information(
                self,
                "Radio non disponible",
                "Aucun service radio n'est relié à BandMap.",
            )
            return

        if not self.radio_service.connected:
            QMessageBox.information(
                self,
                "Radio non connectée",
                "La radio n'est pas connectée : impossible d'envoyer la fréquence.",
            )
            return

        frequency_hz = int(round(frequency_khz * 1000))
        ok = self.radio_service.set_frequency(frequency_hz)

        if not ok:
            QMessageBox.information(self, "Envoi incomplet", "La radio n'a pas accepté la fréquence.")
            return

        self.statusBar().showMessage(
            f"Envoyé à la radio : {frequency_khz:.1f} kHz (mode non transmis, non fourni par le cluster)", 3000
        )

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self.radio_service is not None:
            self.radio_service.updated.disconnect(self._refresh_band_and_frequency)
            self.radio_service.connectionChanged.disconnect(self._on_radio_connection_changed)

        if self.dxcluster_service is not None:
            self.dxcluster_service.spot_received.disconnect(self._on_spot_received)
            self.dxcluster_service.connectionChanged.disconnect(self._on_dxcluster_connection_changed)

        super().closeEvent(event)
