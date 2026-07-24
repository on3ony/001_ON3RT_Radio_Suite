"""
core/module_manager.py
------------------------------------------
ON3RT Radio Suite V3

Gestionnaire central des modules.

Fonctions :
    - ouverture des modules
    - une seule instance par module
    - fermeture propre
    - récupération d'une fenêtre existante
"""

from typing import Dict


class ModuleManager:
    """Gestionnaire des fenêtres de la Radio Suite."""

    def __init__(self):
        self._modules: Dict[str, object] = {}

    # ---------------------------------------------------------
    # Enregistrement
    # ---------------------------------------------------------

    def register(self, name: str, window) -> None:
        """Enregistre une fenêtre."""
        self._modules[name] = window

    # ---------------------------------------------------------
    # Recherche
    # ---------------------------------------------------------

    def exists(self, name: str) -> bool:
        """Retourne True si la fenêtre existe."""
        return name in self._modules

    def get(self, name: str):
        """Retourne la fenêtre enregistrée."""
        return self._modules.get(name)

    # ---------------------------------------------------------
    # Ouverture
    # ---------------------------------------------------------

    def show(self, name: str):
        """Affiche une fenêtre existante."""
        window = self.get(name)

        if window is None:
            return False

        window.show()
        window.raise_()
        window.activateWindow()

        return True

    # ---------------------------------------------------------
    # Fermeture
    # ---------------------------------------------------------

    def close(self, name: str):
        """Ferme une fenêtre."""
        window = self.get(name)

        if window is None:
            return

        try:
            window.close()
        except Exception:
            pass

        self._modules.pop(name, None)

    # ---------------------------------------------------------
    # Général
    # ---------------------------------------------------------

    def close_all(self):
        """Ferme tous les modules."""

        for name in list(self._modules.keys()):
            self.close(name)

    def list_modules(self):
        """Retourne les modules ouverts."""

        return sorted(self._modules.keys())

    def count(self) -> int:
        """Nombre de modules ouverts."""

        return len(self._modules)