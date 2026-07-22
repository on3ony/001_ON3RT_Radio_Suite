"""
ON3RT Radio Suite
Classe de base commune à tous les modules.
"""

from libraries.ui.base_window import BaseWindow


class BaseModule(BaseWindow):
    """
    Classe de base de tous les modules de la Radio Suite.

    Tous les modules héritent de cette classe afin d'obtenir
    automatiquement :
        - le thème ON3RT
        - le logo
        - la barre d'état
        - les futurs menus
        - la future barre d'outils
    """

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__(
            title=title,
            subtitle=subtitle,
        )

    def set_module_widget(self, widget):
        """
        Place le widget principal du module.
        """
        self.content_layout.addWidget(widget)

    def set_status(self, message: str):
        """
        Modifie le texte de la barre d'état.
        """
        self.statusBar().showMessage(message)