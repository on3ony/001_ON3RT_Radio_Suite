#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Live
Auteur : ON3RT
Version : 1.0.0
Description :
    Point d'entrée de l'application ON3RT Live.
=========================================================
"""

import sys
import traceback
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .theme import LOGO_FILE

# ----------------------------------------------------------------------
# Informations application
# ----------------------------------------------------------------------

APP_NAME = "ON3RT Live"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).resolve().parent

# ----------------------------------------------------------------------
# Racine du projet (pour accéder aux modules partagés, ex. apps.logbook)
# ----------------------------------------------------------------------

PROJECT_ROOT = BASE_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ----------------------------------------------------------------------
# Gestion des erreurs
# ----------------------------------------------------------------------

def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Affiche les exceptions non gérées.
    """

    error = "".join(
        traceback.format_exception(
            exc_type,
            exc_value,
            exc_traceback
        )
    )

    print(error)

    QMessageBox.critical(
        None,
        APP_NAME,
        f"Une erreur inattendue est survenue.\n\n{error}"
    )

    sys.exit(1)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():

    sys.excepthook = exception_hook

    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon(str(LOGO_FILE)))

    try:
        from .dashboard import DashboardWindow

        window = DashboardWindow()
        window.show()

        sys.exit(app.exec())

    except Exception:
        exception_hook(*sys.exc_info())


# ----------------------------------------------------------------------

if __name__ == "__main__":
    main()
