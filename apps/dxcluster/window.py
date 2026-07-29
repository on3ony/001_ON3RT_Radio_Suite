"""
ON3RT Radio Suite
Module DX Cluster
Fenêtre du module.
"""

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
)

from libraries.ui import colors
from libraries.ui.base_window import BaseWindow

from apps.dxcluster.table_model import DXClusterTableModel


class DXClusterWindow(BaseWindow):

    def __init__(self, dxcluster_service=None, radio_service=None):
        super().__init__(
            title="DX Cluster",
            subtitle="Spots DX en direct (DXFun)",
        )

        # DXClusterService est un service partagé de la Suite : une
        # seule connexion Telnet pour toute la Suite, injectée depuis
        # core/main_window.py. Cette fenêtre n'ouvre jamais sa propre
        # connexion — si aucun service n'est fourni, elle reste
        # utilisable pour consultation mais l'affiche honnêtement
        # plutôt que d'en créer une.
        self.dxcluster_service = dxcluster_service

        # RadioService partagé, comme dans les autres modules — jamais
        # de CATController direct.
        self.radio_service = radio_service

        self.model = DXClusterTableModel()

        self._build_content()

        self.table.doubleClicked.connect(self.send_to_radio)
        self.connect_button.clicked.connect(self._toggle_connection)

        if self.dxcluster_service is not None:
            self.dxcluster_service.spot_received.connect(self._on_spot_received)
            self.dxcluster_service.connectionChanged.connect(self._on_connection_changed)
            self.model.set_spots(self.dxcluster_service.recent_spots())
            self._update_connection_display(self.dxcluster_service.connected)
        else:
            self.connect_button.setEnabled(False)
            self.connection_label.setText("Connexion : service non disponible")

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_content(self):
        status_row = QHBoxLayout()
        status_row.setSpacing(8)

        self.connection_label = QLabel("Connexion : inconnue")
        self.connect_button = QPushButton("Connecter")

        status_row.addWidget(self.connection_label)
        status_row.addStretch()
        status_row.addWidget(self.connect_button)

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
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Commentaire absorbe l'espace restant

        self.content_layout.addLayout(status_row)
        self.content_layout.addWidget(self.table)

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------

    def _toggle_connection(self) -> None:
        if self.dxcluster_service is None:
            return

        if self.dxcluster_service.connected:
            self.dxcluster_service.disconnect()
        else:
            self.dxcluster_service.connect()

    def _on_connection_changed(self, connected: bool) -> None:
        self._update_connection_display(connected)

    def _update_connection_display(self, connected: bool) -> None:
        self.connection_label.setText("Connexion : connecté" if connected else "Connexion : déconnecté")
        self.connect_button.setText("Déconnecter" if connected else "Connecter")

    # ------------------------------------------------------------------
    # Spots
    # ------------------------------------------------------------------

    def _on_spot_received(self, spot: dict) -> None:
        self.model.add_spot(spot)
        self.statusBar().showMessage(f"Nouveau spot : {spot.get('dx_callsign') or '--'}", 3000)

    def send_to_radio(self) -> None:
        """
        Envoie uniquement la fréquence du spot sélectionné à la radio
        via RadioService — jamais de mode : DXClusterService ne le
        fournit pas (toujours None dans le contrat de spot), donc
        aucun mode n'est jamais inventé ni déduit du commentaire.
        """

        index = self.table.currentIndex()

        if not index.isValid():
            return

        spot = self.model.spot(index.row())
        frequency_khz = spot.get("frequency_khz")

        if not isinstance(frequency_khz, (int, float)):
            return

        if self.radio_service is None:
            QMessageBox.information(
                self,
                "Radio non disponible",
                "Aucun service radio n'est relié au DX Cluster.",
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

    def closeEvent(self, event):
        if self.dxcluster_service is not None:
            self.dxcluster_service.spot_received.disconnect(self._on_spot_received)
            self.dxcluster_service.connectionChanged.disconnect(self._on_connection_changed)
        super().closeEvent(event)
