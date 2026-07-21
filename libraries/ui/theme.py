"""
ON3RT Radio Suite
Gestionnaire de thème (QSS)

Charge automatiquement le thème graphique commun de la suite.
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication


def theme_file() -> Path:
    """
    Retourne le chemin absolu du fichier QSS.
    """

    root = Path(__file__).resolve().parents[2]

    return root / "assets" / "themes" / "on3rt_dark.qss"


def load_theme(app: QApplication) -> bool:
    """
    Charge le thème ON3RT dans l'application.

    Retourne True si le chargement a réussi.
    """

    qss = theme_file()

    if not qss.exists():
        print(f"[THEME] Fichier introuvable : {qss}")
        return False

    try:
        app.setStyleSheet(qss.read_text(encoding="utf-8"))
        print(f"[THEME] Thème chargé : {qss.name}")
        return True

    except Exception as e:
        print(f"[THEME] Erreur : {e}")
        return False