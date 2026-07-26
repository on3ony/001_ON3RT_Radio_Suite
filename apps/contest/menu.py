"""
apps/contest/menu.py
ON3RT Radio Suite - Contest Logbook
"""

from PySide6.QtGui import QAction


def create_menu(window):
    menubar = window.menuBar()

    file_menu = menubar.addMenu("&Fichier")

    act_new = QAction("Nouveau concours", window)
    act_open = QAction("Ouvrir...", window)
    act_save = QAction("Enregistrer", window)
    act_exit = QAction("Quitter", window)

    act_exit.triggered.connect(window.close)

    file_menu.addAction(act_new)
    file_menu.addAction(act_open)
    file_menu.addSeparator()
    file_menu.addAction(act_save)
    file_menu.addSeparator()
    file_menu.addAction(act_exit)

    contest_menu = menubar.addMenu("&Contest")
    contest_menu.addAction(QAction("Import ADIF", window))
    contest_menu.addAction(QAction("Export ADIF", window))
    contest_menu.addAction(QAction("Export Cabrillo", window))

    tools_menu = menubar.addMenu("&Outils")
    tools_menu.addAction(QAction("Préférences", window))

    help_menu = menubar.addMenu("&Aide")
    help_menu.addAction(QAction("À propos", window))

    return menubar
