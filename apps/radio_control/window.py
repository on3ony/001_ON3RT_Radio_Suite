"""
ON3RT Radio Suite
Application : Radio Control
"""

from libraries.ui.base_window import BaseWindow

from .controller import RadioController
from .panels.connection_panel import ConnectionPanel
from .panels.radio_panel import RadioPanel


class RadioControlWindow(BaseWindow):
    """
    Fenêtre principale Radio Control.
    """

    def __init__(self, radio_service=None):
        super().__init__(
            title="Radio Control",
            subtitle="Contrôle de l'ICOM IC-7300"
        )

        self.build_ui()

        # Contrôleur — reçoit le RadioService partagé de l'Application
        # (aucune connexion série propre s'il est déjà fourni).
        self.controller = RadioController(self, radio_service=radio_service)

    def build_ui(self):
        """Construit l'interface."""

        self.radio_panel = RadioPanel()
        self.content_layout.addWidget(self.radio_panel)

        self.connection_panel = ConnectionPanel()
        self.content_layout.addWidget(self.connection_panel)

        self.content_layout.addStretch()

        self.statusBar().showMessage("Radio Control prêt")