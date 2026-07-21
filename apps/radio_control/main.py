"""
ON3RT Radio Suite
Application : Radio Control

Point d'entrée de l'application.
"""

import sys

from PySide6.QtWidgets import QApplication

from libraries.ui.theme import load_theme
from .window import RadioControlWindow


def main():
    """Point d'entrée de l'application."""

    app = QApplication(sys.argv)

    # Chargement du thème ON3RT
    load_theme(app)

    # Fenêtre principale
    window = RadioControlWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()