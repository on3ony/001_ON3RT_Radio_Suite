"""
launcher.py
-------------------------------------------------
ON3RT Radio Suite V3

Point d'entrée unique de l'application.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.application import Application
from core.main_window import MainWindow


def load_theme(app):
    """Charge le thème ON3RT."""

    base = Path(__file__).resolve().parent

    theme = base / "assets" / "themes" / "on3rt_dark.qss"

    if theme.exists():
        with open(theme, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():

    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    load_theme(app)

    application = Application()

    window = MainWindow(application)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()