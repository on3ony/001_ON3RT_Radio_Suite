"""
core/application.py
-------------------------------------------------
ON3RT Radio Suite V3

Cœur de l'application.

Responsabilités :
    - gestion du ModuleManager
    - informations générales
    - fermeture propre des modules
"""

from core.module_manager import ModuleManager


class Application:
    """Classe principale de la Radio Suite."""

    def __init__(self):
        self.module_manager = ModuleManager()
        self.name = "ON3RT Radio Suite"
        self.version = "3.0.0"
        self.author = "ON3RT"

    # ---------------------------------------------------------
    # Informations
    # ---------------------------------------------------------

    def info(self):
        """Retourne les informations de l'application."""

        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "modules": self.module_manager.count(),
        }

    # ---------------------------------------------------------
    # Modules
    # ---------------------------------------------------------

    def register_module(self, name, window):
        """Enregistre un module."""

        self.module_manager.register(name, window)

    def show_module(self, name):
        """Affiche un module."""

        return self.module_manager.show(name)

    def close_module(self, name):
        """Ferme un module."""

        self.module_manager.close(name)

    def close_all(self):
        """Ferme tous les modules."""

        self.module_manager.close_all()